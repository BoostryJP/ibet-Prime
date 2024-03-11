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
from typing import List, Sequence

import uvloop
from eth_keyfile import decode_keyfile_json
from sqlalchemy import and_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import (
    ContractRevertError,
    SendTransactionError,
    ServiceUnavailableError,
)
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    BulkTransferParams as IbetShareBulkTransferParams,
    TransferParams as IbetShareTransferParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    BulkTransferParams as IbetStraightBondBulkTransferParams,
    TransferParams as IbetStraightBondTransferParams,
)
from app.model.db import (
    Account,
    BulkTransfer,
    BulkTransferUpload,
    Notification,
    NotificationType,
    TokenType,
)
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import batch_log
from config import (
    BULK_TRANSFER_INTERVAL,
    BULK_TRANSFER_WORKER_COUNT,
    BULK_TRANSFER_WORKER_LOT_SIZE,
)

"""
[PROCESSOR-Bulk-Transfer]

Asynchronous batch processing for token bulk transfers
"""

process_name = "PROCESSOR-Bulk-Transfer"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


class Processor:
    worker_num: int

    def __init__(self, worker_num):
        self.worker_num: int = worker_num

    async def process(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            upload_list = await self.__get_uploads(db_session=db_session)
            if len(upload_list) < 1:
                return

            for _upload in upload_list:
                LOG.info(
                    f"<{self.worker_num}> Process start: upload_id={_upload.upload_id}"
                )

                # Get issuer's private key
                try:
                    _account: Account | None = (
                        await db_session.scalars(
                            select(Account)
                            .where(Account.issuer_address == _upload.issuer_address)
                            .limit(1)
                        )
                    ).first()

                    # If issuer does not exist, update the status of the upload to ERROR
                    if _account is None:
                        LOG.warning(
                            f"Issuer of the upload_id:{_upload.upload_id} does not exist"
                        )
                        await self.__sink_on_finish_upload_process(
                            db_session=db_session, upload_id=_upload.upload_id, status=2
                        )
                        await self.__error_notification(
                            db_session=db_session,
                            issuer_address=_upload.issuer_address,
                            code=0,
                            upload_id=_upload.upload_id,
                            token_type=_upload.token_type,
                            error_transfer_id=[],
                        )
                        await db_session.commit()
                        await self.__release_processing_issuer(_upload.upload_id)
                        continue

                    keyfile_json = _account.keyfile
                    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                    private_key = decode_keyfile_json(
                        raw_keyfile_json=keyfile_json,
                        password=decrypt_password.encode("utf-8"),
                    )
                except Exception:
                    LOG.exception(
                        f"Could not get the private key of the issuer of upload_id:{_upload.upload_id}"
                    )
                    await self.__sink_on_finish_upload_process(
                        db_session=db_session, upload_id=_upload.upload_id, status=2
                    )
                    await self.__error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=1,
                        upload_id=_upload.upload_id,
                        token_type=_upload.token_type,
                        error_transfer_id=[],
                    )
                    await db_session.commit()
                    await self.__release_processing_issuer(_upload.upload_id)
                    continue

                # Transfer
                transfer_list = await self.__get_transfer_data(
                    db_session=db_session, upload_id=_upload.upload_id, status=0
                )
                if _upload.transaction_compression is True:
                    # Split the original transfer list into sub-lists
                    chunked_transfer_list: list[list[BulkTransfer]] = list(
                        self.__split_list(list(transfer_list), 100)
                    )
                    # Execute bulkTransfer for each sub-list
                    for _transfer_list in chunked_transfer_list:
                        _token_type = _transfer_list[0].token_type
                        _token_addr = _transfer_list[0].token_address
                        _from_addr = _transfer_list[0].from_address

                        _to_addr_list = []
                        _amount_list = []
                        for _transfer in _transfer_list:
                            _to_addr_list.append(_transfer.to_address)
                            _amount_list.append(_transfer.amount)

                        try:
                            if _token_type == TokenType.IBET_SHARE.value:
                                _transfer_data = IbetShareBulkTransferParams(
                                    to_address_list=_to_addr_list,
                                    amount_list=_amount_list,
                                )
                                await IbetShareContract(_token_addr).bulk_transfer(
                                    data=_transfer_data,
                                    tx_from=_from_addr,
                                    private_key=private_key,
                                )
                            elif _token_type == TokenType.IBET_STRAIGHT_BOND.value:
                                _transfer_data = IbetStraightBondBulkTransferParams(
                                    to_address_list=_to_addr_list,
                                    amount_list=_amount_list,
                                )
                                await IbetStraightBondContract(
                                    _token_addr
                                ).bulk_transfer(
                                    data=_transfer_data,
                                    tx_from=_from_addr,
                                    private_key=private_key,
                                )
                            for _transfer in _transfer_list:
                                await self.__sink_on_finish_transfer_process(
                                    db_session=db_session,
                                    record_id=_transfer.id,
                                    status=1,
                                )
                        except ContractRevertError as e:
                            LOG.warning(
                                f"Transaction reverted: id=<{_upload.upload_id}> error_code:<{e.code}> error_msg:<{e.message}>"
                            )
                            for _transfer in _transfer_list:
                                await self.__sink_on_finish_transfer_process(
                                    db_session=db_session,
                                    record_id=_transfer.id,
                                    status=2,
                                    transaction_error_code=e.code,
                                    transaction_error_message=e.message,
                                )
                        except SendTransactionError:
                            LOG.warning(
                                f"Failed to send transaction: id=<{_upload.upload_id}>"
                            )
                            for _transfer in _transfer_list:
                                await self.__sink_on_finish_transfer_process(
                                    db_session=db_session,
                                    record_id=_transfer.id,
                                    status=2,
                                )
                        await db_session.commit()
                else:
                    for _transfer in transfer_list:
                        token = {
                            "token_address": _transfer.token_address,
                            "from_address": _transfer.from_address,
                            "to_address": _transfer.to_address,
                            "amount": _transfer.amount,
                        }
                        try:
                            if _transfer.token_type == TokenType.IBET_SHARE.value:
                                _transfer_data = IbetShareTransferParams(**token)
                                await IbetShareContract(
                                    _transfer.token_address
                                ).transfer(
                                    data=_transfer_data,
                                    tx_from=_transfer.issuer_address,
                                    private_key=private_key,
                                )
                            elif (
                                _transfer.token_type
                                == TokenType.IBET_STRAIGHT_BOND.value
                            ):
                                _transfer_data = IbetStraightBondTransferParams(**token)
                                await IbetStraightBondContract(
                                    _transfer.token_address
                                ).transfer(
                                    data=_transfer_data,
                                    tx_from=_transfer.issuer_address,
                                    private_key=private_key,
                                )
                            await self.__sink_on_finish_transfer_process(
                                db_session=db_session, record_id=_transfer.id, status=1
                            )
                        except ContractRevertError as e:
                            LOG.warning(
                                f"Transaction reverted: id=<{_transfer.id}> error_code:<{e.code}> error_msg:<{e.message}>"
                            )
                            await self.__sink_on_finish_transfer_process(
                                db_session=db_session,
                                record_id=_transfer.id,
                                status=2,
                                transaction_error_code=e.code,
                                transaction_error_message=e.message,
                            )
                        except SendTransactionError:
                            LOG.warning(
                                f"Failed to send transaction: id=<{_transfer.id}>"
                            )
                            await self.__sink_on_finish_transfer_process(
                                db_session=db_session, record_id=_transfer.id, status=2
                            )
                        await db_session.commit()

                # Register upload results
                error_transfer_list = await self.__get_transfer_data(
                    db_session=db_session, upload_id=_upload.upload_id, status=2
                )
                if len(error_transfer_list) == 0:  # success
                    await self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=1,
                    )
                else:  # error
                    await self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=2,
                    )
                    error_transfer_id = [
                        _error_transfer.id for _error_transfer in error_transfer_list
                    ]
                    await self.__error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=2,
                        upload_id=_upload.upload_id,
                        token_type=_upload.token_type,
                        error_transfer_id=error_transfer_id,
                    )

                await db_session.commit()

                # Pop from the list of processing issuers
                await self.__release_processing_issuer(_upload.upload_id)

                LOG.info(
                    f"<{self.worker_num}> Process end: upload_id={_upload.upload_id}"
                )
        finally:
            await db_session.close()

    async def __get_uploads(self, db_session: AsyncSession) -> List[BulkTransferUpload]:
        # NOTE:
        # - Only one issuer can be processed in the same thread.
        # - The maximum number of uploads that can be processed in one batch cycle is the number defined by BULK_TRANSFER_WORKER_LOT_SIZE.
        # - Issuers that are not being processed by other threads are processed first.
        # - Exclusion control is performed to eliminate duplication of data to be acquired.

        async with lock:  # Exclusion control
            locked_update_id = []
            exclude_issuer = []
            for threads_processing in processing_issuer.values():
                for upload_id, issuer_address in threads_processing.items():
                    locked_update_id.append(upload_id)
                    exclude_issuer.append(issuer_address)
            exclude_issuer = list(set(exclude_issuer))

            # Retrieve one target data
            # NOTE: Priority is given to issuers that are not being processed by other threads.
            upload_1: BulkTransferUpload | None = (
                await db_session.scalars(
                    select(BulkTransferUpload)
                    .where(
                        and_(
                            BulkTransferUpload.upload_id.notin_(locked_update_id),
                            BulkTransferUpload.status == 0,
                            BulkTransferUpload.issuer_address.notin_(exclude_issuer),
                        )
                    )
                    .order_by(BulkTransferUpload.created)
                    .limit(1)
                )
            ).first()
            if upload_1 is None:
                # If there are no targets, then all issuers will be retrieved.
                upload_1: BulkTransferUpload | None = (
                    await db_session.scalars(
                        select(BulkTransferUpload)
                        .where(
                            and_(
                                BulkTransferUpload.upload_id.notin_(locked_update_id),
                                BulkTransferUpload.status == 0,
                            )
                        )
                        .order_by(BulkTransferUpload.created)
                        .limit(1)
                    )
                ).first()

            # Issuer to be processed => upload_1.issuer_address
            # Retrieve the data of the Issuer to be processed
            upload_list = []
            if upload_1 is not None:
                upload_list = [upload_1]
                if BULK_TRANSFER_WORKER_LOT_SIZE > 1:
                    upload_list += (
                        await db_session.scalars(
                            select(BulkTransferUpload)
                            .where(
                                and_(
                                    BulkTransferUpload.upload_id.notin_(
                                        locked_update_id
                                    ),
                                    BulkTransferUpload.status == 0,
                                    BulkTransferUpload.issuer_address
                                    == upload_1.issuer_address,
                                )
                            )
                            .order_by(BulkTransferUpload.created)
                            .offset(1)
                            .limit(BULK_TRANSFER_WORKER_LOT_SIZE - 1)
                        )
                    ).all()

            processing_issuer[self.worker_num] = {}
            for upload in upload_list:
                processing_issuer[self.worker_num][
                    upload.upload_id
                ] = upload.issuer_address
        return upload_list

    @staticmethod
    async def __get_transfer_data(
        db_session: AsyncSession, upload_id: str, status: int
    ):
        transfer_list: Sequence[BulkTransfer] = (
            await db_session.scalars(
                select(BulkTransfer).where(
                    and_(
                        BulkTransfer.upload_id == upload_id,
                        BulkTransfer.status == status,
                    )
                )
            )
        ).all()
        return transfer_list

    @staticmethod
    def __split_list(raw_list: list, size: int):
        """Split a list into sub-lists"""
        for idx in range(0, len(raw_list), size):
            yield raw_list[idx : idx + size]

    async def __release_processing_issuer(self, upload_id):
        """Pop from the list of processing issuers"""
        async with lock:
            processing_issuer[self.worker_num].pop(upload_id, None)

    @staticmethod
    async def __sink_on_finish_upload_process(
        db_session: AsyncSession, upload_id: str, status: int
    ):
        await db_session.execute(
            update(BulkTransferUpload)
            .where(BulkTransferUpload.upload_id == upload_id)
            .values(status=status)
        )

    @staticmethod
    async def __sink_on_finish_transfer_process(
        db_session: AsyncSession,
        record_id: int,
        status: int,
        transaction_error_code: int = None,
        transaction_error_message: str = None,
    ):
        await db_session.execute(
            update(BulkTransfer)
            .where(BulkTransfer.id == record_id)
            .values(
                status=status,
                transaction_error_code=transaction_error_code,
                transaction_error_message=transaction_error_message,
            )
        )

    @staticmethod
    async def __error_notification(
        db_session: AsyncSession,
        issuer_address: str,
        code: int,
        upload_id: str,
        token_type: str,
        error_transfer_id: List[int],
    ):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.BULK_TRANSFER_ERROR
        notification.code = code
        notification.metainfo = {
            "upload_id": upload_id,
            "token_type": token_type,
            "error_transfer_id": error_transfer_id,
        }
        db_session.add(notification)


# Lock object for exclusion control
lock = asyncio.Lock()
# Issuer being processed in workers
processing_issuer = {}


class Worker:
    def __init__(self, worker_num: int):
        processor = Processor(worker_num=worker_num)
        self.processor = processor

    async def run(self):
        while True:
            try:
                await self.processor.process()
            except ServiceUnavailableError:
                LOG.warning("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )

            await asyncio.sleep(BULK_TRANSFER_INTERVAL)


async def main():
    LOG.info("Service started successfully")

    workers = [Worker(i) for i in range(BULK_TRANSFER_WORKER_COUNT)]
    try:
        await SemaphoreTaskGroup.run(
            *[worker.run() for worker in workers],
            max_concurrency=BULK_TRANSFER_WORKER_COUNT,
        )
    except ExceptionGroup:
        LOG.exception("Processor went down")
        sys.exit(1)


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
