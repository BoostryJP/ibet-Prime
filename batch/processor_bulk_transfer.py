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
import os
import sys
import threading
import time
import uuid
from typing import List, Sequence

from eth_keyfile import decode_keyfile_json
from sqlalchemy import and_, create_engine, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import batch_log

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
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import Web3Wrapper
from config import (
    BULK_TRANSFER_INTERVAL,
    BULK_TRANSFER_WORKER_COUNT,
    BULK_TRANSFER_WORKER_LOT_SIZE,
    DATABASE_URL,
)

"""
[PROCESSOR-Bulk-Transfer]

Asynchronous batch processing for token bulk transfers
"""

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
                    f"<{self.thread_num}> Process start: upload_id={_upload.upload_id}"
                )

                # Get issuer's private key
                try:
                    _account: Account | None = db_session.scalars(
                        select(Account)
                        .where(Account.issuer_address == _upload.issuer_address)
                        .limit(1)
                    ).first()

                    # If issuer does not exist, update the status of the upload to ERROR
                    if _account is None:
                        LOG.warning(
                            f"Issuer of the upload_id:{_upload.upload_id} does not exist"
                        )
                        self.__sink_on_finish_upload_process(
                            db_session=db_session, upload_id=_upload.upload_id, status=2
                        )
                        self.__error_notification(
                            db_session=db_session,
                            issuer_address=_upload.issuer_address,
                            code=0,
                            upload_id=_upload.upload_id,
                            token_type=_upload.token_type,
                            error_transfer_id=[],
                        )
                        db_session.commit()
                        self.__release_processing_issuer(_upload.upload_id)
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
                    self.__sink_on_finish_upload_process(
                        db_session=db_session, upload_id=_upload.upload_id, status=2
                    )
                    self.__error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=1,
                        upload_id=_upload.upload_id,
                        token_type=_upload.token_type,
                        error_transfer_id=[],
                    )
                    db_session.commit()
                    self.__release_processing_issuer(_upload.upload_id)
                    continue

                # Transfer
                transfer_list = self.__get_transfer_data(
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
                                IbetShareContract(_token_addr).bulk_transfer(
                                    data=_transfer_data,
                                    tx_from=_from_addr,
                                    private_key=private_key,
                                )
                            elif _token_type == TokenType.IBET_STRAIGHT_BOND.value:
                                _transfer_data = IbetStraightBondBulkTransferParams(
                                    to_address_list=_to_addr_list,
                                    amount_list=_amount_list,
                                )
                                IbetStraightBondContract(_token_addr).bulk_transfer(
                                    data=_transfer_data,
                                    tx_from=_from_addr,
                                    private_key=private_key,
                                )
                            for _transfer in _transfer_list:
                                self.__sink_on_finish_transfer_process(
                                    db_session=db_session,
                                    record_id=_transfer.id,
                                    status=1,
                                )
                        except ContractRevertError as e:
                            LOG.warning(
                                f"Transaction reverted: id=<{_upload.upload_id}> error_code:<{e.code}> error_msg:<{e.message}>"
                            )
                            for _transfer in _transfer_list:
                                self.__sink_on_finish_transfer_process(
                                    db_session=db_session,
                                    record_id=_transfer.id,
                                    status=2,
                                )
                        except SendTransactionError:
                            LOG.warning(
                                f"Failed to send transaction: id=<{_upload.upload_id}>"
                            )
                            for _transfer in _transfer_list:
                                self.__sink_on_finish_transfer_process(
                                    db_session=db_session,
                                    record_id=_transfer.id,
                                    status=2,
                                )
                        db_session.commit()
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
                                IbetShareContract(_transfer.token_address).transfer(
                                    data=_transfer_data,
                                    tx_from=_transfer.issuer_address,
                                    private_key=private_key,
                                )
                            elif (
                                _transfer.token_type
                                == TokenType.IBET_STRAIGHT_BOND.value
                            ):
                                _transfer_data = IbetStraightBondTransferParams(**token)
                                IbetStraightBondContract(
                                    _transfer.token_address
                                ).transfer(
                                    data=_transfer_data,
                                    tx_from=_transfer.issuer_address,
                                    private_key=private_key,
                                )
                            self.__sink_on_finish_transfer_process(
                                db_session=db_session, record_id=_transfer.id, status=1
                            )
                        except ContractRevertError as e:
                            LOG.warning(
                                f"Transaction reverted: id=<{_transfer.id}> error_code:<{e.code}> error_msg:<{e.message}>"
                            )
                            self.__sink_on_finish_transfer_process(
                                db_session=db_session, record_id=_transfer.id, status=2
                            )
                        except SendTransactionError:
                            LOG.warning(
                                f"Failed to send transaction: id=<{_transfer.id}>"
                            )
                            self.__sink_on_finish_transfer_process(
                                db_session=db_session, record_id=_transfer.id, status=2
                            )
                        db_session.commit()

                # Register upload results
                error_transfer_list = self.__get_transfer_data(
                    db_session=db_session, upload_id=_upload.upload_id, status=2
                )
                if len(error_transfer_list) == 0:  # success
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=1,
                    )
                else:  # error
                    self.__sink_on_finish_upload_process(
                        db_session=db_session,
                        upload_id=_upload.upload_id,
                        status=2,
                    )
                    error_transfer_id = [
                        _error_transfer.id for _error_transfer in error_transfer_list
                    ]
                    self.__error_notification(
                        db_session=db_session,
                        issuer_address=_upload.issuer_address,
                        code=2,
                        upload_id=_upload.upload_id,
                        token_type=_upload.token_type,
                        error_transfer_id=error_transfer_id,
                    )

                db_session.commit()

                # Pop from the list of processing issuers
                self.__release_processing_issuer(_upload.upload_id)

                LOG.info(
                    f"<{self.thread_num}> Process end: upload_id={_upload.upload_id}"
                )
        finally:
            db_session.close()

    def __get_uploads(self, db_session: Session) -> List[BulkTransferUpload]:
        # NOTE:
        # - Only one issuer can be processed in the same thread.
        # - The maximum number of uploads that can be processed in one batch cycle is the number defined by BULK_TRANSFER_WORKER_LOT_SIZE.
        # - Issuers that are not being processed by other threads are processed first.
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
            upload_1: BulkTransferUpload | None = db_session.scalars(
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
            ).first()
            if upload_1 is None:
                # If there are no targets, then all issuers will be retrieved.
                upload_1: BulkTransferUpload | None = db_session.scalars(
                    select(BulkTransferUpload)
                    .where(
                        and_(
                            BulkTransferUpload.upload_id.notin_(locked_update_id),
                            BulkTransferUpload.status == 0,
                        )
                    )
                    .order_by(BulkTransferUpload.created)
                    .limit(1)
                ).first()

            # Issuer to be processed => upload_1.issuer_address
            # Retrieve the data of the Issuer to be processed
            upload_list = []
            if upload_1 is not None:
                upload_list = [upload_1]
                if BULK_TRANSFER_WORKER_LOT_SIZE > 1:
                    upload_list += db_session.scalars(
                        select(BulkTransferUpload)
                        .where(
                            and_(
                                BulkTransferUpload.upload_id.notin_(locked_update_id),
                                BulkTransferUpload.status == 0,
                                BulkTransferUpload.issuer_address
                                == upload_1.issuer_address,
                            )
                        )
                        .order_by(BulkTransferUpload.created)
                        .offset(1)
                        .limit(BULK_TRANSFER_WORKER_LOT_SIZE - 1)
                    ).all()

            processing_issuer[self.thread_num] = {}
            for upload in upload_list:
                processing_issuer[self.thread_num][
                    upload.upload_id
                ] = upload.issuer_address
        return upload_list

    @staticmethod
    def __get_transfer_data(db_session: Session, upload_id: str, status: int):
        transfer_list: Sequence[BulkTransfer] = db_session.scalars(
            select(BulkTransfer).where(
                and_(BulkTransfer.upload_id == upload_id, BulkTransfer.status == status)
            )
        ).all()
        return transfer_list

    @staticmethod
    def __split_list(raw_list: list, size: int):
        """Split a list into sub-lists"""
        for idx in range(0, len(raw_list), size):
            yield raw_list[idx : idx + size]

    def __release_processing_issuer(self, upload_id):
        """Pop from the list of processing issuers"""
        with lock:
            processing_issuer[self.thread_num].pop(upload_id, None)

    @staticmethod
    def __sink_on_finish_upload_process(
        db_session: Session, upload_id: str, status: int
    ):
        db_session.execute(
            update(BulkTransferUpload)
            .where(BulkTransferUpload.upload_id == upload_id)
            .values(status=status)
        )

    @staticmethod
    def __sink_on_finish_transfer_process(
        db_session: Session, record_id: int, status: int
    ):
        db_session.execute(
            update(BulkTransfer)
            .where(BulkTransfer.id == record_id)
            .values(status=status)
        )

    @staticmethod
    def __error_notification(
        db_session: Session,
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
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )
            except Exception as ex:
                LOG.error(ex)
                err_bucket.append(ex)
                break
            time.sleep(BULK_TRANSFER_INTERVAL)


def main():
    LOG.info("Service started successfully")

    for i in range(BULK_TRANSFER_WORKER_COUNT):
        worker = Worker(i)
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()
        LOG.debug(f"thread {i} started")

    while True:
        if len(err_bucket) > 0:
            LOG.error("Processor went down")
            break
        time.sleep(5)
    exit(1)


if __name__ == "__main__":
    main()
