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

import uvloop
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import HTTPProvider, Web3

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.db import EthereumNode
from batch import free_malloc
from batch.utils import batch_log
from eth_config import (
    BLOCK_GENERATION_SPEED_THRESHOLD,
    BLOCK_SYNC_REMAINING_THRESHOLD,
    BLOCK_SYNC_STATUS_CALC_PERIOD,
    ETH_WEB3_HTTP_PROVIDER,
    ETH_WEB3_HTTP_PROVIDER_STANDBY,
    EXPECTED_BLOCK_GENERATION_PER_MIN,
)

"""
[PROCESSOR-Monitor-Block-Sync-Ethereum]

Processor for block synchronization monitoring for Ethereum node.
"""

process_name = "PROCESSOR-Monitor-Block-Sync-Ethereum"
LOG = batch_log.get_logger(process_name=process_name)


class RingBuffer:
    def __init__(self, size, default=None):
        self._next = 0
        self._buffer = [default] * size

    def append(self, data):
        """
        Append data to the ring buffer, overwriting the oldest data if full.
        """
        self._buffer[self._next] = data
        self._next = (self._next + 1) % len(self._buffer)

    def peek_oldest(self):
        """
        Get the oldest data in the ring buffer.
        """
        return self._buffer[self._next]


class Processor:
    def __init__(self):
        self.node_info = {}
        self.main_web3_provider = None
        self.standby_web3_provider_list = []
        self.valid_endpoint_uri_list = []

    async def initial_setup(self):
        """
        Initial setup for the processor.
        """
        self.main_web3_provider = ETH_WEB3_HTTP_PROVIDER
        self.standby_web3_provider_list = ETH_WEB3_HTTP_PROVIDER_STANDBY
        self.valid_endpoint_uri_list = (
            list(ETH_WEB3_HTTP_PROVIDER) + ETH_WEB3_HTTP_PROVIDER_STANDBY
        )
        db_session = BatchAsyncSessionLocal()
        try:
            # Delete old node data
            await self.__delete_old_node(
                db_session=db_session,
                valid_endpoint_uri_list=self.valid_endpoint_uri_list,
            )
            # Initialize settings
            await self.__set_node_info(
                db_session=db_session, endpoint_uri=self.main_web3_provider, priority=0
            )
            for _uri in self.standby_web3_provider_list:
                await self.__set_node_info(
                    db_session=db_session, endpoint_uri=_uri, priority=1
                )
            await db_session.commit()
        finally:
            await db_session.close()

    async def process(self):
        """
        Process the block synchronization monitoring for Ethereum nodes.
        """
        db_session = BatchAsyncSessionLocal()
        try:
            for endpoint_uri in self.node_info.keys():
                try:
                    await self.__process(
                        db_session=db_session, endpoint_uri=endpoint_uri
                    )
                except Exception:
                    await self.__web3_errors(
                        db_session=db_session, endpoint_uri=endpoint_uri
                    )
                    LOG.error(f"Node connection failed: {endpoint_uri}")
        finally:
            await db_session.close()

    @staticmethod
    async def __delete_old_node(
        db_session: AsyncSession, valid_endpoint_uri_list: list[str]
    ):
        """
        Delete old node data that is not in the valid endpoint URI list.
        """
        await db_session.execute(
            delete(EthereumNode).where(
                EthereumNode.endpoint_uri.not_in(valid_endpoint_uri_list)
            )
        )

    async def __set_node_info(
        self, db_session: AsyncSession, endpoint_uri: str, priority: int
    ):
        """
        Set the node information for block synchronization monitoring.
        """
        self.node_info[endpoint_uri] = {}

        # Set node priority
        self.node_info[endpoint_uri]["priority"] = priority

        # Set web3 instance for the node
        # - Diable retry logic explicitly to avoid retrying on connection errors,
        web3 = Web3(
            HTTPProvider(
                endpoint_uri,
                exception_retry_configuration=None,
            )
        )
        self.node_info[endpoint_uri]["web3"] = web3

        # Get starting point for block monitoring
        try:
            # NOTE:
            #   Since monitoring data is not retained immediately after processing,
            #   the previous block number is retrieved.
            latest_block_number = web3.eth.block_number
            block = web3.eth.get_block(
                max(latest_block_number - BLOCK_SYNC_STATUS_CALC_PERIOD, 0)
            )
        except Exception:
            await self.__web3_errors(db_session=db_session, endpoint_uri=endpoint_uri)
            LOG.error(f"Node connection failed: {endpoint_uri}")
            block = {"timestamp": time.time(), "number": 0}

        # Initialize history for block synchronization status
        history = RingBuffer(
            BLOCK_SYNC_STATUS_CALC_PERIOD,
            {"time": block["timestamp"], "block_number": block["number"]},
        )
        self.node_info[endpoint_uri]["history"] = history

    async def __process(self, db_session: AsyncSession, endpoint_uri: str):
        is_synced = True
        errors = []
        priority: int = self.node_info[endpoint_uri]["priority"]
        web3: Web3 = self.node_info[endpoint_uri]["web3"]
        history: RingBuffer = self.node_info[endpoint_uri]["history"]

        # Check block synchronization status
        syncing = web3.eth.syncing
        if syncing:
            remaining_blocks = syncing["highestBlock"] - syncing["currentBlock"]
            if remaining_blocks > BLOCK_SYNC_REMAINING_THRESHOLD:
                # If the remaining blocks are more than the threshold(2 blocks), mark as not synced
                is_synced = False
                errors.append(
                    f"highestBlock={syncing['highestBlock']}, currentBlock={syncing['currentBlock']}"
                )

        # Check block generation speed
        latest_block_number = web3.eth.block_number
        latest_data = {"time": time.time(), "block_number": latest_block_number}

        oldest_data = history.peek_oldest()
        elapsed_time = latest_data["time"] - oldest_data["time"]
        generated_count = latest_data["block_number"] - oldest_data["block_number"]

        threshold = (
            elapsed_time / 60 * EXPECTED_BLOCK_GENERATION_PER_MIN
        ) * BLOCK_GENERATION_SPEED_THRESHOLD
        if generated_count < threshold:
            # If the generated block count is less than the threshold, mark as not synced
            is_synced = False
            errors.append(f"{generated_count} blocks in {int(elapsed_time)} sec")

        history.append(latest_data)

        # Update node status in the database
        _node: EthereumNode | None = (
            await db_session.scalars(
                select(EthereumNode)
                .where(EthereumNode.endpoint_uri == endpoint_uri)
                .limit(1)
            )
        ).first()
        status_changed = (
            False if _node is not None and _node.is_synced == is_synced else True
        )
        await self.__update_node_status(
            db_session=db_session,
            endpoint_uri=endpoint_uri,
            priority=priority,
            is_synced=is_synced,
        )

        # Output logs
        if status_changed:
            if is_synced:
                LOG.info(f"{endpoint_uri} Block synchronization is working")
            else:
                LOG.error(f"{endpoint_uri} Block synchronization is down: %s", errors)
        else:
            if not is_synced:
                # If the same previous processing status, log output with WARING level.
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
            # Unexpected errors(DB error, etc)
            LOG.exception(ex)

    @staticmethod
    async def __update_node_status(
        db_session: AsyncSession, endpoint_uri: str, priority: int, is_synced: bool
    ):
        _node: EthereumNode | None = (
            await db_session.scalars(
                select(EthereumNode)
                .where(EthereumNode.endpoint_uri == endpoint_uri)
                .limit(1)
            )
        ).first()
        if _node is not None:
            _node.is_synced = is_synced
            await db_session.merge(_node)
        else:
            _node = EthereumNode()
            _node.endpoint_uri = endpoint_uri
            _node.priority = priority
            _node.is_synced = is_synced
            db_session.add(_node)


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

        await asyncio.sleep(60)  # Sleep for a minute before the next processing
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
