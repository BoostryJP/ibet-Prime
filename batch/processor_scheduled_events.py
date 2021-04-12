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
from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from web3 import Web3
from web3.middleware import geth_poa_middleware

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from datetime import datetime
from config import (
    WEB3_HTTP_PROVIDER,
    DATABASE_URL,
    SCHEDULED_EVENTS_INTERVAL
)
from app.model.utils import E2EEUtils
from app.model.db import (
    Account,
    ScheduledEvents,
    ScheduledEventType,
    TokenType
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract
)
from app.model.schema import (
    IbetShareUpdate,
    IbetStraightBondUpdate
)
from app.exceptions import SendTransactionError
import batch_log

process_name = "PROCESSOR-Scheduled-Events"
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

    def on_finish_event_process(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_finish_event_process(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_finish_event_process(self, record_id, status):
        scheduled_event_record = self.db.query(ScheduledEvents). \
            filter(ScheduledEvents.id == record_id). \
            first()
        if scheduled_event_record is not None:
            scheduled_event_record.status = status
            self.db.merge(scheduled_event_record)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db

    def _get_events(self, filter_time) -> List[ScheduledEvents]:
        events_list = self.db.query(ScheduledEvents). \
            filter(ScheduledEvents.status == 0). \
            filter(ScheduledEvents.scheduled_datetime <= filter_time). \
            all()
        return events_list

    def process(self):
        process_start_time = datetime.utcnow()
        events_list = self._get_events(process_start_time)
        if len(events_list) < 1:
            return

        for _event in events_list:
            LOG.info(f"START event_id:{_event.id}")
            _upload_status = 1

            # Get issuer's private key
            try:
                _account = self.db.query(Account). \
                    filter(Account.issuer_address == _event.issuer_address). \
                    first()
                if _account is None:  # If issuer does not exist, update the status of the upload to ERROR
                    LOG.warning(f"Issuer of the event_id:{_event.id} does not exist")
                    self.sink.on_finish_event_process(
                        record_id=_event.id,
                        status=2
                    )
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
                    f"Could not get the private key of the issuer of id:{_event.id}",
                    err)
                self.sink.on_finish_event_process(
                    record_id=_event.id,
                    status=2
                )
                self.sink.flush()
                continue

            try:
                # Token_type
                if _event.token_type == TokenType.IBET_SHARE:
                    # Update
                    if _event.event_type == ScheduledEventType.UPDATE:
                        _update_data = IbetShareUpdate(**_event.data)
                        IbetShareContract.update(
                            contract_address=_event.token_address,
                            data=_update_data,
                            tx_from=_event.issuer_address,
                            private_key=private_key
                        )
                elif _event.token_type == TokenType.IBET_STRAIGHT_BOND:
                    # Update
                    if _event.event_type == ScheduledEventType.UPDATE:
                        _update_data = IbetStraightBondUpdate(**_event.data)
                        IbetStraightBondContract.update(
                            contract_address=_event.token_address,
                            data=_update_data,
                            tx_from=_event.issuer_address,
                            private_key=private_key
                        )
                self.sink.on_finish_event_process(
                    record_id=_event.id,
                    status=1
                    )
            except SendTransactionError:
                LOG.warning(f"Failed to send transaction: id=<{_event.id}>")
                self.sink.on_finish_event_process(
                    record_id=_event.id,
                    status=2
                )
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
        time.sleep(SCHEDULED_EVENTS_INTERVAL)


if __name__ == "__main__":
    main()
