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
import time
from datetime import timezone, timedelta

from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from config import WEB3_HTTP_PROVIDER, DATABASE_URL
from app.model.utils import E2EEUtils
from app.model.db import Account, BulkTransferUpload, BulkTransfer, TokenType
from app.model.blockchain import IbetStraightBondContract, IbetShareContract
from app.model.schema import IbetShareTransfer, IbetStraightBondTransfer
from app.exceptions import SendTransactionError

import batch_log

JST = timezone(timedelta(hours=+9), "JST")
path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

process_name = "Bulk-Transfer"
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

    def on_completed_upload(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_completed_upload(*args, **kwargs)

    def on_completed(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_completed(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_completed_upload(self, upload_id, status):
        transfer_upload_record = self.db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.upload_id == upload_id). \
            first()
        if transfer_upload_record is not None:
            transfer_upload_record.status = status
            self.db.merge(transfer_upload_record)

    def on_completed(self, record_id, status):
        transfer_record = self.db.query(BulkTransfer). \
            filter(BulkTransfer.id == record_id). \
            first()
        if transfer_record is not None:
            transfer_record.status = status
            self.db.merge(transfer_record)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db
        self.token_list = []
        self.upload_list = []
        self.transfer_list = []

    def _get_bulk_transfer_lists(self):
        self.upload_list = []
        bulk_transfer_upload = self.db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.status == 0). \
            all()

        for _upload in bulk_transfer_upload:
            self.upload_list.append(_upload)

        self.transfer_list = []
        bulk_transfer = self.db.query(BulkTransfer). \
            all()
        for _transfer in bulk_transfer:
            self.transfer_list.append(_transfer)

    def process(self):
        self._get_bulk_transfer_lists()
        if len(self.upload_list) < 1:
            LOG.info(f"<{process_name}> bulk transfer upload list is None")
            return

        for _upload in self.upload_list:
            _upload_status = 1
            for _t in self.transfer_list:
                if not _upload.upload_id == _t.upload_id:
                    continue
                # transfer run only status == 0
                if _t.status == 1:
                    continue
                elif _t.status == 2:
                    _upload_status = 2
                    continue
                # Get Account
                _account = self.db.query(Account). \
                    filter(Account.issuer_address == _t.issuer_address). \
                    first()
                if _account is None:
                    self.sink.on_completed(_t.id, 2)
                    _upload_status = 2
                    LOG.info(f"<{process_name}> bulk transfer id=<{_t.id}> not found")
                    continue

                # Get private key
                keyfile_json = _account.keyfile
                decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                private_key = decode_keyfile_json(
                    raw_keyfile_json=keyfile_json,
                    password=decrypt_password.encode("utf-8")
                )

                token = {
                           "token_address": _t.token_address,
                           "transfer_from": _t.from_address,
                           "transfer_to": _t.to_address,
                           "amount": _t.amount
                }
                if _t.token_type == TokenType.IBET_SHARE:
                    _transfer_data = IbetShareTransfer(**token)
                    try:
                        IbetShareContract.transfer(
                            data=_transfer_data,
                            tx_from=_t.issuer_address,
                            private_key=private_key
                        )
                        self.sink.on_completed(_t.id, 1)
                        self.sink.flush()
                    except SendTransactionError:
                        self.sink.on_completed(_t.id, 2)
                        self.sink.flush()
                        _upload_status = 2
                        LOG.info(f"<{process_name}> bulk transfer id=<{_t.id}> failed")
                elif _t.token_type == TokenType.IBET_STRAIGHT_BOND:
                    _transfer_data = IbetStraightBondTransfer(**token)
                    try:
                        IbetStraightBondContract.transfer(
                            data=_transfer_data,
                            tx_from=_t.issuer_address,
                            private_key=private_key
                        )
                        self.sink.on_completed(_t.id, 1)
                        self.sink.flush()
                    except SendTransactionError:
                        self.sink.on_completed(_t.id, 2)
                        self.sink.flush()
                        _upload_status = 2
                        LOG.info(f"<{process_name}> bulk transfer id=<{_t.id}> failed")
            self.sink.on_completed_upload(_upload.upload_id, _upload_status)
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
        time.sleep(10)


if __name__ == "__main__":
    main()
