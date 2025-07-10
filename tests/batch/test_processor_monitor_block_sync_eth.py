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

from unittest import mock
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from web3 import Web3

from app.model.db import EthereumNode
from batch.processor_monitor_block_sync_eth import Processor
from eth_config import ETH_WEB3_HTTP_PROVIDER

web3 = Web3(Web3.HTTPProvider(ETH_WEB3_HTTP_PROVIDER))


@pytest.fixture(scope="function")
def processor(async_db):
    return Processor()


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 1st run: Normal state
    # 2nd run: Abnormal state - Setting BLOCK_GENERATION_SPEED_THRESHOLD to 100% triggers an error.
    # 3rd run: Returns to normal state
    # 4th run: Abnormal state - An error occurs when the difference between highestBlock and currentBlock exceeds the threshold.
    # 5th run: Returns to normal state - No error occurs since the difference between highestBlock and currentBlock is within the threshold.
    @mock.patch(
        "batch.processor_monitor_block_sync_eth.ETH_WEB3_HTTP_PROVIDER",
        ETH_WEB3_HTTP_PROVIDER,
    )
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, async_db):
        await processor.initial_setup()

        # Run 1st: Normal state
        await processor.process()
        async_db.expire_all()

        await async_db.rollback()
        _node = (await async_db.scalars(select(EthereumNode).limit(1))).first()
        assert _node.id == 1
        assert _node.endpoint_uri == ETH_WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True

        # Run 2nd: Abnormal state
        # - Setting BLOCK_GENERATION_SPEED_THRESHOLD to 100% will trigger an error.
        with mock.patch(
            "batch.processor_monitor_block_sync_eth.BLOCK_GENERATION_SPEED_THRESHOLD",
            100,
        ):
            await processor.process()
            await async_db.rollback()
            async_db.expire_all()

        _node = (await async_db.scalars(select(EthereumNode).limit(1))).first()
        assert _node.is_synced == False

        # Run 3rd: Return to normal state
        await processor.process()
        await async_db.rollback()
        async_db.expire_all()

        _node = (await async_db.scalars(select(EthereumNode).limit(1))).first()
        assert _node.is_synced == True

        # Run 4th: Abnormal state
        # - An error occurs when the difference between highestBlock and currentBlock exceeds a threshold.
        block_number = web3.eth.block_number
        is_syncing_mock = MagicMock()
        is_syncing_mock.return_value = {
            "highestBlock": block_number,
            "currentBlock": block_number - 3,
        }
        with mock.patch("web3.eth.Eth.syncing", is_syncing_mock()):
            await processor.process()
            await async_db.rollback()
            async_db.expire_all()

        _node = (await async_db.scalars(select(EthereumNode).limit(1))).first()
        assert _node.is_synced == False

        # Run 5th: Return to normal state
        # - Since the difference between highestBlock and currentBlock is within the threshold, no error occurs.
        block_number = web3.eth.block_number
        is_syncing_mock = MagicMock()
        is_syncing_mock.return_value = {
            "highestBlock": block_number,
            "currentBlock": block_number - 2,
        }
        with mock.patch("web3.eth.Eth.syncing", is_syncing_mock()):
            await processor.process()
            await async_db.rollback()
            async_db.expire_all()

        _node = (await async_db.scalars(select(EthereumNode).limit(1))).first()
        assert _node.is_synced == True

    # <Normal_2>
    # Node stopped → started
    @mock.patch(
        "batch.processor_monitor_block_sync_eth.ETH_WEB3_HTTP_PROVIDER_STANDBY",
        ["http://localhost:1000"],
    )
    @pytest.mark.asyncio
    async def test_normal_2(self, processor, async_db):
        await processor.initial_setup()
        await async_db.rollback()

        # pre assertion
        _node = (await async_db.scalars(select(EthereumNode).limit(1))).first()
        assert _node.id == 1
        assert _node.endpoint_uri == "http://localhost:1000"
        assert _node.priority == 1
        assert _node.is_synced == False

        # node sync(processing)
        org_value = processor.node_info["http://localhost:1000"][
            "web3"
        ].manager.provider.endpoint_uri
        processor.node_info["http://localhost:1000"][
            "web3"
        ].manager.provider.endpoint_uri = (
            ETH_WEB3_HTTP_PROVIDER  # Temporarily replace setting values
        )
        await processor.process()
        await async_db.rollback()
        async_db.expire_all()

        processor.node_info["http://localhost:1000"][
            "web3"
        ].manager.provider.endpoint_uri = org_value

        # assertion
        _node = (
            await async_db.scalars(
                select(EthereumNode)
                .where(EthereumNode.endpoint_uri == "http://localhost:1000")
                .limit(1)
            )
        ).first()
        assert _node.is_synced == True

    # <Normal_3>
    # Delete old node data
    @pytest.mark.asyncio
    async def test_normal_3(self, processor, async_db):
        node = EthereumNode()
        node.id = 1
        node.endpoint_uri = "old_node"
        node.priority = 1
        node.is_synced = True
        async_db.add(node)
        await async_db.commit()

        await processor.initial_setup()

        # assertion-1
        old_node = (await async_db.scalars(select(EthereumNode))).all()
        assert len(old_node) == 0

        # process
        await processor.process()
        await async_db.rollback()
        async_db.expire_all()

        # assertion-2
        new_node = (await async_db.scalars(select(EthereumNode).limit(1))).first()
        assert new_node.id == 1
        assert new_node.endpoint_uri == ETH_WEB3_HTTP_PROVIDER
        assert new_node.priority == 0
        assert new_node.is_synced == True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Node down (At initialization)
    @mock.patch(
        "batch.processor_monitor_block_sync_eth.ETH_WEB3_HTTP_PROVIDER",
        ETH_WEB3_HTTP_PROVIDER,
    )
    @mock.patch(
        "batch.processor_monitor_block_sync_eth.ETH_WEB3_HTTP_PROVIDER_STANDBY",
        ["http://localhost:1000", "http://localhost:2000"],
    )
    @pytest.mark.asyncio
    async def test_error_1(self, processor, async_db):
        await processor.initial_setup()
        await async_db.rollback()

        # assertion
        _node_list = (
            await async_db.scalars(select(EthereumNode).order_by(EthereumNode.id))
        ).all()
        assert len(_node_list) == 2

        _node = _node_list[0]
        assert _node.id == 1
        assert _node.endpoint_uri == "http://localhost:1000"
        assert _node.priority == 1
        assert _node.is_synced == False

        _node = _node_list[1]
        assert _node.id == 2
        assert _node.endpoint_uri == "http://localhost:2000"
        assert _node.priority == 1
        assert _node.is_synced == False

    # <Error_2>
    # Node down (After processed)
    @mock.patch(
        "batch.processor_monitor_block_sync_eth.ETH_WEB3_HTTP_PROVIDER",
        ETH_WEB3_HTTP_PROVIDER,
    )
    @mock.patch(
        "batch.processor_monitor_block_sync_eth.ETH_WEB3_HTTP_PROVIDER_STANDBY",
        ["http://localhost:1000", "http://localhost:2000"],
    )
    @pytest.mark.asyncio
    async def test_error_2(self, processor, async_db):
        await processor.initial_setup()
        await processor.process()
        await async_db.rollback()
        async_db.expire_all()

        # assertion
        _node_list = (
            await async_db.scalars(select(EthereumNode).order_by(EthereumNode.id))
        ).all()
        assert len(_node_list) == 3

        _node = _node_list[0]
        assert _node.id == 1
        assert _node.endpoint_uri == "http://localhost:1000"
        assert _node.priority == 1
        assert _node.is_synced == False

        _node = _node_list[1]
        assert _node.id == 2
        assert _node.endpoint_uri == "http://localhost:2000"
        assert _node.priority == 1
        assert _node.is_synced == False

        _node = _node_list[2]
        assert _node.id == 3
        assert _node.endpoint_uri == ETH_WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True
