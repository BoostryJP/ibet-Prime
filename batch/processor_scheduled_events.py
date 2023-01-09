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
from typing import (
    List,
    Set,
    Optional
)

from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from datetime import datetime
from config import (
    DATABASE_URL,
    SCHEDULED_EVENTS_INTERVAL,
    SCHEDULED_EVENTS_WORKER_COUNT
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import Web3Wrapper
from app.model.db import (
    Account,
    ScheduledEvents,
    ScheduledEventType,
    TokenType,
    Notification,
    NotificationType
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract
)
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams
)
from app.exceptions import (
    SendTransactionError,
    ServiceUnavailableError,
    ContractRevertError
)
import batch_log

"""
[PROCESSOR-Scheduled-Events]

Processor for scheduled token update events
"""

process_name = "PROCESSOR-Scheduled-Events"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

lock = threading.Lock()
# Issuer being processed in threads
processing_issuers: Set[str] = set()


class Processor:
    def __init__(self, thread_num: int):
        self.thread_num = thread_num

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            process_start_time = datetime.utcnow()
            while True:
                events_list = self.__get_events_of_one_issuer(
                    db_session=db_session,
                    filter_time=process_start_time
                )
                if len(events_list) < 1:
                    return

                try:
                    self.__process(db_session=db_session, events_list=events_list)
                except Exception as ex:
                    LOG.error(ex)
                finally:
                    self.__release_processing_issuer(events_list[0].issuer_address)
        finally:
            db_session.close()

    def __get_events_of_one_issuer(self, db_session: Session, filter_time: datetime) -> List[ScheduledEvents]:
        with lock:
            event: Optional[ScheduledEvents] = db_session.query(ScheduledEvents). \
                filter(ScheduledEvents.status == 0). \
                filter(ScheduledEvents.scheduled_datetime <= filter_time). \
                filter(ScheduledEvents.issuer_address.notin_(processing_issuers)). \
                order_by(ScheduledEvents.scheduled_datetime, ScheduledEvents.id). \
                first()
            if event is None:
                return []
            issuer_address = event.issuer_address
            processing_issuers.add(issuer_address)

        events_list: List[ScheduledEvents] = db_session.query(ScheduledEvents). \
            filter(ScheduledEvents.status == 0). \
            filter(ScheduledEvents.scheduled_datetime <= filter_time). \
            filter(ScheduledEvents.issuer_address == issuer_address). \
            order_by(ScheduledEvents.scheduled_datetime, ScheduledEvents.id). \
            all()
        return events_list

    def __release_processing_issuer(self, issuer_address: str):
        with lock:
            processing_issuers.remove(issuer_address)

    def __process(self, db_session: Session, events_list: List[ScheduledEvents]):
        for _event in events_list:
            LOG.info(f"<{self.thread_num}> Process start: upload_id={_event.id}")

            _upload_status = 1

            # Get issuer's private key
            try:
                _account = db_session.query(Account). \
                    filter(Account.issuer_address == _event.issuer_address). \
                    first()
                if _account is None:  # If issuer does not exist, update the status of the upload to ERROR
                    LOG.warning(f"Issuer of the event_id:{_event.id} does not exist")
                    self.__sink_on_finish_event_process(
                        db_session=db_session,
                        record_id=_event.id,
                        status=2
                    )
                    self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_event.issuer_address, code=0,
                        scheduled_event_id=_event.event_id,
                        token_type=_event.token_type,
                        token_address=_event.token_address
                    )
                    db_session.commit()
                    continue
                keyfile_json = _account.keyfile
                decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                private_key = decode_keyfile_json(
                    raw_keyfile_json=keyfile_json,
                    password=decrypt_password.encode("utf-8")
                )
            except Exception:
                LOG.exception(f"Could not get the private key of the issuer of id:{_event.id}")
                self.__sink_on_finish_event_process(
                    db_session=db_session,
                    record_id=_event.id,
                    status=2
                )
                self.__sink_on_error_notification(
                    db_session=db_session,
                    issuer_address=_event.issuer_address, code=1,
                    scheduled_event_id=_event.event_id,
                    token_type=_event.token_type,
                    token_address=_event.token_address
                )
                db_session.commit()
                continue

            try:
                # Token_type
                if _event.token_type == TokenType.IBET_SHARE.value:
                    # Update
                    if _event.event_type == ScheduledEventType.UPDATE.value:
                        _update_data = IbetShareUpdateParams(**_event.data)
                        IbetShareContract.update(
                            contract_address=_event.token_address,
                            data=_update_data,
                            tx_from=_event.issuer_address,
                            private_key=private_key
                        )
                elif _event.token_type == TokenType.IBET_STRAIGHT_BOND.value:
                    # Update
                    if _event.event_type == ScheduledEventType.UPDATE.value:
                        _update_data = IbetStraightBondUpdateParams(**_event.data)
                        IbetStraightBondContract.update(
                            contract_address=_event.token_address,
                            data=_update_data,
                            tx_from=_event.issuer_address,
                            private_key=private_key
                        )

                self.__sink_on_finish_event_process(
                    db_session=db_session,
                    record_id=_event.id,
                    status=1
                )
            except ContractRevertError as e:
                LOG.warning(f"Transaction reverted: id=<{_event.id}> error_code:<{e.code}> error_msg:<{e.message}>")
                self.__sink_on_finish_event_process(
                    db_session=db_session,
                    record_id=_event.id,
                    status=2
                )
                self.__sink_on_error_notification(
                    db_session=db_session,
                    issuer_address=_event.issuer_address,
                    code=2,
                    scheduled_event_id=_event.event_id,
                    token_type=_event.token_type,
                    token_address=_event.token_address
                )
            except SendTransactionError:
                LOG.warning(f"Failed to send transaction: id=<{_event.id}>")
                self.__sink_on_finish_event_process(
                    db_session=db_session,
                    record_id=_event.id,
                    status=2
                )
                self.__sink_on_error_notification(
                    db_session=db_session,
                    issuer_address=_event.issuer_address,
                    code=2,
                    scheduled_event_id=_event.event_id,
                    token_type=_event.token_type,
                    token_address=_event.token_address
                )
            db_session.commit()

            LOG.info(f"<{self.thread_num}> Process end: upload_id={_event.id}")

    @staticmethod
    def __sink_on_finish_event_process(db_session: Session, record_id: int, status: int):
        scheduled_event_record = db_session.query(ScheduledEvents). \
            filter(ScheduledEvents.id == record_id). \
            first()
        if scheduled_event_record is not None:
            scheduled_event_record.status = status
            db_session.merge(scheduled_event_record)

    @staticmethod
    def __sink_on_error_notification(db_session: Session,
                                     issuer_address: str,
                                     code: int,
                                     scheduled_event_id: str,
                                     token_type: str,
                                     token_address: str):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.SCHEDULE_EVENT_ERROR
        notification.code = code
        notification.metainfo = {
            "scheduled_event_id": scheduled_event_id,
            "token_type": token_type,
            "token_address": token_address
        }
        db_session.add(notification)


class Worker:

    def __init__(self, thread_num: int):
        processor = Processor(thread_num=thread_num)
        self.processor = processor

    def run(self):

        while True:
            started_at = time.time()
            try:
                self.processor.process()
            except ServiceUnavailableError:
                LOG.warning("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
            except Exception as ex:
                LOG.error(ex)
            sleeping_time = max(0, SCHEDULED_EVENTS_INTERVAL - (time.time() - started_at))
            time.sleep(sleeping_time)


def main():
    LOG.info("Service started successfully")

    for i in range(SCHEDULED_EVENTS_WORKER_COUNT):
        worker = Worker(i)
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()
        LOG.debug(f"thread {i} started")

    while True:
        time.sleep(99999)


if __name__ == "__main__":
    main()
