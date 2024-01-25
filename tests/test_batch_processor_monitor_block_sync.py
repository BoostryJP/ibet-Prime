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
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model.db import Node
from batch.processor_monitor_block_sync import Processor
from config import WEB3_HTTP_PROVIDER

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def processor(db):
    return Processor()


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Execute Batch Run 1st: synced
    # Execute Batch Run 2nd: block generation speed down(same the previous)
    # Execute Batch Run 3rd: synced
    # Execute Batch Run 4th: node syncing(DIFF:over 2)
    # Execute Batch Run 5th: node syncing(DIFF:2) == synced
    @mock.patch(
        "batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER",
        WEB3_HTTP_PROVIDER,
    )
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, db):
        await processor.initial_setup()

        # Run 1st: synced
        await processor.process()

        db.rollback()
        _node = db.scalars(select(Node).limit(1)).first()
        assert _node.id == 1
        assert _node.endpoint_uri == WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True

        # Run 2nd: block generation speed down(same the previous)
        with mock.patch(
            "batch.processor_monitor_block_sync.BLOCK_GENERATION_SPEED_THRESHOLD", 100
        ):
            await processor.process()

        db.rollback()
        _node = db.scalars(select(Node).limit(1)).first()
        assert _node.is_synced == False

        # Run 3rd: synced
        await processor.process()

        db.rollback()
        _node = db.scalars(select(Node).limit(1)).first()
        assert _node.is_synced == True

        # Run 4th: node syncing(DIFF:over 2)
        block_number = web3.eth.block_number
        is_syncing_mock = AsyncMock()
        is_syncing_mock.return_value = {
            "highestBlock": block_number,
            "currentBlock": block_number - 3,
        }
        with mock.patch("web3.eth.async_eth.AsyncEth.syncing", is_syncing_mock()):
            await processor.process()

        db.rollback()
        _node = db.scalars(select(Node).limit(1)).first()
        assert _node.is_synced == False

        # Run 5th: node syncing(DIFF:2) == synced
        block_number = web3.eth.block_number
        is_syncing_mock = AsyncMock()
        is_syncing_mock.return_value = {
            "highestBlock": block_number,
            "currentBlock": block_number - 2,
        }
        with mock.patch("web3.eth.async_eth.AsyncEth.syncing", is_syncing_mock()):
            await processor.process()

        db.rollback()
        _node = db.scalars(select(Node).limit(1)).first()
        assert _node.is_synced == True

    # <Normal_2>
    # Node stopped → started
    @mock.patch(
        "batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER_STANDBY",
        ["http://localhost:1000"],
    )
    @pytest.mark.asyncio
    async def test_normal_2(self, processor, db):
        await processor.initial_setup()

        # pre assertion
        db.rollback()
        _node = db.scalars(select(Node).limit(1)).first()
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
            WEB3_HTTP_PROVIDER  # Temporarily replace setting values
        )
        await processor.process()

        processor.node_info["http://localhost:1000"][
            "web3"
        ].manager.provider.endpoint_uri = org_value

        # assertion
        db.rollback()
        _node = db.scalars(
            select(Node).where(Node.endpoint_uri == "http://localhost:1000").limit(1)
        ).first()
        assert _node.is_synced == True

    # <Normal_3>
    # Delete old node data
    @pytest.mark.asyncio
    async def test_normal_3(self, processor, db):
        node = Node()
        node.id = 1
        node.endpoint_uri = "old_node"
        node.priority = 1
        node.is_synced = True
        db.add(node)
        db.commit()

        await processor.initial_setup()

        # assertion-1
        old_node = db.scalars(select(Node)).all()
        assert len(old_node) == 0

        # process
        await processor.process()
        db.commit()

        # assertion-2
        new_node = db.scalars(select(Node).limit(1)).first()
        assert new_node.id == 1
        assert new_node.endpoint_uri == WEB3_HTTP_PROVIDER
        assert new_node.priority == 0
        assert new_node.is_synced == True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Node down (At initialization)
    @mock.patch(
        "batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER",
        WEB3_HTTP_PROVIDER,
    )
    @mock.patch(
        "batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER_STANDBY",
        ["http://localhost:1000", "http://localhost:2000"],
    )
    @pytest.mark.asyncio
    async def test_error_1(self, processor, db):
        await processor.initial_setup()

        # assertion
        db.rollback()
        _node_list = db.scalars(select(Node).order_by(Node.id)).all()
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
        "batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER",
        WEB3_HTTP_PROVIDER,
    )
    @mock.patch(
        "batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER_STANDBY",
        ["http://localhost:1000", "http://localhost:2000"],
    )
    @pytest.mark.asyncio
    async def test_error_2(self, processor, db):
        await processor.initial_setup()
        await processor.process()

        # assertion
        db.rollback()
        _node_list = db.scalars(select(Node).order_by(Node.id)).all()
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
        assert _node.endpoint_uri == WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True
