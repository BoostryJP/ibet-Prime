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

import asyncio
import sys
import time
import uuid
from datetime import datetime
from typing import List, Optional, Sequence, Set

import uvloop
from eth_keyfile import decode_keyfile_json
from sqlalchemy import and_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import (
    ContractRevertError,
    SendTransactionError,
    ServiceUnavailableError,
)
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    Account,
    Notification,
    NotificationType,
    ScheduledEvents,
    ScheduledEventType,
    TokenType,
    TokenUpdateOperationCategory,
    TokenUpdateOperationLog,
)
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import batch_log
from config import SCHEDULED_EVENTS_INTERVAL, SCHEDULED_EVENTS_WORKER_COUNT

"""
[PROCESSOR-Scheduled-Events]

Processor for scheduled token update events
"""

process_name = "PROCESSOR-Scheduled-Events"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


class Processor:
    def __init__(self, worker_num: int):
        self.worker_num = worker_num

    async def process(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            process_start_time = datetime.utcnow()
            while True:
                events_list = await self.__get_events_of_one_issuer(
                    db_session=db_session, filter_time=process_start_time
                )
                if len(events_list) < 1:
                    return

                try:
                    await self.__process(db_session=db_session, events_list=events_list)
                except Exception as ex:
                    LOG.error(ex)
                finally:
                    await self.__release_processing_issuer(
                        events_list[0].issuer_address
                    )
        finally:
            await db_session.close()

    @staticmethod
    async def __get_events_of_one_issuer(
        db_session: AsyncSession, filter_time: datetime
    ):
        async with lock:
            event: Optional[ScheduledEvents] = (
                await db_session.scalars(
                    select(ScheduledEvents)
                    .where(
                        and_(
                            ScheduledEvents.status == 0,
                            ScheduledEvents.scheduled_datetime <= filter_time,
                            ScheduledEvents.issuer_address.notin_(processing_issuers),
                        )
                    )
                    .order_by(ScheduledEvents.scheduled_datetime, ScheduledEvents.id)
                    .limit(1)
                )
            ).first()
            if event is None:
                return []
            issuer_address = event.issuer_address
            processing_issuers.add(issuer_address)

        events_list: Sequence[ScheduledEvents] = (
            await db_session.scalars(
                select(ScheduledEvents)
                .where(
                    and_(
                        ScheduledEvents.status == 0,
                        ScheduledEvents.scheduled_datetime <= filter_time,
                        ScheduledEvents.issuer_address == issuer_address,
                    )
                )
                .order_by(ScheduledEvents.scheduled_datetime, ScheduledEvents.id)
            )
        ).all()
        return events_list

    @staticmethod
    async def __release_processing_issuer(issuer_address: str):
        async with lock:
            processing_issuers.remove(issuer_address)

    async def __process(
        self, db_session: AsyncSession, events_list: List[ScheduledEvents]
    ):
        for _event in events_list:
            LOG.info(f"<{self.worker_num}> Process start: upload_id={_event.id}")

            _upload_status = 1

            # Get issuer's private key
            try:
                _account: Account | None = (
                    await db_session.scalars(
                        select(Account)
                        .where(Account.issuer_address == _event.issuer_address)
                        .limit(1)
                    )
                ).first()
                if (
                    _account is None
                ):  # If issuer does not exist, update the status of the upload to ERROR
                    LOG.warning(f"Issuer of the event_id:{_event.id} does not exist")
                    await self.__sink_on_finish_event_process(
                        db_session=db_session, record_id=_event.id, status=2
                    )
                    await self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_event.issuer_address,
                        code=0,
                        scheduled_event_id=_event.event_id,
                        token_type=_event.token_type,
                        token_address=_event.token_address,
                    )
                    await db_session.commit()
                    continue
                keyfile_json = _account.keyfile
                decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                private_key = decode_keyfile_json(
                    raw_keyfile_json=keyfile_json,
                    password=decrypt_password.encode("utf-8"),
                )
            except Exception:
                LOG.exception(
                    f"Could not get the private key of the issuer of id:{_event.id}"
                )
                await self.__sink_on_finish_event_process(
                    db_session=db_session, record_id=_event.id, status=2
                )
                await self.__sink_on_error_notification(
                    db_session=db_session,
                    issuer_address=_event.issuer_address,
                    code=1,
                    scheduled_event_id=_event.event_id,
                    token_type=_event.token_type,
                    token_address=_event.token_address,
                )
                await db_session.commit()
                continue

            try:
                # Token_type
                if _event.token_type == TokenType.IBET_SHARE.value:
                    # Update
                    if _event.event_type == ScheduledEventType.UPDATE.value:
                        token_contract = IbetShareContract(_event.token_address)
                        original_contents = (await token_contract.get()).__dict__
                        _update_data = IbetShareUpdateParams(**_event.data)
                        await token_contract.update(
                            data=_update_data,
                            tx_from=_event.issuer_address,
                            private_key=private_key,
                        )
                        await self.__sink_on_token_update_operation_log(
                            db_session=db_session,
                            token_address=_event.token_address,
                            issuer_address=_event.issuer_address,
                            token_type=_event.token_type,
                            arguments=_update_data.model_dump(exclude_none=True),
                            original_contents=original_contents,
                        )

                elif _event.token_type == TokenType.IBET_STRAIGHT_BOND.value:
                    # Update
                    if _event.event_type == ScheduledEventType.UPDATE.value:
                        token_contract = IbetStraightBondContract(_event.token_address)
                        original_contents = (await token_contract.get()).__dict__
                        _update_data = IbetStraightBondUpdateParams(**_event.data)
                        await IbetStraightBondContract(_event.token_address).update(
                            data=_update_data,
                            tx_from=_event.issuer_address,
                            private_key=private_key,
                        )
                        await self.__sink_on_token_update_operation_log(
                            db_session=db_session,
                            token_address=_event.token_address,
                            issuer_address=_event.issuer_address,
                            token_type=_event.token_type,
                            arguments=_update_data.model_dump(exclude_none=True),
                            original_contents=original_contents,
                        )

                await self.__sink_on_finish_event_process(
                    db_session=db_session, record_id=_event.id, status=1
                )
            except ContractRevertError as e:
                LOG.warning(
                    f"Transaction reverted: id=<{_event.id}> error_code:<{e.code}> error_msg:<{e.message}>"
                )
                await self.__sink_on_finish_event_process(
                    db_session=db_session, record_id=_event.id, status=2
                )
                await self.__sink_on_error_notification(
                    db_session=db_session,
                    issuer_address=_event.issuer_address,
                    code=2,
                    scheduled_event_id=_event.event_id,
                    token_type=_event.token_type,
                    token_address=_event.token_address,
                )
            except SendTransactionError:
                LOG.warning(f"Failed to send transaction: id=<{_event.id}>")
                await self.__sink_on_finish_event_process(
                    db_session=db_session, record_id=_event.id, status=2
                )
                await self.__sink_on_error_notification(
                    db_session=db_session,
                    issuer_address=_event.issuer_address,
                    code=2,
                    scheduled_event_id=_event.event_id,
                    token_type=_event.token_type,
                    token_address=_event.token_address,
                )
            await db_session.commit()

            LOG.info(f"<{self.worker_num}> Process end: upload_id={_event.id}")

    @staticmethod
    async def __sink_on_finish_event_process(
        db_session: AsyncSession, record_id: int, status: int
    ):
        await db_session.execute(
            update(ScheduledEvents)
            .where(ScheduledEvents.id == record_id)
            .values(status=status)
        )

    @staticmethod
    async def __sink_on_error_notification(
        db_session: AsyncSession,
        issuer_address: str,
        code: int,
        scheduled_event_id: str,
        token_type: str,
        token_address: str,
    ):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = NotificationType.SCHEDULE_EVENT_ERROR
        notification.code = code
        notification.metainfo = {
            "scheduled_event_id": scheduled_event_id,
            "token_type": token_type,
            "token_address": token_address,
        }
        db_session.add(notification)

    @staticmethod
    async def __sink_on_token_update_operation_log(
        db_session: AsyncSession,
        token_address: str,
        issuer_address: str,
        token_type: str,
        arguments: dict,
        original_contents: dict,
    ):
        operation_log = TokenUpdateOperationLog()
        operation_log.token_address = token_address
        operation_log.issuer_address = issuer_address
        operation_log.type = token_type
        operation_log.arguments = arguments
        operation_log.original_contents = original_contents
        operation_log.operation_category = TokenUpdateOperationCategory.UPDATE.value
        db_session.add(operation_log)


# Lock object for exclusion control
lock = asyncio.Lock()
# Issuer being processed in workers
processing_issuers: Set[str] = set()


class Worker:
    def __init__(self, worker_num: int):
        processor = Processor(worker_num=worker_num)
        self.processor = processor

    async def run(self):
        while True:
            started_at = time.time()
            try:
                await self.processor.process()
            except ServiceUnavailableError:
                LOG.warning("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )

            await asyncio.sleep(
                max(0, SCHEDULED_EVENTS_INTERVAL - (time.time() - started_at))
            )


async def main():
    LOG.info("Service started successfully")

    workers = [Worker(i) for i in range(SCHEDULED_EVENTS_WORKER_COUNT)]
    try:
        await SemaphoreTaskGroup.run(
            *[worker.run() for worker in workers],
            max_concurrency=SCHEDULED_EVENTS_WORKER_COUNT,
        )
    except ExceptionGroup:
        LOG.exception("Processor went down")
        sys.exit(1)


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
