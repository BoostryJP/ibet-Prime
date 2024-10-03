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
from app.model.blockchain.tx_params.ibet_security_token import ForcedTransferParams
from app.model.db import (
    Account,
    BulkTransfer,
    BulkTransferUpload,
    Notification,
    NotificationType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch.utils import batch_log
from batch.utils.signal_handler import setup_signal_handler
from config import (
    BULK_TRANSFER_INTERVAL,
    BULK_TRANSFER_WORKER_COUNT,
    BULK_TRANSFER_WORKER_LOT_SIZE,
    BULK_TX_LOT_SIZE,
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
    is_shutdown: Event

    def __init__(self, worker_num, is_shutdown: Event):
        self.worker_num: int = worker_num
        self.is_shutdown = is_shutdown

    async def process(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            upload_list = await self.__get_uploads(db_session=db_session)
            if len(upload_list) < 1:
                return

            for _d in upload_list:
                if self.is_shutdown.is_set():
                    return

                _upload = _d[0]
                _token_version = _d[1]

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
                            token_address=_upload.token_address,
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
                        token_address=_upload.token_address,
                        error_transfer_id=[],
                    )
                    await db_session.commit()
                    await self.__release_processing_issuer(_upload.upload_id)
                    continue

                # Transfer
                # - ~v24.6: Forced transfer individually
                # - v24.9~: Bulk forced transfer
                transfer_list = await self.__get_transfer_data(
                    db_session=db_session, upload_id=_upload.upload_id, status=0
                )
                if (
                    _token_version is not None
                    and _token_version >= TokenVersion.V_24_09
                ):
                    # Split the original transfer list into sub-lists
                    chunked_transfer_list: list[list[BulkTransfer]] = list(
                        self.__split_list(list(transfer_list), BULK_TX_LOT_SIZE)
                    )
                    # Execute bulk forced transfer for each sub-list
                    for _transfer_list in chunked_transfer_list:
                        if self.is_shutdown.is_set():
                            LOG.info(
                                f"<{self.worker_num}> Process pause for graceful shutdown: upload_id={_upload.upload_id}"
                            )
                            return

                        try:
                            _transfer_data_list = [
                                ForcedTransferParams(
                                    from_address=_transfer.from_address,
                                    to_address=_transfer.to_address,
                                    amount=_transfer.amount,
                                )
                                for _transfer in _transfer_list
                            ]
                            await self.__bulk_forced_transfer(
                                token_address=_upload.token_address,
                                token_type=_upload.token_type,
                                transfer_data_list=_transfer_data_list,
                                tx_from=_upload.issuer_address,
                                tx_from_pk=private_key,
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
                        if self.is_shutdown.is_set():
                            return

                        # Execute bulk forced transfer
                        try:
                            _transfer_data = ForcedTransferParams(
                                from_address=_transfer.from_address,
                                to_address=_transfer.to_address,
                                amount=_transfer.amount,
                            )
                            await self.__forced_transfer(
                                token_address=_transfer.token_address,
                                token_type=_transfer.token_type,
                                transfer_data=_transfer_data,
                                tx_from=_upload.issuer_address,
                                tx_from_pk=private_key,
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
                        token_address=_upload.token_address,
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

    async def __get_uploads(
        self, db_session: AsyncSession
    ) -> list[tuple[BulkTransferUpload, TokenVersion]]:
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
            upload_1: tuple[BulkTransferUpload, TokenVersion | None] | None = (
                (
                    await db_session.execute(
                        select(BulkTransferUpload, Token.version)
                        .outerjoin(
                            Token,
                            and_(
                                BulkTransferUpload.issuer_address
                                == Token.issuer_address,
                                BulkTransferUpload.token_address == Token.token_address,
                            ),
                        )
                        .where(
                            and_(
                                BulkTransferUpload.upload_id.notin_(locked_update_id),
                                BulkTransferUpload.status == 0,
                                BulkTransferUpload.issuer_address.notin_(
                                    exclude_issuer
                                ),
                                BulkTransferUpload.token_address != None,
                            )
                        )
                        .order_by(BulkTransferUpload.created)
                        .limit(1)
                    )
                )
                .tuples()
                .first()
            )
            if upload_1 is None:
                # If there are no targets, then all issuers will be retrieved.
                upload_1: tuple[BulkTransferUpload, TokenVersion | None] | None = (
                    (
                        await db_session.execute(
                            select(BulkTransferUpload, Token.version)
                            .outerjoin(
                                Token,
                                and_(
                                    BulkTransferUpload.issuer_address
                                    == Token.issuer_address,
                                    BulkTransferUpload.token_address
                                    == Token.token_address,
                                ),
                            )
                            .where(
                                and_(
                                    BulkTransferUpload.upload_id.notin_(
                                        locked_update_id
                                    ),
                                    BulkTransferUpload.status == 0,
                                    BulkTransferUpload.token_address != None,
                                )
                            )
                            .order_by(BulkTransferUpload.created)
                            .limit(1)
                        )
                    )
                    .tuples()
                    .first()
                )

            # Issuer to be processed => upload_1.issuer_address
            # Retrieve the data of the Issuer to be processed
            upload_list: list[tuple[BulkTransferUpload, TokenVersion | None]] = []
            if upload_1 is not None:
                upload_list = [upload_1]
                if BULK_TRANSFER_WORKER_LOT_SIZE > 1:
                    upload_list += (
                        (
                            await db_session.execute(
                                select(BulkTransferUpload, Token.version)
                                .outerjoin(
                                    Token,
                                    and_(
                                        BulkTransferUpload.issuer_address
                                        == Token.issuer_address,
                                        BulkTransferUpload.token_address
                                        == Token.token_address,
                                    ),
                                )
                                .where(
                                    and_(
                                        BulkTransferUpload.upload_id.notin_(
                                            locked_update_id
                                        ),
                                        BulkTransferUpload.status == 0,
                                        BulkTransferUpload.issuer_address
                                        == upload_1[0].issuer_address,
                                        BulkTransferUpload.token_address != None,
                                    )
                                )
                                .order_by(BulkTransferUpload.created)
                                .offset(1)
                                .limit(BULK_TRANSFER_WORKER_LOT_SIZE - 1)
                            )
                        )
                        .tuples()
                        .all()
                    )

            processing_issuer[self.worker_num] = {}
            for upload in upload_list:
                processing_issuer[self.worker_num][upload[0].upload_id] = upload[
                    0
                ].issuer_address
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
    async def __bulk_forced_transfer(
        token_address: str,
        token_type: str,
        transfer_data_list: list[ForcedTransferParams],
        tx_from: str,
        tx_from_pk: bytes,
    ):
        """
        Bulk forced transfer
        - Forced transfers in batch
        """
        if token_type == TokenType.IBET_SHARE.value:
            await IbetShareContract(token_address).bulk_forced_transfer(
                data=transfer_data_list,
                tx_from=tx_from,
                private_key=tx_from_pk,
            )
        elif token_type == TokenType.IBET_STRAIGHT_BOND.value:
            await IbetStraightBondContract(token_address).bulk_forced_transfer(
                data=transfer_data_list,
                tx_from=tx_from,
                private_key=tx_from_pk,
            )

    @staticmethod
    async def __forced_transfer(
        token_address: str,
        token_type: str,
        transfer_data: ForcedTransferParams,
        tx_from: str,
        tx_from_pk: bytes,
    ):
        """
        Forced transfer individually
        """
        if token_type == TokenType.IBET_SHARE.value:
            await IbetShareContract(token_address).forced_transfer(
                data=transfer_data,
                tx_from=tx_from,
                private_key=tx_from_pk,
            )
        elif token_type == TokenType.IBET_STRAIGHT_BOND.value:
            await IbetStraightBondContract(token_address).forced_transfer(
                data=transfer_data,
                tx_from=tx_from,
                private_key=tx_from_pk,
            )

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
        token_address: str | None,
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
            "token_address": token_address,
            "error_transfer_id": error_transfer_id,
        }
        db_session.add(notification)


# Lock object for exclusion control
lock = asyncio.Lock()
# Issuer being processed in workers
processing_issuer = {}


class Worker:
    def __init__(self, worker_num: int, is_shutdown: Event):
        processor = Processor(worker_num=worker_num, is_shutdown=is_shutdown)
        self.processor = processor
        self.is_shutdown = is_shutdown

    async def run(self):
        while not self.is_shutdown.is_set():
            try:
                await self.processor.process()
            except ServiceUnavailableError:
                LOG.warning("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )

            for _ in range(BULK_TRANSFER_INTERVAL):
                if self.is_shutdown.is_set():
                    break
                await asyncio.sleep(1)


async def main():
    LOG.info("Service started successfully")

    is_shutdown = asyncio.Event()
    setup_signal_handler(logger=LOG, is_shutdown=is_shutdown)

    workers = [
        asyncio.create_task(Worker(worker_num=i, is_shutdown=is_shutdown).run())
        for i in range(BULK_TRANSFER_WORKER_COUNT)
    ]
    try:
        while not is_shutdown.is_set():
            await asyncio.sleep(1)
    finally:
        # Ensure that all workers is shutdown
        await asyncio.gather(*workers)
        LOG.info("Service is shutdown")


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
