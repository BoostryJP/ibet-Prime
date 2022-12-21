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
import os
import sys
import time
import uuid
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    DATABASE_URL,
    ZERO_ADDRESS,
    BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE,
    BATCH_REGISTER_PERSONAL_INFO_INTERVAL,
    BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT
)
from app.model.db import (
    Account,
    Token,
    TokenType,
    Notification,
    NotificationType,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfo,
    BatchRegisterPersonalInfoUploadStatus
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract, PersonalInfoContract
)
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import (
    SendTransactionError,
    ServiceUnavailableError,
    ContractRevertError
)
import batch_log

"""
[PROCESSOR-Batch-Register-Personal-Info]

Batch processing for force registration of investor's personal information
"""

process_name = "PROCESSOR-Batch-Register-Personal-Info"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    thread_num: int
    personal_info_contract_accessor_map: dict[str, PersonalInfoContract]

    def __init__(self, thread_num):
        self.thread_num = thread_num
        self.personal_info_contract_accessor_map = {}

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            upload_list: list[BatchRegisterPersonalInfoUpload] = self.__get_uploads(db_session=db_session)

            if len(upload_list) < 1:
                return

            for _upload in upload_list:
                LOG.info(f"<{self.thread_num}> Process start: upload_id={_upload.upload_id}")

                # Get issuer's private key
                issuer_account: Account | None = db_session.query(Account).\
                    filter(Account.issuer_address == _upload.issuer_address).\
                    first()
                if issuer_account is None:  # If issuer does not exist, update the status of the upload to ERROR
                    LOG.warning(f"Issuer of the upload_id:{_upload.upload_id} does not exist")
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=BatchRegisterPersonalInfoUploadStatus.FAILED.value
                    )
                    self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=0,
                        upload_id=_upload.upload_id,
                        error_registration_id=[]
                    )
                    db_session.commit()
                    self.__release_processing_issuer(_upload.upload_id)
                    continue

                # Load PersonalInfo Contract accessor
                self.__load_personal_info_contract_accessor(
                    db_session=db_session,
                    issuer_address=issuer_account.issuer_address
                )

                # Register
                batch_data_list = self.__get_registration_data(
                    db_session=db_session,
                    upload_id=_upload.upload_id,
                    status=0
                )
                for batch_data in batch_data_list:
                    try:
                        personal_info_contract: PersonalInfoContract | None = \
                            self.personal_info_contract_accessor_map.get(batch_data.token_address)
                        if personal_info_contract:
                            tx_hash = personal_info_contract.register_info(
                                account_address=batch_data.account_address,
                                data=batch_data.personal_info
                            )
                            LOG.debug(f"Transaction sent successfully: {tx_hash}")
                            self.__sink_on_finish_register_process(
                                db_session=db_session,
                                record_id=batch_data.id,
                                status=1
                            )
                        else:
                            LOG.warning(f"Failed to get personal info contract: id=<{batch_data.id}>")
                            self.__sink_on_finish_register_process(
                                db_session=db_session,
                                record_id=batch_data.id,
                                status=2
                            )
                    except ContractRevertError as e:
                        LOG.warning(f"Transaction reverted: id=<{batch_data.id}> error_code:<{e.code}> error_msg:<{e.message}>")
                        self.__sink_on_finish_register_process(
                            db_session=db_session,
                            record_id=batch_data.id,
                            status=2
                        )
                    except SendTransactionError:
                        LOG.warning(f"Failed to send transaction: id=<{batch_data.id}>")
                        self.__sink_on_finish_register_process(
                            db_session=db_session,
                            record_id=batch_data.id,
                            status=2
                        )
                    db_session.commit()

                error_registration_list = self.__get_registration_data(
                    db_session=db_session,
                    upload_id=_upload.upload_id,
                    status=2
                )
                if len(error_registration_list) == 0:
                    # succeeded
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=BatchRegisterPersonalInfoUploadStatus.DONE.value
                    )
                else:
                    # failed
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=BatchRegisterPersonalInfoUploadStatus.FAILED.value
                    )
                    error_registration_id = [_error_registration.id for _error_registration in error_registration_list]
                    self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=2,
                        upload_id=_upload.upload_id,
                        error_registration_id=error_registration_id
                    )
                db_session.commit()
                self.__release_processing_issuer(_upload.upload_id)

                LOG.info(f"<{self.thread_num}> Process end: upload_id={_upload.upload_id}")
        finally:
            self.personal_info_contract_accessor_map = {}
            db_session.close()

    def __load_personal_info_contract_accessor(self, db_session: Session, issuer_address: str) -> None:
        """Load PersonalInfo Contracts related to given issuer_address to memory

        :param db_session: database session
        :param issuer_address: from block number
        :return: None
        """
        self.personal_info_contract_accessor_map = {}

        token_list = db_session.query(Token). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_status == 1). \
            all()
        for token in token_list:
            if token.type == TokenType.IBET_SHARE.value:
                token_contract = IbetShareContract.get(token.token_address)
            elif token.type == TokenType.IBET_STRAIGHT_BOND.value:
                token_contract = IbetStraightBondContract.get(token.token_address)
            else:
                continue

            contract_address = token_contract.personal_info_contract_address
            if contract_address != ZERO_ADDRESS:
                self.personal_info_contract_accessor_map[token.token_address] = PersonalInfoContract(
                    db=db_session,
                    issuer_address=issuer_address,
                    contract_address=contract_address
                )

    def __get_uploads(self, db_session: Session) -> list[BatchRegisterPersonalInfoUpload]:
        # NOTE:
        # - There is only one Issuer that is processed in the same thread.
        # - The maximum size to be processed at one time is the size defined
        #   in BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE.
        # - Issuer that is being processed by other threads is controlled to be selected with lower priority.
        # - Exclusion control is performed to eliminate duplication of data to be acquired.

        with lock:  # Exclusion control
            locked_update_id = []
            exclude_issuer = []
            for threads_processing in processing_issuer.values():
                for upload_id, issuer_address in threads_processing.items():
                    locked_update_id.append(upload_id)
                    exclude_issuer.append(issuer_address)
            exclude_issuer = list(set(exclude_issuer))

            # Retrieve one target data
            # NOTE: Priority is given to issuers that are not being processed by other threads.
            upload_1 = db_session.query(BatchRegisterPersonalInfoUpload). \
                filter(BatchRegisterPersonalInfoUpload.upload_id.notin_(locked_update_id)). \
                filter(BatchRegisterPersonalInfoUpload.status == BatchRegisterPersonalInfoUploadStatus.PENDING.value). \
                filter(BatchRegisterPersonalInfoUpload.issuer_address.notin_(exclude_issuer)). \
                order_by(BatchRegisterPersonalInfoUpload.created). \
                first()
            if upload_1 is None:
                # Retrieve again for all issuers
                upload_1 = db_session.query(BatchRegisterPersonalInfoUpload). \
                    filter(BatchRegisterPersonalInfoUpload.upload_id.notin_(locked_update_id)). \
                    filter(BatchRegisterPersonalInfoUpload.status == BatchRegisterPersonalInfoUploadStatus.PENDING.value). \
                    order_by(BatchRegisterPersonalInfoUpload.created). \
                    first()

            # Issuer to be processed => upload_1.issuer_address
            # Retrieve the data of the Issuer to be processed
            upload_list = []
            if upload_1 is not None:
                upload_list = [upload_1]
                if BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE > 1:
                    upload_list = upload_list + db_session.query(BatchRegisterPersonalInfoUpload). \
                        filter(BatchRegisterPersonalInfoUpload.upload_id.notin_(locked_update_id)). \
                        filter(BatchRegisterPersonalInfoUpload.status == BatchRegisterPersonalInfoUploadStatus.PENDING.value). \
                        filter(BatchRegisterPersonalInfoUpload.issuer_address == upload_1.issuer_address). \
                        order_by(BatchRegisterPersonalInfoUpload.created). \
                        offset(1). \
                        limit(BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE - 1). \
                        all()

            processing_issuer[self.thread_num] = {}
            for upload in upload_list:
                processing_issuer[self.thread_num][upload.upload_id] = upload.issuer_address
        return upload_list

    @staticmethod
    def __get_registration_data(db_session: Session, upload_id: str, status: int):
        register_list = db_session.query(BatchRegisterPersonalInfo). \
            filter(BatchRegisterPersonalInfo.upload_id == upload_id). \
            filter(BatchRegisterPersonalInfo.status == status). \
            all()
        return register_list

    def __release_processing_issuer(self, upload_id):
        with lock:
            processing_issuer[self.thread_num].pop(upload_id, None)

    @staticmethod
    def __sink_on_finish_upload_process(db_session: Session, upload_id: str, status: str):
        personal_info_register_upload_record: BatchRegisterPersonalInfoUpload | None = \
            db_session.query(BatchRegisterPersonalInfoUpload). \
            filter(BatchRegisterPersonalInfoUpload.upload_id == upload_id). \
            first()
        if personal_info_register_upload_record is not None:
            personal_info_register_upload_record.status = status
            db_session.merge(personal_info_register_upload_record)

    @staticmethod
    def __sink_on_finish_register_process(db_session: Session, record_id: int, status: int):
        register_record = db_session.query(BatchRegisterPersonalInfo). \
            filter(BatchRegisterPersonalInfo.id == record_id). \
            first()
        if register_record is not None:
            register_record.status = status
            db_session.merge(register_record)

    @staticmethod
    def __sink_on_error_notification(db_session: Session,
                                     issuer_address: str,
                                     code: int,
                                     upload_id: str,
                                     error_registration_id: list[int]):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
        notification.code = code
        notification.metainfo = {
            "upload_id": upload_id,
            "error_registration_id": error_registration_id
        }
        db_session.add(notification)


# Exception Stack
err_bucket = []
# Lock object for exclusion control
lock = threading.Lock()
# Issuer being processed in threads
# {
#     [thread_num: int]: {
#         [upload_id: str]: "issuer_address"
#     }
# }
processing_issuer: dict[int, dict[str, str]] = {}


class Worker:

    def __init__(self, thread_num: int):
        processor = Processor(thread_num=thread_num)
        self.processor = processor

    def run(self):

        while True:
            try:
                self.processor.process()
            except ServiceUnavailableError:
                LOG.warning("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
            except Exception as ex:
                LOG.error(ex)
                err_bucket.append(ex)
                break
            time.sleep(BATCH_REGISTER_PERSONAL_INFO_INTERVAL)


def main():
    LOG.info("Service started successfully")

    for i in range(BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT):
        worker = Worker(i)
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()
        LOG.debug(f"Thread {i} started")

    while True:
        if len(err_bucket) > 0:
            LOG.error("Processor went down")
            break
        time.sleep(5)
    exit(1)


if __name__ == "__main__":
    main()
