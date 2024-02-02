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
from datetime import timedelta, timezone
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import Account, Token, TokenType
from batch import batch_log
from config import INDEXER_SYNC_INTERVAL

process_name = "INDEXER-Token-Cache"
LOG = batch_log.get_logger(process_name=process_name)

UTC = timezone(timedelta(hours=0), "UTC")


class Processor:
    @staticmethod
    async def process():
        db_session = BatchAsyncSessionLocal()
        try:
            token_list: Sequence[tuple[str, str]] = (
                (
                    await db_session.execute(
                        select(Token.type, Token.token_address)
                        .join(
                            Account,
                            and_(
                                Account.issuer_address == Token.issuer_address,
                                Account.is_deleted == False,
                            ),
                        )
                        .where(Token.token_status == 1)
                        .order_by(Token.created)
                    )
                )
                .tuples()
                .all()
            )
            for token_type, token_address in token_list:
                if token_type == TokenType.IBET_STRAIGHT_BOND:
                    await IbetStraightBondContract(token_address).get()
                elif token_type == TokenType.IBET_SHARE:
                    await IbetShareContract(token_address).get()
                await db_session.commit()
                LOG.debug(
                    f"token refreshed: token_type={token_type}, token_address={token_address}"
                )
                await asyncio.sleep(60)
        except Exception as e:
            await db_session.rollback()
            raise e
        finally:
            await db_session.close()
        LOG.info("Sync job has been completed")


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
