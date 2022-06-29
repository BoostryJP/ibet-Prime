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
from typing import List
import os
import sys
import time
import uuid
import threading

from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    DATABASE_URL,
    BULK_TRANSFER_INTERVAL,
    BULK_TRANSFER_WORKER_COUNT,
    BULK_TRANSFER_WORKER_LOT_SIZE
)
from app.utils.e2ee_utils import E2EEUtils
from app.model.db import (
    Account,
    BulkTransferUpload,
    BulkTransfer,
    TokenType,
    Notification,
    NotificationType
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract
)
from app.model.schema import (
    IbetShareTransfer,
    IbetStraightBondTransfer
)
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import (
    SendTransactionError,
    ServiceUnavailableError,
    ContractRevertError
)
import batch_log

process_name = "PROCESSOR-Bulk-Transfer"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def __init__(self, thread_num):
        self.thread_num = thread_num

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            upload_list = self.__get_uploads(db_session=db_session)
            if len(upload_list) < 1:
                return

            for _upload in upload_list:
                LOG.info(
                    f"thread {self.thread_num} START upload_id:{_upload.upload_id} issuer_address:{_upload.issuer_address}")

                # Get issuer's private key
                try:
                    _account = db_session.query(Account). \
                        filter(Account.issuer_address == _upload.issuer_address). \
                        first()
                    if _account is None:  # If issuer does not exist, update the status of the upload to ERROR
                        LOG.warning(f"Issuer of the upload_id:{_upload.upload_id} does not exist")
                        self.__sink_on_finish_upload_process(
                            db_session=db_session,
                            upload_id=_upload.upload_id,
                            status=2
                        )
                        self.__sink_on_error_notification(
                            db_session=db_session,
                            issuer_address=_upload.issuer_address,
                            code=0,
                            upload_id=_upload.upload_id,
                            token_type=_upload.token_type,
                            error_transfer_id=[]
                        )
                        db_session.commit()
                        self.__release_processing_issuer(_upload.upload_id)
                        continue
                    keyfile_json = _account.keyfile
                    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                    private_key = decode_keyfile_json(
                        raw_keyfile_json=keyfile_json,
                        password=decrypt_password.encode("utf-8")
                    )
                except Exception as err:
                    LOG.exception(
                        f"Could not get the private key of the issuer of upload_id:{_upload.upload_id}",
                        err)
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=2
                    )
                    self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=1,
                        upload_id=_upload.upload_id,
                        token_type=_upload.token_type,
                        error_transfer_id=[]
                    )
                    db_session.commit()
                    self.__release_processing_issuer(_upload.upload_id)
                    continue

                # Transfer
                transfer_list = self.__get_transfer_data(
                    db_session=db_session,
                    upload_id=_upload.upload_id,
                    status=0
                )
                for _transfer in transfer_list:
                    token = {
                        "token_address": _transfer.token_address,
                        "from_address": _transfer.from_address,
                        "to_address": _transfer.to_address,
                        "amount": _transfer.amount
                    }
                    try:
                        if _transfer.token_type == TokenType.IBET_SHARE.value:
                            _transfer_data = IbetShareTransfer(**token)
                            IbetShareContract.transfer(
                                data=_transfer_data,
                                tx_from=_transfer.issuer_address,
                                private_key=private_key
                            )
                        elif _transfer.token_type == TokenType.IBET_STRAIGHT_BOND.value:
                            _transfer_data = IbetStraightBondTransfer(**token)
                            IbetStraightBondContract.transfer(
                                data=_transfer_data,
                                tx_from=_transfer.issuer_address,
                                private_key=private_key
                            )
                        self.__sink_on_finish_transfer_process(
                            db_session=db_session,
                            record_id=_transfer.id,
                            status=1
                        )
                    except ContractRevertError as e:
                        LOG.warning(f"Transaction reverted: id=<{_transfer.id}> error_code:<{e.code}> error_msg:<{e.message}>")
                        self.__sink_on_finish_transfer_process(
                            db_session=db_session,
                            record_id=_transfer.id,
                            status=2
                        )
                    except SendTransactionError:
                        LOG.warning(f"Failed to send transaction: id=<{_transfer.id}>")
                        self.__sink_on_finish_transfer_process(
                            db_session=db_session,
                            record_id=_transfer.id,
                            status=2
                        )
                    db_session.commit()

                error_transfer_list = self.__get_transfer_data(
                    db_session=db_session,
                    upload_id=_upload.upload_id,
                    status=2
                )
                if len(error_transfer_list) == 0:
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=1  # succeeded
                    )
                else:
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=2  # error
                    )
                    error_transfer_id = [_error_transfer.id for _error_transfer in error_transfer_list]
                    self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=2,
                        upload_id=_upload.upload_id,
                        token_type=_upload.token_type,
                        error_transfer_id=error_transfer_id
                    )

                db_session.commit()
                self.__release_processing_issuer(_upload.upload_id)
        finally:
            db_session.close()

    def __get_uploads(self, db_session: Session) -> List[BulkTransferUpload]:
        # NOTE:
        # - There is only one Issuer that is processed in the same thread.
        # - The maximum size to be processed at one time is the size defined in BULK_TRANSFER_WORKER_LOT_SIZE.
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
            # NOTE: Priority is given to non-issuers that are being processed by other threads.
            upload_1 = db_session.query(BulkTransferUpload). \
                filter(BulkTransferUpload.upload_id.notin_(locked_update_id)). \
                filter(BulkTransferUpload.status == 0). \
                filter(BulkTransferUpload.issuer_address.notin_(exclude_issuer)). \
                order_by(BulkTransferUpload.created). \
                first()
            if upload_1 is None:
                # Retrieve again for all issuers
                upload_1 = db_session.query(BulkTransferUpload). \
                    filter(BulkTransferUpload.upload_id.notin_(locked_update_id)). \
                    filter(BulkTransferUpload.status == 0). \
                    order_by(BulkTransferUpload.created). \
                    first()

            # Issuer to be processed => upload_1.issuer_address
            # Retrieve the data of the Issuer to be processed
            upload_list = []
            if upload_1 is not None:
                upload_list = [upload_1]
                if BULK_TRANSFER_WORKER_LOT_SIZE > 1:
                    upload_list = upload_list + db_session.query(BulkTransferUpload). \
                        filter(BulkTransferUpload.upload_id.notin_(locked_update_id)). \
                        filter(BulkTransferUpload.status == 0). \
                        filter(BulkTransferUpload.issuer_address == upload_1.issuer_address). \
                        order_by(BulkTransferUpload.created). \
                        offset(1). \
                        limit(BULK_TRANSFER_WORKER_LOT_SIZE - 1). \
                        all()

            processing_issuer[self.thread_num] = {}
            for upload in upload_list:
                processing_issuer[self.thread_num][upload.upload_id] = upload.issuer_address
        return upload_list

    def __get_transfer_data(self, db_session: Session, upload_id: str, status: int) -> List[BulkTransfer]:
        transfer_list = db_session.query(BulkTransfer). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.status == status). \
            all()
        return transfer_list

    def __release_processing_issuer(self, upload_id):
        with lock:
            processing_issuer[self.thread_num].pop(upload_id, None)

    @staticmethod
    def __sink_on_finish_upload_process(db_session: Session, upload_id: str, status: int):
        transfer_upload_record = db_session.query(BulkTransferUpload). \
            filter(BulkTransferUpload.upload_id == upload_id). \
            first()
        if transfer_upload_record is not None:
            transfer_upload_record.status = status
            db_session.merge(transfer_upload_record)

    @staticmethod
    def __sink_on_finish_transfer_process(db_session: Session, record_id: int, status: int):
        transfer_record = db_session.query(BulkTransfer). \
            filter(BulkTransfer.id == record_id). \
            first()
        if transfer_record is not None:
            transfer_record.status = status
            db_session.merge(transfer_record)

    @staticmethod
    def __sink_on_error_notification(db_session: Session,
                                     issuer_address: str,
                                     code: int,
                                     upload_id: str,
                                     token_type: str,
                                     error_transfer_id: List[int]):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.BULK_TRANSFER_ERROR
        notification.code = code
        notification.metainfo = {
            "upload_id": upload_id,
            "token_type": token_type,
            "error_transfer_id": error_transfer_id
        }
        db_session.add(notification)


# Exception Stack
err_bucket = []
# Lock object for exclusion control
lock = threading.Lock()
# Issuer being processed in threads
processing_issuer = {}


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
            time.sleep(BULK_TRANSFER_INTERVAL)


def main():
    LOG.info("Service started successfully")

    for i in range(BULK_TRANSFER_WORKER_COUNT):
        worker = Worker(i)
        thread = threading.Thread(target=worker.run)
        thread.setDaemon(True)
        thread.start()
        LOG.info(f"thread {i} started")

    while True:
        if len(err_bucket) > 0:
            LOG.error("Processor went down")
            break
        time.sleep(5)
    exit(1)


if __name__ == "__main__":
    main()
