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
    BULK_TRANSFER_INTERVAL
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
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


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

    def on_error_notification(self, issuer_address, message, upload_id, error_transfer_id):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.BULK_TRANSFER_ERROR
        notification.message = message
        notification.metainfo = {
            "upload_id": upload_id,
            "error_transfer_id": error_transfer_id
        }
        self.db.add(notification)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db

    def _get_uploads(self) -> List[BulkTransferUpload]:
        upload_list = self.db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.status == 0). \
            all()
        return upload_list

    def _get_transfer_data(self, upload_id) -> List[BulkTransfer]:
        transfer_list = self.db.query(BulkTransfer). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.status == 0). \
            all()
        return transfer_list

    def process(self):
        upload_list = self._get_uploads()
        if len(upload_list) < 1:
            return

        for _upload in upload_list:
            LOG.info(f"START upload_id:{_upload.upload_id}")
            _upload_status = 1

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
                        _upload.issuer_address,
                        "Issuer does not exist",
                        _upload.upload_id,
                        [])
                    self.sink.flush()
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
                    _upload.issuer_address,
                    "Could not get the private key of the issuer",
                    _upload.upload_id,
                    [])
                self.sink.flush()
                continue

            # Transfer
            transfer_list = self._get_transfer_data(upload_id=_upload.upload_id)
            error_transfer_id = []
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
                    _upload_status = 2  # Error
                    error_transfer_id.append(_transfer.id)
                self.sink.flush()

            self.sink.on_finish_upload_process(_upload.upload_id, _upload_status)
            if len(error_transfer_id) > 0:
                self.sink.on_error_notification(
                    _upload.issuer_address,
                    "Failed to send transaction",
                    _upload.upload_id,
                    error_transfer_id)
            self.sink.flush()


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    while True:
        try:
            processor.process()
        except Exception as ex:
            LOG.error(ex)
        time.sleep(BULK_TRANSFER_INTERVAL)


if __name__ == "__main__":
    main()
