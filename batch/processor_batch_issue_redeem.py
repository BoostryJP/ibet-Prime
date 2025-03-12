"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import asyncio
import sys
import uuid
from asyncio import Event
from typing import Sequence

import uvloop
from eth_keyfile import decode_keyfile_json
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    AdditionalIssueParams as IbetShareAdditionalIssueParams,
    RedeemParams as IbetShareRedeemParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    AdditionalIssueParams as IbetStraightBondAdditionalIssueParams,
    RedeemParams as IbetStraightBondRedeemParams,
)
from app.model.db import (
    Account,
    BatchIssueRedeem,
    BatchIssueRedeemProcessingCategory,
    BatchIssueRedeemUpload,
    Notification,
    NotificationType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from batch import free_malloc
from batch.utils import batch_log
from batch.utils.signal_handler import setup_signal_handler
from config import BULK_TX_LOT_SIZE

"""
[PROCESSOR-Batch-Issue-Redeem]

Batch processing for additional issuance and redemption
"""

process_name = "PROCESSOR-Batch-Issue-Redeem"
LOG = batch_log.get_logger(process_name=process_name)


class Processor:
    def __init__(self, is_shutdown: Event):
        self.is_shutdown = is_shutdown

    async def process(self):
        db_session = BatchAsyncSessionLocal()
        try:
            upload_list: Sequence[
                tuple[BatchIssueRedeemUpload, TokenVersion | None]
            ] = (
                (
                    await db_session.execute(
                        select(BatchIssueRedeemUpload, Token.version)
                        .outerjoin(
                            Token,
                            and_(
                                BatchIssueRedeemUpload.issuer_address
                                == Token.issuer_address,
                                BatchIssueRedeemUpload.token_address
                                == Token.token_address,
                            ),
                        )
                        .where(BatchIssueRedeemUpload.processed == False)
                        .order_by(BatchIssueRedeemUpload.created)
                    )
                )
                .tuples()
                .all()
            )
            for _d in upload_list:
                if self.is_shutdown.is_set():
                    return

                upload = _d[0]
                token_version = _d[1]

                LOG.info(f"Process start: upload_id={upload.upload_id}")

                # Get issuer's private key
                issuer_account: Account | None = (
                    await db_session.scalars(
                        select(Account)
                        .where(Account.issuer_address == upload.issuer_address)
                        .limit(1)
                    )
                ).first()
                if issuer_account is None:
                    LOG.error("Issuer account does not exist")
                    await self.__sink_on_notification(
                        db_session=db_session,
                        issuer_address=upload.issuer_address,
                        token_address=upload.token_address,
                        token_type=upload.token_type,
                        code=1,
                        upload_category=upload.category,
                        upload_id=upload.upload_id,
                        error_data_id_list=[],
                    )
                    upload.processed = True
                    await db_session.commit()
                    continue

                try:
                    issuer_pk = decode_keyfile_json(
                        raw_keyfile_json=issuer_account.keyfile,
                        password=E2EEUtils.decrypt(issuer_account.eoa_password).encode(
                            "utf-8"
                        ),
                    )
                except (ValueError, TypeError):
                    LOG.exception("Failed to decode keyfile")
                    await self.__sink_on_notification(
                        db_session=db_session,
                        issuer_address=upload.issuer_address,
                        token_address=upload.token_address,
                        token_type=upload.token_type,
                        code=2,
                        upload_category=upload.category,
                        upload_id=upload.upload_id,
                        error_data_id_list=[],
                    )
                    upload.processed = True
                    await db_session.commit()
                    continue

                # Processing
                if token_version is not None and token_version >= TokenVersion.V_24_09:
                    await self.__processing_in_batch(
                        db_session=db_session, issuer_pk=issuer_pk, upload=upload
                    )
                else:
                    await self.__processing_individually(
                        db_session=db_session, issuer_pk=issuer_pk, upload=upload
                    )
                if self.is_shutdown.is_set():
                    LOG.info(
                        f"Process pause for graceful shutdown: upload_id={upload.upload_id}"
                    )
                    return

                # Process failed data
                failed_batch_data_list: Sequence[BatchIssueRedeem] = (
                    await db_session.scalars(
                        select(BatchIssueRedeem)
                        .where(
                            and_(
                                BatchIssueRedeem.upload_id == upload.upload_id,
                                BatchIssueRedeem.status == 2,
                            )
                        )
                        .order_by(BatchIssueRedeem.created)
                    )
                ).all()

                error_data_id_list = [data.id for data in failed_batch_data_list]
                # 0: Success, 3: failed
                code = 3 if len(error_data_id_list) > 0 else 0
                await self.__sink_on_notification(
                    db_session=db_session,
                    issuer_address=upload.issuer_address,
                    token_address=upload.token_address,
                    token_type=upload.token_type,
                    code=code,
                    upload_category=upload.category,
                    upload_id=upload.upload_id,
                    error_data_id_list=error_data_id_list,
                )
                # Update to processed
                upload.processed = True
                await db_session.commit()

                LOG.info(f"Process end: upload_id={upload.upload_id}")
        finally:
            await db_session.close()

    async def __processing_individually(
        self, db_session: AsyncSession, issuer_pk: bytes, upload: BatchIssueRedeemUpload
    ):
        """
        Process transactions line by line
        - For v24.6 and earlier tokens
        """
        batch_data_list: Sequence[BatchIssueRedeem] = (
            await db_session.scalars(
                select(BatchIssueRedeem).where(
                    and_(
                        BatchIssueRedeem.upload_id == upload.upload_id,
                        BatchIssueRedeem.status == 0,
                    )
                )
            )
        ).all()
        for batch_data in batch_data_list:
            if self.is_shutdown.is_set():
                return

            tx_hash = "-"
            try:
                if upload.token_type == TokenType.IBET_STRAIGHT_BOND.value:
                    if (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.ISSUE.value
                    ):
                        tx_hash = await IbetStraightBondContract(
                            upload.token_address
                        ).additional_issue(
                            data=IbetStraightBondAdditionalIssueParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            ),
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )
                    elif (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.REDEEM.value
                    ):
                        tx_hash = await IbetStraightBondContract(
                            upload.token_address
                        ).redeem(
                            data=IbetStraightBondRedeemParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            ),
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )
                elif upload.token_type == TokenType.IBET_SHARE.value:
                    if (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.ISSUE.value
                    ):
                        tx_hash = await IbetShareContract(
                            upload.token_address
                        ).additional_issue(
                            data=IbetShareAdditionalIssueParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            ),
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )
                    elif (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.REDEEM.value
                    ):
                        tx_hash = await IbetShareContract(upload.token_address).redeem(
                            data=IbetShareRedeemParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            ),
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )
                LOG.debug(f"Transaction sent successfully: {tx_hash}")
                batch_data.status = 1
            except ContractRevertError as e:
                LOG.warning(
                    f"Transaction reverted: upload_id=<{batch_data.upload_id}> error_code:<{e.code}> error_msg:<{e.message}>"
                )
                batch_data.status = 2
            except SendTransactionError:
                LOG.warning(f"Failed to send transaction: {tx_hash}")
                batch_data.status = 2
            finally:
                await db_session.commit()  # commit for each data

    async def __processing_in_batch(
        self, db_session: AsyncSession, issuer_pk: bytes, upload: BatchIssueRedeemUpload
    ):
        """
        Process transactions in batch
        """

        while True:
            if self.is_shutdown.is_set():
                return

            # Get unprocessed records
            # - Process up to 100(default) records in a batch
            batch_data_list: Sequence[BatchIssueRedeem] = (
                await db_session.scalars(
                    select(BatchIssueRedeem)
                    .where(
                        and_(
                            BatchIssueRedeem.upload_id == upload.upload_id,
                            BatchIssueRedeem.status == 0,
                        )
                    )
                    .limit(BULK_TX_LOT_SIZE)
                )
            ).all()
            if len(batch_data_list) == 0:
                break

            tx_hash = "-"
            try:
                # Send bulk transaction
                if upload.token_type == TokenType.IBET_STRAIGHT_BOND.value:
                    if (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.ISSUE.value
                    ):
                        tx_data: list[IbetStraightBondAdditionalIssueParams] = [
                            IbetStraightBondAdditionalIssueParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            )
                            for batch_data in batch_data_list
                        ]
                        tx_hash = await IbetStraightBondContract(
                            upload.token_address
                        ).bulk_additional_issue(
                            data=tx_data,
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )
                    elif (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.REDEEM.value
                    ):
                        tx_data: list[IbetStraightBondRedeemParams] = [
                            IbetStraightBondRedeemParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            )
                            for batch_data in batch_data_list
                        ]
                        tx_hash = await IbetStraightBondContract(
                            upload.token_address
                        ).bulk_redeem(
                            data=tx_data,
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )
                elif upload.token_type == TokenType.IBET_SHARE.value:
                    if (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.ISSUE.value
                    ):
                        tx_data: list[IbetShareAdditionalIssueParams] = [
                            IbetShareAdditionalIssueParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            )
                            for batch_data in batch_data_list
                        ]
                        tx_hash = await IbetShareContract(
                            upload.token_address
                        ).bulk_additional_issue(
                            data=tx_data,
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )
                    elif (
                        upload.category
                        == BatchIssueRedeemProcessingCategory.REDEEM.value
                    ):
                        tx_data: list[IbetShareRedeemParams] = [
                            IbetShareRedeemParams(
                                account_address=batch_data.account_address,
                                amount=batch_data.amount,
                            )
                            for batch_data in batch_data_list
                        ]
                        tx_hash = await IbetShareContract(
                            upload.token_address
                        ).bulk_redeem(
                            data=tx_data,
                            tx_from=upload.issuer_address,
                            private_key=issuer_pk,
                        )

                # Update status
                LOG.debug(f"Transaction sent successfully: {tx_hash}")
                for batch_data in batch_data_list:
                    batch_data.status = 1
            except ContractRevertError as e:
                LOG.warning(
                    f"Transaction reverted: upload_id=<{upload.upload_id}> error_code:<{e.code}> error_msg:<{e.message}>"
                )
                for batch_data in batch_data_list:
                    batch_data.status = 2
            except SendTransactionError:
                LOG.warning(f"Failed to send transaction: {tx_hash}")
                for batch_data in batch_data_list:
                    batch_data.status = 2
            finally:
                await db_session.commit()  # commit per each bulk transaction

    @staticmethod
    async def __sink_on_notification(
        db_session: AsyncSession,
        issuer_address: str,
        token_address: str,
        token_type: str,
        upload_category: str,
        code: int,
        upload_id: str,
        error_data_id_list: list[int],
    ):
        notification = Notification()
        notification.notice_id = str(uuid.uuid4())
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.code = code
        notification.type = NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
        notification.metainfo = {
            "category": upload_category,
            "upload_id": upload_id,
            "error_data_id": error_data_id_list,
            "token_address": token_address,
            "token_type": token_type,
        }
        db_session.add(notification)


async def main():
    LOG.info("Service started successfully")

    is_shutdown = asyncio.Event()
    setup_signal_handler(logger=LOG, is_shutdown=is_shutdown)

    processor = Processor(is_shutdown)
    try:
        while not is_shutdown.is_set():
            try:
                await processor.process()
            except SQLAlchemyError as sa_err:
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )
            except Exception as ex:
                LOG.exception(ex)

            for _ in range(60):
                if is_shutdown.is_set():
                    break
                await asyncio.sleep(1)
            free_malloc()
    finally:
        LOG.info("Service is shutdown")


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
