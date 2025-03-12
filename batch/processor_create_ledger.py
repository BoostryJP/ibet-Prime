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
from asyncio import Event
from datetime import UTC, datetime, timedelta
from typing import Sequence

import uvloop
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
)
from app.model.db import (
    LedgerCreationRequest,
    LedgerCreationStatus,
    TokenType,
)
from app.utils.ledger_utils import (
    finalize_ledger,
    sync_request_with_registered_personal_info,
)
from batch import free_malloc
from batch.utils import batch_log
from batch.utils.signal_handler import setup_signal_handler

"""
[PROCESSOR-Create-Ledger]

- The processor creates the ledger as instructed in the creation request.
- Once all the holder's personal information has been registered (up to a maximum of 6 hours), 
  it finalizes the record as the official ledger.
"""

process_name = "PROCESSOR-Create-Ledger"
LOG = batch_log.get_logger(process_name=process_name)


class Processor:
    def __init__(self, is_shutdown: Event):
        self.is_shutdown = is_shutdown

    async def process(self):
        db: AsyncSession = BatchAsyncSessionLocal()

        try:
            LOG.info("Process Start")

            req_list: Sequence[LedgerCreationRequest] = (
                await db.scalars(
                    select(LedgerCreationRequest).where(
                        LedgerCreationRequest.status == LedgerCreationStatus.PROCESSING
                    )
                )
            ).all()
            for req in req_list:
                # Graceful shutdown
                if self.is_shutdown.is_set():
                    return

                # Get token attributes
                if req.token_type == TokenType.IBET_SHARE:
                    token_contract: IbetShareContract = await IbetShareContract(
                        req.token_address
                    ).get()
                elif req.token_type == TokenType.IBET_STRAIGHT_BOND:
                    token_contract: IbetStraightBondContract = (
                        await IbetStraightBondContract(req.token_address).get()
                    )

                # Sync ledger creation request data with registered personal info
                (
                    initial_unset_count,
                    final_set_count,
                ) = await sync_request_with_registered_personal_info(
                    db=db,
                    request_id=req.request_id,
                    issuer_address=token_contract.issuer_address,
                )
                LOG.info(
                    f"Personal information fields have been updated: {req.request_id} {final_set_count}/{initial_unset_count}"
                )

                # Finalize the creation of the ledger
                # - 1) If all the holder's personal information has been set.
                # - 2) If more than 6 hours have passed since the creation request.
                if initial_unset_count == final_set_count:
                    await finalize_ledger(
                        db=db,
                        request_id=req.request_id,
                        token_address=token_contract.token_address,
                        currency_code=token_contract.face_value_currency
                        if req.token_type == TokenType.IBET_STRAIGHT_BOND
                        else None,
                    )
                    req.status = LedgerCreationStatus.COMPLETED
                    await db.merge(req)
                    LOG.info(
                        f"The ledger has been created: {req.request_id} {token_contract.token_address}"
                    )
                elif req.created + timedelta(hours=6) < datetime.now(UTC).replace(
                    tzinfo=None
                ):
                    await finalize_ledger(
                        db=db,
                        request_id=req.request_id,
                        token_address=token_contract.token_address,
                        currency_code=token_contract.face_value_currency
                        if type(token_contract) is IbetStraightBondContract
                        else None,
                        some_personal_info_not_registered=True,
                    )
                    req.status = LedgerCreationStatus.COMPLETED
                    await db.merge(req)
                    LOG.info(
                        f"The ledger has been created (time limit exceeded): {req.request_id} {token_contract.token_address}"
                    )

                await db.commit()

            LOG.info("Process End")
        finally:
            await db.close()


async def main():
    LOG.info("Service started successfully")

    is_shutdown = asyncio.Event()
    setup_signal_handler(logger=LOG, is_shutdown=is_shutdown)

    processor = Processor(is_shutdown)

    try:
        while not is_shutdown.is_set():
            try:
                await processor.process()
            except ServiceUnavailableError:
                LOG.warning("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )
            except Exception:
                LOG.exception("An error occurred during processing")

            await asyncio.sleep(10)
            free_malloc()
    finally:
        LOG.info("Service is shutdown")


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
