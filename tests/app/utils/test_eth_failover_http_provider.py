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

import pytest
from web3 import AsyncWeb3

from app.exceptions import ServiceUnavailableError
from app.model.db import EthereumNode
from app.utils.eth_contract_utils import EthFailOverHTTPProvider
from eth_config import ETH_WEB3_HTTP_PROVIDER


@pytest.mark.asyncio
class TestEthFailOverHTTPProvider:
    ########################################################
    # Normal
    ########################################################

    # Normal_1
    # - Test that the provider connects successfully when fail_over_mode is False
    async def test_normal_1(self):
        web3 = AsyncWeb3(EthFailOverHTTPProvider(fail_over_mode=False))
        assert (await web3.is_connected()) is True

    # Normal_2
    async def test_normal_2(self, async_db):
        # Add a node information to the database
        node = EthereumNode(
            endpoint_uri=ETH_WEB3_HTTP_PROVIDER, priority=1, is_synced=True
        )
        async_db.add(node)
        await async_db.commit()

        # Test that the provider connects successfully when fail_over_mode is True
        web3 = AsyncWeb3(EthFailOverHTTPProvider(fail_over_mode=True))
        assert (await web3.is_connected()) is True

    ########################################################
    # Error
    ########################################################

    # Error_1
    # - Test that an error is raised when no nodes are available
    @mock.patch("app.utils.eth_contract_utils.ETH_WEB3_REQUEST_WAIT_TIME", 0.1)
    async def test_error_1(self, async_db):
        # Add a node information to the database with is_synced=False
        node = EthereumNode(
            endpoint_uri=ETH_WEB3_HTTP_PROVIDER, priority=1, is_synced=False
        )
        async_db.add(node)
        await async_db.commit()

        # Test that an error is raised
        web3 = AsyncWeb3(EthFailOverHTTPProvider(fail_over_mode=True))
        with pytest.raises(
            ServiceUnavailableError, match="Cannot connect to any Ethereum node"
        ):
            await web3.is_connected()

    # Error_2
    # - Test that an error is raised when no nodes are available
    @mock.patch("app.utils.eth_contract_utils.ETH_WEB3_REQUEST_WAIT_TIME", 0.1)
    async def test_error_2(self, async_db):
        # Add a node information to the database with an invalid endpoint URI
        node = EthereumNode(endpoint_uri="invalid_uri", priority=1, is_synced=True)
        async_db.add(node)
        await async_db.commit()

        # Test that an error is raised
        web3 = AsyncWeb3(EthFailOverHTTPProvider(fail_over_mode=True))
        with pytest.raises(
            ServiceUnavailableError, match="Cannot connect to any Ethereum node"
        ):
            await web3.is_connected()
