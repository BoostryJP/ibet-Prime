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

from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest

from app.model.db import EthereumNode, Node


class TestServiceHealthCheck:
    # target API endpoint
    apiurl = "/healthcheck"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        _node = Node()
        _node.endpoint_uri = "http://test1"
        _node.priority = 0
        _node.is_synced = False
        async_db.add(_node)

        _node = Node()
        _node.endpoint_uri = "http://test2"
        _node.priority = 1
        _node.is_synced = True
        async_db.add(_node)

        _node = EthereumNode()
        _node.endpoint_uri = "http://test1"
        _node.priority = 0
        _node.is_synced = False
        async_db.add(_node)

        _node = EthereumNode()
        _node.endpoint_uri = "http://test2"
        _node.priority = 1
        _node.is_synced = True
        async_db.add(_node)

        await async_db.commit()

        # request target api
        resp = await async_client.get(self.apiurl)

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Node not sync
    # E2EE key invalid
    @mock.patch(
        "app.utils.e2ee_utils.E2EEUtils.cache",
        {
            "private_key": None,
            "public_key": None,
            "encrypted_length": None,
            "expiration_datetime": datetime.min,
        },
    )
    @mock.patch(
        "app.utils.e2ee_utils.E2EE_RSA_RESOURCE", "tests/data/account_config.yml"
    )
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        _node = Node()
        _node.endpoint_uri = "http://test1"
        _node.priority = 0
        _node.is_synced = False
        async_db.add(_node)

        _node = Node()
        _node.endpoint_uri = "http://test2"
        _node.priority = 1
        _node.is_synced = False
        async_db.add(_node)

        _node = EthereumNode()
        _node.endpoint_uri = "http://test1"
        _node.priority = 0
        _node.is_synced = False
        async_db.add(_node)

        _node = EthereumNode()
        _node.endpoint_uri = "http://test2"
        _node.priority = 1
        _node.is_synced = False
        async_db.add(_node)

        await async_db.commit()

        # request target api
        resp = await async_client.get(self.apiurl)

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 1, "title": "ServiceUnavailableError"},
            "detail": [
                "ibet node is down",
                "ethereum node is down",
                "Setting E2EE key is invalid",
            ],
        }

    # <Error_2>
    # DB connect error
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # request target api
        with mock.patch(
            "sqlalchemy.ext.asyncio.AsyncSession.connection",
            MagicMock(side_effect=Exception()),
        ):
            resp = await async_client.get(self.apiurl)

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 1, "title": "ServiceUnavailableError"},
            "detail": [
                "Cannot connect to the data source",
            ],
        }
