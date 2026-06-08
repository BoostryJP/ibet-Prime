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
import time
from dataclasses import dataclass
from typing import cast

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from eth_typing import URI
from web3._utils.async_caching import async_lock
from web3._utils.caching.caching_utils import generate_cache_key
from web3._utils.http import DEFAULT_HTTP_TIMEOUT
from web3._utils.http_session_manager import HTTPSessionManager

DEFAULT_RESOLVED_ENDPOINT_CACHE_TTL = 1.0


@dataclass
class ResolvedEndpointCache:
    endpoint_uri: URI
    expires_at: float


class ResolvedEndpointCacheMixin:
    def _init_resolved_endpoint_cache(self) -> None:
        self._resolved_endpoint_cache: ResolvedEndpointCache | None = None

    def _get_cache_ttl(self) -> float:
        return DEFAULT_RESOLVED_ENDPOINT_CACHE_TTL

    def _get_cached_endpoint_uri(self) -> URI | None:
        cached_endpoint = self._resolved_endpoint_cache
        if cached_endpoint is None:
            return None
        # TTL expiry is handled lazily on access so the provider does not need
        # a separate cleanup path between requests.
        if cached_endpoint.expires_at <= time.monotonic():
            self._clear_cached_endpoint_uri()
            return None
        return cached_endpoint.endpoint_uri

    def _set_cached_endpoint_uri(self, endpoint_uri: URI) -> None:
        self._resolved_endpoint_cache = ResolvedEndpointCache(
            endpoint_uri=endpoint_uri,
            expires_at=time.monotonic() + self._get_cache_ttl(),
        )

    def _clear_cached_endpoint_uri(self) -> None:
        self._resolved_endpoint_cache = None


class KeepAliveHTTPSessionManager(HTTPSessionManager):
    @staticmethod
    def _create_async_session() -> ClientSession:
        # Keep the connector reusable so repeated RPC calls share connections.
        return ClientSession(
            raise_for_status=True,
            connector=TCPConnector(),
        )

    async def async_cache_and_return_session(
        self,
        endpoint_uri: URI,
        session: ClientSession | None = None,
        request_timeout: ClientTimeout | None = None,
    ) -> ClientSession:
        # Preserve async HTTP keep-alive for RPC-heavy workloads.
        cache_key = self._async_session_cache_key(endpoint_uri)

        evicted_items = None
        cached_session: ClientSession | None = None
        async with async_lock(self.session_pool, self._lock):
            if cache_key not in self.session_cache:
                if session is None:
                    session = self._create_async_session()

                cached_session, evicted_items = self.session_cache.cache(
                    cache_key, session
                )
                self.logger.debug(
                    "Async session cached: %s, %s", endpoint_uri, cached_session
                )

            else:
                cached_session = cast(
                    ClientSession,
                    self.session_cache.get_cache_entry(cache_key),
                )
                session_is_closed = cached_session.closed
                session_loop = getattr(cached_session, "_loop", None)
                session_loop_is_closed = bool(
                    session_loop is not None and session_loop.is_closed()
                )

                warning = (
                    "Async session was closed"
                    if session_is_closed
                    else (
                        "Loop was closed for async session"
                        if session_loop_is_closed
                        else None
                    )
                )
                if warning:
                    self.logger.debug(
                        "%s: %s, %s. Creating and caching a new async session for uri.",
                        warning,
                        endpoint_uri,
                        cached_session,
                    )

                    self.session_cache.pop(cache_key)
                    if not session_is_closed:
                        await cached_session.close()
                    self.logger.debug(
                        "Async session closed and evicted from cache: %s",
                        cached_session,
                    )

                    replacement_session = self._create_async_session()
                    cached_session, evicted_items = self.session_cache.cache(
                        cache_key, replacement_session
                    )
                    self.logger.debug(
                        "Async session cached: %s, %s", endpoint_uri, cached_session
                    )

        if evicted_items is not None:
            evicted_sessions = list(evicted_items.values())
            for evicted_session in evicted_sessions:
                self.logger.debug(
                    "Async session cache full. Session evicted from cache: %s",
                    evicted_session,
                )
            timeout_total = DEFAULT_HTTP_TIMEOUT
            if request_timeout is not None and request_timeout.total is not None:
                timeout_total = request_timeout.total
            asyncio.create_task(
                self._async_close_evicted_sessions(
                    timeout_total + 0.1,
                    evicted_sessions,
                )
            )

        assert cached_session is not None
        return cached_session

    @staticmethod
    def _async_session_cache_key(endpoint_uri: URI) -> str:
        return generate_cache_key(f"{id(asyncio.get_event_loop())}:{endpoint_uri}")
