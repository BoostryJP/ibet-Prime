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

from json.decoder import JSONDecodeError
from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from eth_typing import URI
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import AsyncWeb3
from web3.types import RPCEndpoint

from app.exceptions import ServiceUnavailableError
from app.model.db import AvalancheNode
from app.utils.ava_contract_utils import AvaFailOverHTTPProvider
from app.utils.web3_provider_utils import KeepAliveHTTPSessionManager
from avalanche_config import AVA_WEB3_HTTP_PROVIDER


class _AvaFailOverHTTPProviderForTest(AvaFailOverHTTPProvider):
    def seed_cached_endpoint_uri(self, endpoint_uri: URI) -> None:
        self._set_cached_endpoint_uri(endpoint_uri)


@pytest.mark.asyncio
class TestAvaFailOverHTTPProvider:
    ########################################################
    # Normal
    ########################################################

    # Normal_1
    # - Test that the provider connects successfully when fail_over_mode is False
    async def test_normal_1(self):
        web3 = AsyncWeb3(AvaFailOverHTTPProvider(fail_over_mode=False))
        try:
            assert (await web3.is_connected()) is True
        finally:
            await web3.provider.disconnect()

    # Normal_2
    # - Test that the provider connects successfully when fail_over_mode is True
    async def test_normal_2(self, async_db: AsyncSession):
        # Add a node information to the database
        node = AvalancheNode(
            endpoint_uri=AVA_WEB3_HTTP_PROVIDER, priority=1, is_synced=True
        )
        async_db.add(node)
        await async_db.commit()

        web3 = AsyncWeb3(AvaFailOverHTTPProvider(fail_over_mode=True))
        try:
            assert (await web3.is_connected()) is True
        finally:
            await web3.provider.disconnect()

    # Normal_3
    # - Test that the provider reuses a cached endpoint without querying the DB again
    async def test_normal_3(self):
        provider = AvaFailOverHTTPProvider(
            fail_over_mode=True,
            session_manager=KeepAliveHTTPSessionManager(),
        )
        method = RPCEndpoint("eth_chainId")
        fake_session = MagicMock()
        fake_session.scalars = AsyncMock(
            side_effect=[
                MagicMock(first=MagicMock(return_value=object())),
                MagicMock(
                    first=MagicMock(
                        return_value=SimpleNamespace(
                            endpoint_uri=AVA_WEB3_HTTP_PROVIDER
                        )
                    )
                ),
            ]
        )
        fake_session.close = AsyncMock()

        with (
            patch(
                "app.utils.ava_contract_utils.AsyncSession", return_value=fake_session
            ),
            patch(
                "web3.providers.rpc.async_rpc.AsyncHTTPProvider.make_request",
                AsyncMock(return_value={"result": "ok"}),
            ) as make_request,
        ):
            first_response = await provider.make_request(method, [])
            second_response = await provider.make_request(method, [])

        assert first_response == {"result": "ok"}
        assert second_response == {"result": "ok"}
        assert fake_session.scalars.await_count == 2
        assert make_request.await_count == 2
        assert fake_session.close.await_count == 2

    # Normal_4
    # - Test that cached primary endpoint failure falls back to the standby endpoint
    async def test_normal_4(self):
        provider = _AvaFailOverHTTPProviderForTest(
            fail_over_mode=True,
            session_manager=KeepAliveHTTPSessionManager(),
        )
        primary_endpoint = URI("http://primary.example:8545")
        standby_endpoint = URI("http://standby.example:8545")
        provider.seed_cached_endpoint_uri(primary_endpoint)
        method = RPCEndpoint("eth_chainId")
        fake_session = MagicMock()
        fake_session.scalars = AsyncMock(
            side_effect=[
                MagicMock(first=MagicMock(return_value=object())),
                MagicMock(
                    first=MagicMock(
                        return_value=SimpleNamespace(endpoint_uri=str(standby_endpoint))
                    )
                ),
            ]
        )
        fake_session.close = AsyncMock()

        with (
            patch(
                "app.utils.ava_contract_utils.AsyncSession", return_value=fake_session
            ),
            patch(
                "web3.providers.rpc.async_rpc.AsyncHTTPProvider.make_request",
                AsyncMock(
                    side_effect=[
                        JSONDecodeError("decode failed", "", 0),
                        {"result": "ok"},
                    ]
                ),
            ) as make_request,
        ):
            response = await provider.make_request(method, [])

        assert response == {"result": "ok"}
        assert provider.endpoint_uri == standby_endpoint
        assert fake_session.scalars.await_count == 2
        assert make_request.await_count == 2
        assert fake_session.close.await_count == 1

    ########################################################
    # Error
    ########################################################

    # Error_1
    # - Test that an error is raised when no nodes are available
    @mock.patch("app.utils.ava_contract_utils.AVA_WEB3_REQUEST_WAIT_TIME", 0.1)
    async def test_error_1(self, async_db: AsyncSession):
        # Add a node information to the database with is_synced=False
        node = AvalancheNode(
            endpoint_uri=AVA_WEB3_HTTP_PROVIDER, priority=1, is_synced=False
        )
        async_db.add(node)
        await async_db.commit()

        # Test that an error is raised
        web3 = AsyncWeb3(AvaFailOverHTTPProvider(fail_over_mode=True))
        try:
            with pytest.raises(
                ServiceUnavailableError, match="Cannot connect to any Avalanche node"
            ):
                await web3.is_connected()
        finally:
            await web3.provider.disconnect()

    # Error_2
    # - Test that an error is raised when no nodes are available
    @mock.patch("app.utils.ava_contract_utils.AVA_WEB3_REQUEST_WAIT_TIME", 0.1)
    async def test_error_2(self, async_db: AsyncSession):
        # Add a node information to the database with an invalid endpoint URI
        node = AvalancheNode(endpoint_uri="invalid_uri", priority=1, is_synced=True)
        async_db.add(node)
        await async_db.commit()

        # Test that an error is raised
        web3 = AsyncWeb3(AvaFailOverHTTPProvider(fail_over_mode=True))
        try:
            with pytest.raises(
                ServiceUnavailableError, match="Cannot connect to any Avalanche node"
            ):
                await web3.is_connected()
        finally:
            await web3.provider.disconnect()
