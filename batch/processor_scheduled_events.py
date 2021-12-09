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
from typing import List, Set, Optional, cast

from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session, Session
)

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from datetime import (
    datetime,
    timezone
)
from config import (
    DATABASE_URL,
    SCHEDULED_EVENTS_INTERVAL, SCHEDULED_EVENTS_WORKER_COUNT
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import Web3Wrapper
from app.model.db import (
    Account,
    ScheduledEvents,
    ScheduledEventType,
    TokenType,
    AdditionalTokenInfo,
    Notification,
    NotificationType
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

web3 = Web3Wrapper()
engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)

lock = threading.Lock()
# Issuer being processed in threads
processing_issuers: Set[str] = set()


class Sinks:
    def __init__(self):
        self.sinks: List["DBSink"] = []

    def register(self, sink: "DBSink"):
        self.sinks.append(sink)

    def on_finish_event_process(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_finish_event_process(*args, **kwargs)

    def on_error_notification(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_error_notification(*args, **kwargs)

    def on_additional_token_info(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_additional_token_info(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db: Session):
        self.db = db

    def on_finish_event_process(self, record_id, status):
        scheduled_event_record = self.db.query(ScheduledEvents). \
            filter(ScheduledEvents.id == record_id). \
            first()
        if scheduled_event_record is not None:
            scheduled_event_record.status = status
            self.db.merge(scheduled_event_record)

    def on_error_notification(self, issuer_address, code, scheduled_event_id, token_type):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.SCHEDULE_EVENT_ERROR
        notification.code = code
        notification.metainfo = {
            "scheduled_event_id": scheduled_event_id,
            "token_type": token_type
        }
        self.db.add(notification)

    def on_additional_token_info(self, token_address, **kwargs):
        _additional_info = AdditionalTokenInfo()
        _additional_info.token_address = token_address
        block = web3.eth.get_block("latest")
        _additional_info.block_number = block["number"]
        _additional_info.block_timestamp = datetime.fromtimestamp(block["timestamp"], tz=timezone.utc)
        if "is_manual_transfer_approval" in kwargs:
            setattr(_additional_info, "is_manual_transfer_approval", kwargs["is_manual_transfer_approval"])
        self.db.add(_additional_info)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink: Sinks, db: Session, thread_num: int):
        self.sink = sink
        self.db = db
        self.thread_num = thread_num

    def _get_events_of_one_issuer(self, filter_time: datetime) -> List[ScheduledEvents]:
        with lock:
            event: Optional[ScheduledEvents] = self.db.query(ScheduledEvents). \
                filter(ScheduledEvents.status == 0). \
                filter(ScheduledEvents.scheduled_datetime <= filter_time). \
                filter(ScheduledEvents.issuer_address.notin_(processing_issuers)). \
                order_by(ScheduledEvents.scheduled_datetime, ScheduledEvents.id). \
                first()
            if event is None:
                return []
            issuer_address = event.issuer_address
            processing_issuers.add(issuer_address)

        events_list: List[ScheduledEvents] = self.db.query(ScheduledEvents). \
            filter(ScheduledEvents.status == 0). \
            filter(ScheduledEvents.scheduled_datetime <= filter_time). \
            filter(ScheduledEvents.issuer_address == issuer_address). \
            order_by(ScheduledEvents.scheduled_datetime, ScheduledEvents.id). \
            all()
        return events_list

    def _release_processing_issuer(self, issuer_address: str):
        with lock:
            processing_issuers.remove(issuer_address)

    def process(self):
        process_start_time = datetime.utcnow()
        while True:
            events_list = self._get_events_of_one_issuer(process_start_time)
            if len(events_list) < 1:
                return

            try:
                self._process(events_list)
            except Exception as ex:
                LOG.error(ex)
            finally:
                self._release_processing_issuer(events_list[0].issuer_address)

    def _process(self, events_list: List[ScheduledEvents]):
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
                    self.sink.on_error_notification(
                        issuer_address=_event.issuer_address, code=0,
                        scheduled_event_id=_event.event_id, token_type=_event.token_type)
                    self.sink.flush()
                    continue
                keyfile_json = _account.keyfile
                decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                private_key = decode_keyfile_json(
                    raw_keyfile_json=keyfile_json,
                    password=decrypt_password.encode("utf-8")
                )
            except Exception as err:
                LOG.exception(f"Could not get the private key of the issuer of id:{_event.id}", err)
                self.sink.on_finish_event_process(
                    record_id=_event.id,
                    status=2
                )
                self.sink.on_error_notification(
                    issuer_address=_event.issuer_address, code=1,
                    scheduled_event_id=_event.event_id, token_type=_event.token_type)
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

                        # Register additional token info data
                        if "is_manual_transfer_approval" in _event.data:
                            self.sink.on_additional_token_info(
                                _event.token_address,
                                is_manual_transfer_approval=_event.data["is_manual_transfer_approval"]
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

                        # Register additional token info data
                        if "is_manual_transfer_approval" in _event.data:
                            self.sink.on_additional_token_info(
                                _event.token_address,
                                is_manual_transfer_approval=_event.data["is_manual_transfer_approval"]
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
                self.sink.on_error_notification(
                    issuer_address=_event.issuer_address, code=2,
                    scheduled_event_id=_event.event_id, token_type=_event.token_type)
            self.sink.flush()


class Worker:

    def __init__(self, db: scoped_session, thread_num: int):
        session = cast(Session, db)
        _sink = Sinks()
        _sink.register(DBSink(session))
        processor = Processor(sink=_sink, db=session, thread_num=thread_num)
        self.processor = processor

    def run(self):

        while True:
            started_at = time.time()
            try:
                self.processor.process()
            except Exception as ex:
                LOG.error(ex)
            sleeping_time = max(0, SCHEDULED_EVENTS_INTERVAL - (time.time() - started_at))
            time.sleep(sleeping_time)


def main():
    LOG.info("Service started successfully")

    for i in range(SCHEDULED_EVENTS_WORKER_COUNT):
        worker = Worker(db_session, i)
        thread = threading.Thread(target=worker.run)
        thread.setDaemon(True)
        thread.start()
        LOG.info(f"thread {i} started")

    while True:
        time.sleep(99999)


if __name__ == "__main__":
    main()
