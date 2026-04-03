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
from typing import Any, TypedDict, cast

import uvloop
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import HTTPProvider, Web3

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.db import AvalancheNode
from avalanche_config import (
    AVA_WEB3_HTTP_PROVIDER,
    AVA_WEB3_HTTP_PROVIDER_STANDBY,
    BLOCK_GENERATION_SPEED_THRESHOLD,
    BLOCK_SYNC_REMAINING_THRESHOLD,
    BLOCK_SYNC_STATUS_CALC_PERIOD,
    EXPECTED_BLOCK_GENERATION_PER_MIN,
)
from batch import free_malloc
from batch.utils import batch_log

"""
[PROCESSOR-Monitor-Block-Sync-Avalanche]

Processor for block synchronization monitoring for Avalanche node.
"""

process_name = "PROCESSOR-Monitor-Block-Sync-Avalanche"
LOG = batch_log.get_logger(process_name=process_name)


class HistoryData(TypedDict):
    time: float
    block_number: int


class RingBuffer:
    def __init__(self, size: int, default: HistoryData):
        self._next = 0
        self._buffer: list[HistoryData] = [default] * size

    def append(self, data: HistoryData) -> None:
        """Append data to the ring buffer, overwriting oldest data if full."""
        self._buffer[self._next] = data
        self._next = (self._next + 1) % len(self._buffer)

    def peek_oldest(self) -> HistoryData:
        """Get the oldest data in the ring buffer."""
        return self._buffer[self._next]


class NodeInfo(TypedDict):
    priority: int
    web3: Web3
    history: RingBuffer


