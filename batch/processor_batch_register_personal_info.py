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

from __future__ import annotations

import asyncio
import sys
import uuid
from asyncio import Event
from typing import Sequence

import uvloop
from sqlalchemy import and_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import (
    ContractRevertError,
    SendTransactionError,
    ServiceUnavailableError,
)
from app.model.db import (
    Account,
    BatchRegisterPersonalInfo,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    Notification,
    NotificationType,
    Token,
    TokenStatus,
    TokenType,
)
from app.model.ibet import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract,
)
from app.utils.ibet_web3_utils import AsyncWeb3Wrapper
from batch import free_malloc
from batch.utils import batch_log
from batch.utils.signal_handler import setup_signal_handler
from config import (
    BATCH_REGISTER_PERSONAL_INFO_INTERVAL,
    BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT,
    BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE,
    ZERO_ADDRESS,
)

"""
[PROCESSOR-Batch-Register-Personal-Info]

Batch processing for force registration of investor's personal information
"""

process_name = "PROCESSOR-Batch-Register-Personal-Info"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


class Processor:
    worker_num: int
    personal_info_contract_accessor_map: dict[str, PersonalInfoContract]
    is_shutdown: Event

    def __init__(self, worker_num, is_shutdown: Event):
        self.worker_num = worker_num
        self.personal_info_contract_accessor_map = {}
        self.is_shutdown = is_shutdown

    async def process(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            upload_list: list[
                BatchRegisterPersonalInfoUpload
            ] = await self.__get_uploads(db_session=db_session)

            if len(upload_list) < 1:
                return

            for _upload in upload_list:
                if self.is_shutdown.is_set():
                    return

                LOG.info(
                    f"<{self.worker_num}> Process start: upload_id={_upload.upload_id}"
                )

                # Get issuer's private key
                issuer_account: Account | None = (
                    await db_session.scalars(
                        select(Account)
                        .where(Account.issuer_address == _upload.issuer_address)
                        .limit(1)
                    )
                ).first()
                if (
                    issuer_account is None
                ):  # If issuer does not exist, update the status of the upload to ERROR
                    LOG.warning(
                        f"Issuer of the upload_id:{_upload.upload_id} does not exist"
                    )
                    await self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=BatchRegisterPersonalInfoUploadStatus.FAILED,
                    )
                    await self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        token_address=_upload.token_address,
                        code=0,
                        upload_id=_upload.upload_id,
                        error_registration_id=[],
                    )
                    await db_session.commit()
                    await self.__release_processing_issuer(_upload.upload_id)
                    continue

                # Load PersonalInfo Contract accessor
                await self.__load_personal_info_contract_accessor(
                    db_session=db_session, issuer_account=issuer_account
                )

                # Register
                batch_data_list = await self.__get_registration_data(
                    db_session=db_session, upload_id=_upload.upload_id, status=0
                )
                for batch_data in batch_data_list:
                    if self.is_shutdown.is_set():
                        LOG.info(
                            f"<{self.worker_num}> Process pause for graceful shutdown: upload_id={_upload.upload_id}"
                        )
                        return

                    try:
                        personal_info_contract: PersonalInfoContract | None = (
                            self.personal_info_contract_accessor_map.get(
                                batch_data.token_address
                            )
                        )
                        if personal_info_contract:
                            tx_hash = await personal_info_contract.register_info(
                                account_address=batch_data.account_address,
                                data=batch_data.personal_info,
                            )
                            LOG.debug(f"Transaction sent successfully: {tx_hash}")
                            await self.__sink_on_finish_register_process(
                                db_session=db_session, record_id=batch_data.id, status=1
                            )
                        else:
                            LOG.warning(
                                f"Failed to get personal info contract: id=<{batch_data.id}>"
                            )
                            await self.__sink_on_finish_register_process(
                                db_session=db_session, record_id=batch_data.id, status=2
                            )
                    except ContractRevertError as e:
                        LOG.warning(
                            f"Transaction reverted: id=<{batch_data.id}> error_code:<{e.code}> error_msg:<{e.message}>"
                        )
                        await self.__sink_on_finish_register_process(
                            db_session=db_session, record_id=batch_data.id, status=2
                        )
                    except SendTransactionError:
                        LOG.warning(f"Failed to send transaction: id=<{batch_data.id}>")
                        await self.__sink_on_finish_register_process(
                            db_session=db_session, record_id=batch_data.id, status=2
                        )
                    except ValueError:
                        # for ValueError: Plaintext is too long
                        LOG.warning(f"Failed to send transaction: id=<{batch_data.id}>")
                        await self.__sink_on_finish_register_process(
                            db_session=db_session, record_id=batch_data.id, status=2
                        )
                    await db_session.commit()

                error_registration_list = await self.__get_registration_data(
                    db_session=db_session, upload_id=_upload.upload_id, status=2
                )
                if len(error_registration_list) == 0:
                    # succeeded
                    await self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=BatchRegisterPersonalInfoUploadStatus.DONE,
                    )
                else:
                    # failed
                    await self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=BatchRegisterPersonalInfoUploadStatus.FAILED,
                    )
                    error_registration_id = [
                        _error_registration.id
                        for _error_registration in error_registration_list
                    ]
                    await self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        token_address=_upload.token_address,
                        code=1,
                        upload_id=_upload.upload_id,
                        error_registration_id=error_registration_id,
                    )
                await db_session.commit()
                await self.__release_processing_issuer(_upload.upload_id)

                LOG.info(
                    f"<{self.worker_num}> Process end: upload_id={_upload.upload_id}"
                )
        finally:
            self.personal_info_contract_accessor_map = {}
            await db_session.close()

    async def __load_personal_info_contract_accessor(
        self, db_session: AsyncSession, issuer_account: Account
    ) -> None:
        """Load PersonalInfo Contracts related to given issuer_address to memory"""
        self.personal_info_contract_accessor_map = {}

        token_list: Sequence[Token] = (
            await db_session.scalars(
                select(Token)
                .join(
                    Account,
                    and_(
                        Account.issuer_address == Token.issuer_address,
                        Account.is_deleted == False,
                    ),
                )
                .where(
                    and_(
                        Token.issuer_address == issuer_account.issuer_address,
                        Token.token_status == TokenStatus.SUCCEEDED,
                    )
                )
            )
        ).all()
        for token in token_list:
            if token.type == TokenType.IBET_SHARE.value:
                token_contract = await IbetShareContract(token.token_address).get()
            elif token.type == TokenType.IBET_STRAIGHT_BOND.value:
                token_contract = await IbetStraightBondContract(
                    token.token_address
                ).get()
            else:
                continue

            contract_address = token_contract.personal_info_contract_address
            if contract_address != ZERO_ADDRESS:
                self.personal_info_contract_accessor_map[token.token_address] = (
                    PersonalInfoContract(
                        logger=LOG,
                        issuer=issuer_account,
                        contract_address=contract_address,
                    )
                )

    async def __get_uploads(
        self, db_session: AsyncSession
    ) -> list[BatchRegisterPersonalInfoUpload]:
        # NOTE:
        # - There is only one Issuer that is processed in the same thread.
        # - The maximum size to be processed at one time is the size defined
        #   in BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE.
        # - Issuer that is being processed by other threads is controlled to be selected with lower priority.
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
            upload_1: BatchRegisterPersonalInfoUpload | None = (
                await db_session.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        and_(
                            BatchRegisterPersonalInfoUpload.upload_id.notin_(
                                locked_update_id
                            ),
                            BatchRegisterPersonalInfoUpload.status
                            == BatchRegisterPersonalInfoUploadStatus.PENDING,
                            BatchRegisterPersonalInfoUpload.issuer_address.notin_(
                                exclude_issuer
                            ),
                        )
                    )
                    .order_by(BatchRegisterPersonalInfoUpload.created)
                    .limit(1)
                )
            ).first()
            if upload_1 is None:
                # Retrieve again for all issuers
                upload_1: BatchRegisterPersonalInfoUpload | None = (
                    await db_session.scalars(
                        select(BatchRegisterPersonalInfoUpload)
                        .where(
                            and_(
                                BatchRegisterPersonalInfoUpload.upload_id.notin_(
                                    locked_update_id
                                ),
                                BatchRegisterPersonalInfoUpload.status
                                == BatchRegisterPersonalInfoUploadStatus.PENDING,
                            )
                        )
                        .order_by(BatchRegisterPersonalInfoUpload.created)
                        .limit(1)
                    )
                ).first()

            # Issuer to be processed => upload_1.issuer_address
            # Retrieve the data of the Issuer to be processed
            upload_list = []
            if upload_1 is not None:
                upload_list = [upload_1]
                if BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE > 1:
                    upload_list += (
                        await db_session.scalars(
                            select(BatchRegisterPersonalInfoUpload)
                            .where(
                                and_(
                                    BatchRegisterPersonalInfoUpload.upload_id.notin_(
                                        locked_update_id
                                    ),
                                    BatchRegisterPersonalInfoUpload.status
                                    == BatchRegisterPersonalInfoUploadStatus.PENDING,
                                    BatchRegisterPersonalInfoUpload.issuer_address
                                    == upload_1.issuer_address,
                                )
                            )
                            .order_by(BatchRegisterPersonalInfoUpload.created)
                            .offset(1)
                            .limit(BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE - 1)
                        )
                    ).all()

            processing_issuer[self.worker_num] = {}
            for upload in upload_list:
                processing_issuer[self.worker_num][upload.upload_id] = (
                    upload.issuer_address
                )
        return upload_list

    @staticmethod
    async def __get_registration_data(
        db_session: AsyncSession, upload_id: str, status: int
    ):
        register_list: Sequence[BatchRegisterPersonalInfo] = (
            await db_session.scalars(
                select(BatchRegisterPersonalInfo).where(
                    and_(
                        BatchRegisterPersonalInfo.upload_id == upload_id,
                        BatchRegisterPersonalInfo.status == status,
                    )
                )
            )
        ).all()
        return register_list

    async def __release_processing_issuer(self, upload_id):
        async with lock:
            processing_issuer[self.worker_num].pop(upload_id, None)

    @staticmethod
    async def __sink_on_finish_upload_process(
        db_session: AsyncSession, upload_id: str, status: str
    ):
        await db_session.execute(
            update(BatchRegisterPersonalInfoUpload)
            .where(BatchRegisterPersonalInfoUpload.upload_id == upload_id)
            .values(status=status)
        )

    @staticmethod
    async def __sink_on_finish_register_process(
        db_session: AsyncSession, record_id: int, status: int
    ):
        await db_session.execute(
            update(BatchRegisterPersonalInfo)
            .where(BatchRegisterPersonalInfo.id == record_id)
            .values(status=status)
        )

    @staticmethod
    async def __sink_on_error_notification(
        db_session: AsyncSession,
        issuer_address: str,
        token_address: str | None,
        code: int,
        upload_id: str,
        error_registration_id: list[int],
    ):
        notification = Notification()
        notification.notice_id = str(uuid.uuid4())
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
        notification.code = code
        notification.metainfo = {
            "upload_id": upload_id,
            "token_address": token_address,
            "error_registration_id": error_registration_id,
        }
        db_session.add(notification)


# Lock object for exclusion control
lock = asyncio.Lock()
# Issuer being processed in workers
# {
#     [thread_num: int]: {
#         [upload_id: str]: "issuer_address"
#     }
# }
processing_issuer: dict[int, dict[str, str]] = {}


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

            for _ in range(BATCH_REGISTER_PERSONAL_INFO_INTERVAL):
                if self.is_shutdown.is_set():
                    break
                await asyncio.sleep(1)
            free_malloc()


async def main():
    LOG.info("Service started successfully")

    is_shutdown = asyncio.Event()
    setup_signal_handler(logger=LOG, is_shutdown=is_shutdown)

    workers = [
        asyncio.create_task(Worker(worker_num=i, is_shutdown=is_shutdown).run())
        for i in range(BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT)
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
