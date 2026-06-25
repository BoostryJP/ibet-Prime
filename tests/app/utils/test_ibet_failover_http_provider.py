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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from eth_typing import URI
from requests.exceptions import ConnectionError
from web3.types import RPCEndpoint

from app.utils.ibet_web3_utils import AsyncFailOverHTTPProvider, FailOverHTTPProvider
from app.utils.web3_provider_utils import KeepAliveHTTPSessionManager
from config import WEB3_HTTP_PROVIDER


class _FailOverHTTPProviderForTest(FailOverHTTPProvider):
    def seed_cached_endpoint_uri(self, endpoint_uri: URI) -> None:
        self._set_cached_endpoint_uri(endpoint_uri)


class _AsyncFailOverHTTPProviderForTest(AsyncFailOverHTTPProvider):
    def seed_cached_endpoint_uri(self, endpoint_uri: URI) -> None:
        self._set_cached_endpoint_uri(endpoint_uri)


class TestFailOverHTTPProvider:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Resolved endpoint is cached and reused on the second request
    def test_normal_1(self, monkeypatch: pytest.MonkeyPatch):
        provider = FailOverHTTPProvider()
        fake_session = MagicMock()
        fake_session.scalars.side_effect = [
            MagicMock(first=MagicMock(return_value=object())),
            MagicMock(
                first=MagicMock(
                    return_value=SimpleNamespace(endpoint_uri=WEB3_HTTP_PROVIDER)
                )
            ),
        ]
        fake_session.close = MagicMock()

        monkeypatch.setattr(FailOverHTTPProvider, "fail_over_mode", True)
        method = RPCEndpoint("eth_chainId")

        with (
            patch("app.utils.ibet_web3_utils.Session", return_value=fake_session),
            patch(
                "web3.providers.rpc.rpc.HTTPProvider.make_request",
                return_value={"result": "ok"},
            ) as make_request,
        ):
            first_response = provider.make_request(method, [])
            second_response = provider.make_request(method, [])

        assert first_response == {"result": "ok"}
        assert second_response == {"result": "ok"}
        assert fake_session.scalars.call_count == 2
        assert make_request.call_count == 2
        assert fake_session.close.call_count == 2

    # <Normal_2>
    # Cached primary endpoint failure falls back to the standby endpoint.
    def test_normal_2(self, monkeypatch: pytest.MonkeyPatch):
        provider = _FailOverHTTPProviderForTest()
        primary_endpoint = URI("http://primary.example:8545")
        standby_endpoint = URI("http://standby.example:8545")
        provider.seed_cached_endpoint_uri(primary_endpoint)
        fake_session = MagicMock()
        fake_session.scalars.side_effect = [
            MagicMock(first=MagicMock(return_value=object())),
            MagicMock(
                first=MagicMock(
                    return_value=SimpleNamespace(endpoint_uri=str(standby_endpoint))
                )
            ),
        ]
        fake_session.close = MagicMock()

        monkeypatch.setattr(FailOverHTTPProvider, "fail_over_mode", True)
        method = RPCEndpoint("eth_chainId")

        with (
            patch("app.utils.ibet_web3_utils.Session", return_value=fake_session),
            patch(
                "web3.providers.rpc.rpc.HTTPProvider.make_request",
                side_effect=[ConnectionError(), {"result": "ok"}],
            ) as make_request,
        ):
            response = provider.make_request(method, [])

        assert response == {"result": "ok"}
        assert provider.endpoint_uri == standby_endpoint
        assert fake_session.scalars.call_count == 2
        assert make_request.call_count == 2
        assert fake_session.close.call_count == 1


@pytest.mark.asyncio
class TestAsyncFailOverHTTPProvider:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Resolved endpoint is cached and reused on the second async request
    async def test_normal_1(self, monkeypatch: pytest.MonkeyPatch):
        provider = AsyncFailOverHTTPProvider(
            session_manager=KeepAliveHTTPSessionManager()
        )
        fake_session = MagicMock()
        fake_session.scalars = AsyncMock(
            side_effect=[
                MagicMock(first=MagicMock(return_value=object())),
                MagicMock(
                    first=MagicMock(
                        return_value=SimpleNamespace(endpoint_uri=WEB3_HTTP_PROVIDER)
                    )
                ),
            ]
        )
        fake_session.close = AsyncMock()

        monkeypatch.setattr(AsyncFailOverHTTPProvider, "fail_over_mode", True)
        method = RPCEndpoint("eth_chainId")

        with (
            patch(
                "app.utils.ibet_web3_utils.AsyncSession",
                return_value=fake_session,
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

    # <Normal_2>
    # Cached primary endpoint failure falls back to the standby endpoint.
    async def test_normal_2(self, monkeypatch: pytest.MonkeyPatch):
        provider = _AsyncFailOverHTTPProviderForTest(
            session_manager=KeepAliveHTTPSessionManager()
        )
        primary_endpoint = URI("http://primary.example:8545")
        standby_endpoint = URI("http://standby.example:8545")
        provider.seed_cached_endpoint_uri(primary_endpoint)
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

        monkeypatch.setattr(AsyncFailOverHTTPProvider, "fail_over_mode", True)
        method = RPCEndpoint("eth_chainId")

        with (
            patch(
                "app.utils.ibet_web3_utils.AsyncSession",
                return_value=fake_session,
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