class Processor:
    def __init__(self):
        self.node_info: dict[str, NodeInfo] = {}
        self.main_web3_provider: str = ""
        self.standby_web3_provider_list: list[str] = []
        self.valid_endpoint_uri_list: list[str] = []

    async def initial_setup(self):
        """Initial setup for the processor."""
        self.main_web3_provider = AVA_WEB3_HTTP_PROVIDER
        self.standby_web3_provider_list = AVA_WEB3_HTTP_PROVIDER_STANDBY
        self.valid_endpoint_uri_list = [
            AVA_WEB3_HTTP_PROVIDER,
            *AVA_WEB3_HTTP_PROVIDER_STANDBY,
        ]

        db_session = BatchAsyncSessionLocal()
        try:
            await self.__delete_old_node(
                db_session=db_session,
                valid_endpoint_uri_list=self.valid_endpoint_uri_list,
            )
            await self.__set_node_info(
                db_session=db_session,
                endpoint_uri=self.main_web3_provider,
                priority=0,
            )
            for endpoint_uri in self.standby_web3_provider_list:
                await self.__set_node_info(
                    db_session=db_session,
                    endpoint_uri=endpoint_uri,
                    priority=1,
                )
            await db_session.commit()
        finally:
            await db_session.close()

    async def process(self):
        """Process block synchronization monitoring for Avalanche nodes."""
        db_session = BatchAsyncSessionLocal()
        try:
            for endpoint_uri in self.node_info.keys():
                try:
                    await self.__process(
                        db_session=db_session, endpoint_uri=endpoint_uri
                    )
                except Exception:
                    await self.__web3_errors(
                        db_session=db_session,
                        endpoint_uri=endpoint_uri,
                    )
                    LOG.error(f"Node connection failed: {endpoint_uri}")
        finally:
            await db_session.close()

    @staticmethod
    async def __delete_old_node(
        db_session: AsyncSession,
        valid_endpoint_uri_list: list[str],
    ):
        """Delete old node data that is not in the valid endpoint URI list."""
        await db_session.execute(
            delete(AvalancheNode).where(
                AvalancheNode.endpoint_uri.not_in(valid_endpoint_uri_list)
            )
        )

    async def __set_node_info(
        self,
        db_session: AsyncSession,
        endpoint_uri: str,
        priority: int,
    ):
        """Set node info used for synchronization monitoring."""
        web3 = Web3(
            HTTPProvider(
                endpoint_uri,
                exception_retry_configuration=None,
            )
        )

        # Set node info before connectivity checks so __web3_errors can update DB
        # even when initialization fails.
        self.node_info[endpoint_uri] = {
            "priority": priority,
            "web3": web3,
            "history": RingBuffer(
                BLOCK_SYNC_STATUS_CALC_PERIOD,
                {
                    "time": time.time(),
                    "block_number": 0,
                },
            ),
        }

        try:
            latest_block_number = web3.eth.block_number
            block = web3.eth.get_block(
                max(latest_block_number - BLOCK_SYNC_STATUS_CALC_PERIOD, 0)
            )
        except Exception:
            await self.__web3_errors(db_session=db_session, endpoint_uri=endpoint_uri)
            LOG.error(f"Node connection failed: {endpoint_uri}")
            block = {"timestamp": time.time(), "number": 0}

        block_data = cast(dict[str, Any], block)

        history = RingBuffer(
            BLOCK_SYNC_STATUS_CALC_PERIOD,
            {
                "time": float(block_data.get("timestamp", time.time())),
                "block_number": int(block_data.get("number", 0)),
            },
        )
        self.node_info[endpoint_uri]["history"] = history

    async def __process(self, db_session: AsyncSession, endpoint_uri: str):
        is_synced = True
        errors: list[str] = []
        priority = self.node_info[endpoint_uri]["priority"]
        web3 = self.node_info[endpoint_uri]["web3"]
        history = self.node_info[endpoint_uri]["history"]

        syncing = cast(dict[str, Any] | bool, web3.eth.syncing)
        if isinstance(syncing, dict):
            remaining_blocks = int(syncing.get("highestBlock", 0)) - int(
                syncing.get("currentBlock", 0)
            )
            if remaining_blocks > BLOCK_SYNC_REMAINING_THRESHOLD:
                is_synced = False
                errors.append(
                    f"highestBlock={syncing.get('highestBlock')}, currentBlock={syncing.get('currentBlock')}"
                )

        latest_data: HistoryData = {
            "time": time.time(),
            "block_number": int(web3.eth.block_number),
        }
        oldest_data = history.peek_oldest()
        elapsed_time = latest_data["time"] - oldest_data["time"]
        generated_count = latest_data["block_number"] - oldest_data["block_number"]

        threshold = (
            elapsed_time / 60 * EXPECTED_BLOCK_GENERATION_PER_MIN
        ) * BLOCK_GENERATION_SPEED_THRESHOLD
        if generated_count < threshold:
            is_synced = False
            errors.append(f"{generated_count} blocks in {int(elapsed_time)} sec")

        history.append(latest_data)

        node: AvalancheNode | None = (
            await db_session.scalars(
                select(AvalancheNode)
                .where(AvalancheNode.endpoint_uri == endpoint_uri)
                .limit(1)
            )
        ).first()
        status_changed = node is None or node.is_synced != is_synced

        await self.__update_node_status(
            db_session=db_session,
            endpoint_uri=endpoint_uri,
            priority=priority,
            is_synced=is_synced,
        )

        if status_changed:
            if is_synced:
                LOG.info(f"{endpoint_uri} Block synchronization is working")
            else:
                LOG.error(f"{endpoint_uri} Block synchronization is down: %s", errors)
        elif not is_synced:
            LOG.warning(f"{endpoint_uri} Block synchronization is down: %s", errors)

        await db_session.commit()

    async def __web3_errors(self, db_session: AsyncSession, endpoint_uri: str):
        try:
            priority = self.node_info[endpoint_uri]["priority"]
            await self.__update_node_status(
                db_session=db_session,
                endpoint_uri=endpoint_uri,
                priority=priority,
                is_synced=False,
            )
            await db_session.commit()
        except Exception as ex:
            LOG.exception(ex)

    @staticmethod
    async def __update_node_status(
        db_session: AsyncSession,
        endpoint_uri: str,
        priority: int,
        is_synced: bool,
    ):
        node: AvalancheNode | None = (
            await db_session.scalars(
                select(AvalancheNode)
                .where(AvalancheNode.endpoint_uri == endpoint_uri)
                .limit(1)
            )
        ).first()
        if node is None:
            node = AvalancheNode()
            node.endpoint_uri = endpoint_uri
            node.priority = priority
            node.is_synced = is_synced
            db_session.add(node)
        else:
            node.is_synced = is_synced
            await db_session.merge(node)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()
    await processor.initial_setup()

    while True:
        try:
            await processor.process()
            LOG.debug("Processed")
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        await asyncio.sleep(60)
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
