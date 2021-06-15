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
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
from web3 import Web3
from web3.middleware import geth_poa_middleware

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    WEB3_HTTP_PROVIDER,
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
from app.exceptions import SendTransactionError
import batch_log

process_name = "PROCESSOR-Bulk-Transfer"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
engine = create_engine(DATABASE_URL, echo=False)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_finish_upload_process(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_finish_upload_process(*args, **kwargs)

    def on_finish_transfer_process(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_finish_transfer_process(*args, **kwargs)

    def on_error_notification(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_error_notification(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_finish_upload_process(self, upload_id, status):
        transfer_upload_record = self.db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.upload_id == upload_id). \
            first()
        if transfer_upload_record is not None:
            transfer_upload_record.status = status
            self.db.merge(transfer_upload_record)

    def on_finish_transfer_process(self, record_id, status):
        transfer_record = self.db.query(BulkTransfer). \
            filter(BulkTransfer.id == record_id). \
            first()
        if transfer_record is not None:
            transfer_record.status = status
            self.db.merge(transfer_record)

    def on_error_notification(self, issuer_address, code, upload_id, error_transfer_id):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.BULK_TRANSFER_ERROR
        notification.code = code
        notification.metainfo = {
            "upload_id": upload_id,
            "error_transfer_id": error_transfer_id
        }
        self.db.add(notification)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db, thread_num):
        self.sink = sink
        self.db = db
        self.thread_num = thread_num

    def _get_uploads(self) -> List[BulkTransferUpload]:
        # NOTE:
        # - Process the same Issuer in one thread.
        # - Processing Issuer by other threads is not priority.
        # - If there is no other than a not priority Issuer, process not priority Issuer.
        lock.acquire()

        locked_update_id = []
        not_priority = []
        for other_thread in non_priority_issuer.values():
            for k, v in other_thread.items():
                locked_update_id.append(k)
                not_priority.append(v)
        not_priority = list(set(not_priority))

        # Get priority Issuer's upload data
        # NOTE: Priority Issuer is an issuer that is not processed by other threads.
        upload = self.db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.upload_id.notin_(locked_update_id)). \
            filter(BulkTransferUpload.status == 0). \
            filter(BulkTransferUpload.issuer_address.notin_(not_priority)). \
            order_by(BulkTransferUpload.created). \
            first()
        if upload is None:
            # Get all Issuer's upload data
            upload = self.db.query(BulkTransferUpload). \
                filter(BulkTransferUpload.upload_id.notin_(locked_update_id)). \
                filter(BulkTransferUpload.status == 0). \
                order_by(BulkTransferUpload.created). \
                first()

        upload_list = []
        if upload is not None:
            upload_list = [upload]
            if BULK_TRANSFER_WORKER_LOT_SIZE > 1:
                # Get same the first Issuer
                upload_list = upload_list + self.db.query(BulkTransferUpload). \
                    filter(BulkTransferUpload.upload_id.notin_(locked_update_id)). \
                    filter(BulkTransferUpload.status == 0). \
                    filter(BulkTransferUpload.issuer_address == upload.issuer_address). \
                    order_by(BulkTransferUpload.created). \
                    offset(1). \
                    limit(BULK_TRANSFER_WORKER_LOT_SIZE - 1). \
                    all()

        non_priority_issuer[self.thread_num] = {}
        for upload in upload_list:
            non_priority_issuer[self.thread_num][upload.upload_id] = upload.issuer_address

        lock.release()
        return upload_list

    def _get_transfer_data(self, upload_id, status) -> List[BulkTransfer]:
        transfer_list = self.db.query(BulkTransfer). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.status == status). \
            all()
        return transfer_list

    def _release_non_priority_issuer(self, upload_id):
        lock.acquire()
        non_priority_issuer[self.thread_num].pop(upload_id, None)
        lock.release()

    def process(self):
        upload_list = self._get_uploads()
        if len(upload_list) < 1:
            return

        for _upload in upload_list:
            LOG.info(
                f"thread {self.thread_num} START upload_id:{_upload.upload_id} issuer_address:{_upload.issuer_address}")
            time.sleep(30)

            # Get issuer's private key
            try:
                _account = self.db.query(Account). \
                    filter(Account.issuer_address == _upload.issuer_address). \
                    first()
                if _account is None:  # If issuer does not exist, update the status of the upload to ERROR
                    LOG.warning(f"Issuer of the upload_id:{_upload.upload_id} does not exist")
                    self.sink.on_finish_upload_process(
                        upload_id=_upload.upload_id,
                        status=2
                    )
                    self.sink.on_error_notification(
                        issuer_address=_upload.issuer_address, code=0, upload_id=_upload.upload_id,
                        error_transfer_id=[])
                    self.sink.flush()
                    self._release_non_priority_issuer(_upload.upload_id)
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
                self.sink.on_finish_upload_process(
                    upload_id=_upload.upload_id,
                    status=2
                )
                self.sink.on_error_notification(
                    issuer_address=_upload.issuer_address, code=1, upload_id=_upload.upload_id, error_transfer_id=[])
                self.sink.flush()
                self._release_non_priority_issuer(_upload.upload_id)
                continue

            # Transfer
            transfer_list = self._get_transfer_data(upload_id=_upload.upload_id, status=0)
            for _transfer in transfer_list:
                token = {
                    "token_address": _transfer.token_address,
                    "transfer_from": _transfer.from_address,
                    "transfer_to": _transfer.to_address,
                    "amount": _transfer.amount
                }
                try:
                    if _transfer.token_type == TokenType.IBET_SHARE:
                        _transfer_data = IbetShareTransfer(**token)
                        IbetShareContract.transfer(
                            data=_transfer_data,
                            tx_from=_transfer.issuer_address,
                            private_key=private_key
                        )
                    elif _transfer.token_type == TokenType.IBET_STRAIGHT_BOND:
                        _transfer_data = IbetStraightBondTransfer(**token)
                        IbetStraightBondContract.transfer(
                            data=_transfer_data,
                            tx_from=_transfer.issuer_address,
                            private_key=private_key
                        )
                    self.sink.on_finish_transfer_process(
                        record_id=_transfer.id,
                        status=1
                    )
                except SendTransactionError:
                    LOG.warning(f"Failed to send transaction: id=<{_transfer.id}>")
                    self.sink.on_finish_transfer_process(
                        record_id=_transfer.id,
                        status=2
                    )
                self.sink.flush()

            error_transfer_list = self._get_transfer_data(upload_id=_upload.upload_id, status=2)
            if len(error_transfer_list) == 0:
                self.sink.on_finish_upload_process(_upload.upload_id, 1)  # succeeded
            else:
                self.sink.on_finish_upload_process(_upload.upload_id, 2)  # error
                error_transfer_id = [_error_transfer.id for _error_transfer in error_transfer_list]
                self.sink.on_error_notification(
                    issuer_address=_upload.issuer_address, code=2,
                    upload_id=_upload.upload_id, error_transfer_id=error_transfer_id)

            self.sink.flush()
            self._release_non_priority_issuer(_upload.upload_id)


err_bucket = []
lock = threading.Lock()
non_priority_issuer = {}


class Worker:

    def __init__(self, thread_num: int):

        db = scoped_session(sessionmaker())
        db.configure(bind=engine)
        _sink = Sinks()
        _sink.register(DBSink(db))
        processor = Processor(sink=_sink, db=db, thread_num=thread_num)
        self.processor = processor

    def run(self):

        while True:
            try:
                self.processor.process()
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
