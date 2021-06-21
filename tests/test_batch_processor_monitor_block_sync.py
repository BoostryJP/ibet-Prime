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
import pytest
import time
from unittest import mock
from unittest.mock import MagicMock

from web3 import Web3
from web3.middleware import geth_poa_middleware

from config import (
    BLOCK_SYNC_STATUS_SLEEP_INTERVAL,
    WEB3_HTTP_PROVIDER
)
from app.model.db import Node
from batch.processor_monitor_block_sync import (
    Sinks,
    DBSink,
    Processor
)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope='function')
def processor(db):
    _sink = Sinks()
    _sink.register(DBSink(db))
    return Processor(sink=_sink, db=db)


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Execute Batch Run 1st: synced
    # Execute Batch Run 2nd: block generation speed down(same the previous)
    # Execute Batch Run 3rd: synced
    # Execute Batch Run 4th: node syncing(DIFF:over 1)
    # Execute Batch Run 5th: node syncing(DIFF:1) == synced
    def test_normal_1(self, processor, db):
        # Run 1st: synced
        processor.process()

        # assertion
        _node = db.query(Node).first()
        assert _node.id == 1
        assert _node.endpoint_uri == WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True

        time.sleep(BLOCK_SYNC_STATUS_SLEEP_INTERVAL)

        # Run 2st: block generation speed down(same the previous)
        with mock.patch("batch.processor_monitor_block_sync.BLOCK_GENERATION_SPEED_THRESHOLD", 100):
            processor.process()

        # assertion
        _node = db.query(Node).first()
        assert _node.is_synced == False

        time.sleep(BLOCK_SYNC_STATUS_SLEEP_INTERVAL)

        # Run 3rd: synced
        processor.process()

        # assertion
        _node = db.query(Node).first()
        assert _node.is_synced == True

        time.sleep(BLOCK_SYNC_STATUS_SLEEP_INTERVAL)

        # Run 4th: node syncing(DIFF:over 1)
        block_number = web3.eth.blockNumber
        with mock.patch("web3.eth.Eth.is_syncing") as mock_is_syncing:
            mock_is_syncing.side_effect = [
                {
                    "highestBlock": block_number,
                    "currentBlock": block_number - 2
                }
            ]
            processor.process()

        # assertion
        _node = db.query(Node).first()
        assert _node.is_synced == False

        time.sleep(BLOCK_SYNC_STATUS_SLEEP_INTERVAL)

        # Run 5th: node syncing(DIFF:1) == synced
        block_number = web3.eth.blockNumber
        with mock.patch("web3.eth.Eth.is_syncing") as mock_is_syncing:
            mock_is_syncing.side_effect = [
                {
                    "highestBlock": block_number,
                    "currentBlock": block_number - 1
                }
            ]
            processor.process()

        # assertion
        _node = db.query(Node).first()
        assert _node.is_synced == True

    # <Normal_2>
    # standby node is down to sync
    @mock.patch("batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER_STANDBY", ["http://test1:1000"])
    def test_normal_2(self, db):
        _sink = Sinks()
        _sink.register(DBSink(db))
        processor = Processor(sink=_sink, db=db)

        # pre assertion
        _node = db.query(Node).first()
        assert _node.id == 1
        assert _node.endpoint_uri == "http://test1:1000"
        assert _node.priority == 1
        assert _node.is_synced == False

        # node sync(processing)
        org_value = processor.node_info["http://test1:1000"]["web3"].manager.provider.endpoint_uri
        processor.node_info["http://test1:1000"]["web3"].manager.provider.endpoint_uri = WEB3_HTTP_PROVIDER
        processor.process()
        processor.node_info["http://test1:1000"]["web3"].manager.provider.endpoint_uri = org_value

        # assertion
        _node = db.query(Node).filter(Node.endpoint_uri == "http://test1:1000").first()
        assert _node.is_synced == True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # node down(initialize)
    @mock.patch("batch.processor_monitor_block_sync.WEB3_HTTP_PROVIDER_STANDBY",
                ["http://test1:1000", "http://test2:2000"])
    @mock.patch("web3.providers.rpc.HTTPProvider.make_request", MagicMock(side_effect=Exception()))
    def test_error_1(self, db):
        _sink = Sinks()
        _sink.register(DBSink(db))
        Processor(sink=_sink, db=db)

        # assertion
        _node_list = db.query(Node).order_by(Node.id).all()
        assert len(_node_list) == 3
        _node = _node_list[0]
        assert _node.id == 1
        assert _node.endpoint_uri == WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == False
        _node = _node_list[1]
        assert _node.id == 2
        assert _node.endpoint_uri == "http://test1:1000"
        assert _node.priority == 1
        assert _node.is_synced == False
        _node = _node_list[2]
        assert _node.id == 3
        assert _node.endpoint_uri == "http://test2:2000"
        assert _node.priority == 1
        assert _node.is_synced == False

    # <Error_2>
    # node down(processing)
    def test_error_2(self, processor, db):
        processor.process()

        # assertion
        _node = db.query(Node).first()
        assert _node.id == 1
        assert _node.endpoint_uri == WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == True

        # node down(processing)
        org_value = processor.node_info[WEB3_HTTP_PROVIDER]["web3"].manager.provider.endpoint_uri
        processor.node_info[WEB3_HTTP_PROVIDER]["web3"].manager.provider.endpoint_uri = "http://hogehoge"
        processor.process()
        processor.node_info[WEB3_HTTP_PROVIDER]["web3"].manager.provider.endpoint_uri = org_value

        # assertion
        _node = db.query(Node).first()
        assert _node.id == 1
        assert _node.endpoint_uri == WEB3_HTTP_PROVIDER
        assert _node.priority == 0
        assert _node.is_synced == False
