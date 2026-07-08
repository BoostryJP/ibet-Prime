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
import threading
import time
from json.decoder import JSONDecodeError
from typing import Any, cast
from weakref import WeakKeyDictionary

from aiohttp import ClientError, ClientTimeout
from eth_typing import URI
from requests.exceptions import ConnectionError, HTTPError, Timeout as RequestsTimeout
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from web3 import AsyncHTTPProvider, AsyncWeb3, HTTPProvider, Web3
from web3.eth import AsyncEth
from web3.geth import AsyncGeth
from web3.middleware import ExtraDataToPOAMiddleware
from web3.net import AsyncNet
from web3.types import RPCEndpoint, RPCResponse

from app import log
from app.database import async_engine, engine
from app.exceptions import ServiceUnavailableError
from app.model.db import Node
from app.utils.web3_provider_utils import (
    KeepAliveHTTPSessionManager,
    ResolvedEndpointCacheMixin,
)
from config import WEB3_HTTP_PROVIDER, WEB3_REQUEST_RETRY_COUNT, WEB3_REQUEST_WAIT_TIME

thread_local = threading.local()
LOG = log.get_logger()

# Cache AsyncWeb3 by timeout shape so wrappers with different timeout settings
# do not accidentally share the same provider/session.
AsyncWeb3TimeoutKey = tuple[Any, Any, Any, Any]
AsyncWeb3CacheMap = dict[AsyncWeb3TimeoutKey, AsyncWeb3[Any]]
_SYNC_RETRYABLE_RPC_EXCEPTIONS = (
    ConnectionError,
    HTTPError,
    RequestsTimeout,
    JSONDecodeError,
)
_ASYNC_RETRYABLE_RPC_EXCEPTIONS = (ClientError, TimeoutError, JSONDecodeError)


class Web3Wrapper:
    DEFAULT_TIMEOUT = 5

    def __init__(self, request_timeout: int = DEFAULT_TIMEOUT):
        if "pytest" not in sys.modules:
            FailOverHTTPProvider.set_fail_over_mode(True)
        self.request_timeout = request_timeout

    @property
    def eth(self):
        web3 = self._get_web3(self.request_timeout)
        return web3.eth

    @property
    def geth(self):
        web3 = self._get_web3(self.request_timeout)
        return web3.geth

    @property
    def net(self):
        web3 = self._get_web3(self.request_timeout)
        return web3.net

    @staticmethod
    def _get_web3(request_timeout: int) -> Web3:
        # Get web3 for each thread because make to FailOverHTTPProvider thread-safe
        try:
            web3 = thread_local.web3
        except AttributeError:
            web3 = Web3(
                FailOverHTTPProvider(request_kwargs={"timeout": request_timeout})
            )
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            thread_local.web3 = web3

        return web3


class AsyncWeb3Wrapper:
    DEFAULT_TIMEOUT = 5

    def __init__(self, request_timeout: int | ClientTimeout = DEFAULT_TIMEOUT):
        if "pytest" not in sys.modules:
            AsyncFailOverHTTPProvider.set_fail_over_mode(True)
        self.request_timeout = request_timeout

    @property
    def eth(self) -> AsyncEth:
        web3 = self.get_web3()
        return web3.eth

    @property
    def geth(self) -> AsyncGeth:
        web3 = self.get_web3()
        return web3.geth

    @property
    def net(self) -> AsyncNet:
        web3 = self.get_web3()
        return web3.net

    def get_web3(self) -> AsyncWeb3[Any]:
        return self._get_web3(self.request_timeout)

    @staticmethod
    def _normalize_async_timeout(
        request_timeout: int | ClientTimeout,
    ) -> ClientTimeout:
        if isinstance(request_timeout, ClientTimeout):
            return request_timeout
        return ClientTimeout(total=request_timeout)

    @classmethod
    def _get_web3(cls, request_timeout: int | ClientTimeout) -> AsyncWeb3[Any]:
        timeout = cls._normalize_async_timeout(request_timeout)
        # Use normalized timeout fields as the cache key because ClientTimeout
        # itself is mutable-like and not suitable as a stable dict key here.
        timeout_key: AsyncWeb3TimeoutKey = (
            timeout.total,
            timeout.connect,
            timeout.sock_connect,
            timeout.sock_read,
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            # Some call sites still resolve AsyncWeb3 outside a running loop.
            # Keep a separate per-thread cache for that fallback path.
            try:
                async_web3_map = cast(
                    AsyncWeb3CacheMap,
                    thread_local.async_web3_without_loop,
                )
            except AttributeError:
                async_web3_map = {}
                thread_local.async_web3_without_loop = async_web3_map

            async_web3 = async_web3_map.get(timeout_key)
            if async_web3 is None:
                async_web3 = cls._create_web3(timeout)
                async_web3_map[timeout_key] = async_web3
            return async_web3

        # AsyncHTTPProvider owns an aiohttp session, so reuse is limited to the
        # event loop that created it.
        try:
            async_web3_by_loop = cast(
                WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncWeb3CacheMap],
                thread_local.async_web3_by_loop,
            )
        except AttributeError:
            async_web3_by_loop: WeakKeyDictionary[
                asyncio.AbstractEventLoop, AsyncWeb3CacheMap
            ] = WeakKeyDictionary()
            thread_local.async_web3_by_loop = async_web3_by_loop

        loop_web3_map: AsyncWeb3CacheMap = async_web3_by_loop.setdefault(loop, {})
        async_web3 = loop_web3_map.get(timeout_key)
        if async_web3 is None:
            async_web3 = cls._create_web3(timeout)
            loop_web3_map[timeout_key] = async_web3
        return async_web3

    @staticmethod
    def _create_web3(timeout: ClientTimeout) -> AsyncWeb3[Any]:
        async_web3 = AsyncWeb3(
            AsyncFailOverHTTPProvider(
                request_kwargs={"timeout": timeout},
                session_manager=KeepAliveHTTPSessionManager(),
            )
        )
        async_web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return async_web3


class FailOverHTTPProvider(ResolvedEndpointCacheMixin, HTTPProvider):
    fail_over_mode = False  # If False, use only the default(primary) provider

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._init_resolved_endpoint_cache()
        self.endpoint_uri: URI | None = None

    def _get_cache_ttl(self) -> float:
        return float(WEB3_REQUEST_WAIT_TIME)

    def _resolve_endpoint_uri(
        self, db_session: Session, failed_endpoint_uris: set[URI] | None = None
    ) -> URI | None:
        cached_endpoint_uri = self._get_cached_endpoint_uri()
        if cached_endpoint_uri is not None and cached_endpoint_uri not in (
            failed_endpoint_uris or set()
        ):
            return cached_endpoint_uri

        stmt = select(Node).where(Node.is_synced == True)
        if failed_endpoint_uris:
            stmt = stmt.where(
                Node.endpoint_uri.not_in([str(uri) for uri in failed_endpoint_uris])
            )
        node = db_session.scalars(
            stmt.order_by(Node.priority, Node.id).limit(1)
        ).first()
        if node is None or node.endpoint_uri is None:
            return None

        endpoint_uri = URI(node.endpoint_uri)
        self._set_cached_endpoint_uri(endpoint_uri)
        return endpoint_uri

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            if FailOverHTTPProvider.fail_over_mode is True:
                failed_endpoint_uris: set[URI] = set()
                # Try cached endpoint first to avoid unnecessary DB query,
                # and fallback to resolving from DB if it fails.
                cached_endpoint_uri = self._get_cached_endpoint_uri()
                if cached_endpoint_uri is not None:
                    self.endpoint_uri = cached_endpoint_uri
                    try:
                        return super().make_request(method, params)
                    except _SYNC_RETRYABLE_RPC_EXCEPTIONS:
                        self._clear_cached_endpoint_uri()
                        failed_endpoint_uris.add(cached_endpoint_uri)
                        LOG.warning(
                            f"Retry web3 request due to connection fail: endpoint={cached_endpoint_uri}, method={method}, params={params}"
                        )

                # If never running the block monitoring processor,
                # use default(primary) node.
                if db_session.scalars(select(Node).limit(1)).first() is None:
                    self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                    return super().make_request(method, params)
                counter = 0
                while counter <= WEB3_REQUEST_RETRY_COUNT:
                    endpoint_uri = self._resolve_endpoint_uri(
                        db_session, failed_endpoint_uris
                    )
                    if endpoint_uri is None:
                        counter += 1
                        if counter <= WEB3_REQUEST_RETRY_COUNT:
                            time.sleep(WEB3_REQUEST_WAIT_TIME)
                            continue
                        raise ServiceUnavailableError("Block synchronization is down")
                    self.endpoint_uri = endpoint_uri
                    try:
                        return super().make_request(method, params)
                    except _SYNC_RETRYABLE_RPC_EXCEPTIONS:
                        # NOTE:
                        #  JSONDecodeError will be raised if a request is sent
                        #  while Quorum is terminating.
                        self._clear_cached_endpoint_uri()
                        failed_endpoint_uris.add(endpoint_uri)
                        LOG.warning(
                            f"Retry web3 request due to connection fail: endpoint={endpoint_uri}, method={method}, params={params}"
                        )
                        counter += 1
                        if counter <= WEB3_REQUEST_RETRY_COUNT:
                            time.sleep(WEB3_REQUEST_WAIT_TIME)
                            continue
                        raise ServiceUnavailableError("Block synchronization is down")
            else:  # Use default provider
                self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                return super().make_request(method, params)
            raise ServiceUnavailableError("Block synchronization is down")
        finally:
            db_session.close()

    @staticmethod
    def set_fail_over_mode(use_fail_over: bool):
        FailOverHTTPProvider.fail_over_mode = use_fail_over


class AsyncFailOverHTTPProvider(ResolvedEndpointCacheMixin, AsyncHTTPProvider):
    fail_over_mode = False  # If False, use only the default(primary) provider

    def __init__(
        self,
        session_manager: KeepAliveHTTPSessionManager | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._init_resolved_endpoint_cache()
        if session_manager is not None:
            self._request_session_manager = session_manager
        self.endpoint_uri: URI | None = None

    def _get_cache_ttl(self) -> float:
        return float(WEB3_REQUEST_WAIT_TIME)

    async def _resolve_endpoint_uri(
        self, db_session: AsyncSession, failed_endpoint_uris: set[URI] | None = None
    ) -> URI | None:
        cached_endpoint_uri = self._get_cached_endpoint_uri()
        if cached_endpoint_uri is not None and cached_endpoint_uri not in (
            failed_endpoint_uris or set()
        ):
            return cached_endpoint_uri

        stmt = select(Node).where(Node.is_synced == True)
        if failed_endpoint_uris:
            stmt = stmt.where(
                Node.endpoint_uri.not_in([str(uri) for uri in failed_endpoint_uris])
            )
        node = (
            await db_session.scalars(stmt.order_by(Node.priority, Node.id).limit(1))
        ).first()
        if node is None or node.endpoint_uri is None:
            return None

        endpoint_uri = URI(node.endpoint_uri)
        self._set_cached_endpoint_uri(endpoint_uri)
        return endpoint_uri

    async def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            if AsyncFailOverHTTPProvider.fail_over_mode is True:
                failed_endpoint_uris: set[URI] = set()
                # Try cached endpoint first to avoid unnecessary DB query,
                # and fallback to resolving from DB if it fails.
                cached_endpoint_uri = self._get_cached_endpoint_uri()
                if cached_endpoint_uri is not None:
                    self.endpoint_uri = cached_endpoint_uri
                    try:
                        return await super().make_request(method, params)
                    except _ASYNC_RETRYABLE_RPC_EXCEPTIONS:
                        self._clear_cached_endpoint_uri()
                        failed_endpoint_uris.add(cached_endpoint_uri)
                        LOG.warning(
                            f"Retry web3 request due to connection fail: endpoint={cached_endpoint_uri}, method={method}, params={params}"
                        )

                # If never running the block monitoring processor,
                # use default(primary) node.
                if (await db_session.scalars(select(Node).limit(1))).first() is None:
                    self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                    return await super().make_request(method, params)
                counter = 0
                while counter <= WEB3_REQUEST_RETRY_COUNT:
                    endpoint_uri = await self._resolve_endpoint_uri(
                        db_session, failed_endpoint_uris
                    )
                    if endpoint_uri is None:
                        counter += 1
                        if counter <= WEB3_REQUEST_RETRY_COUNT:
                            await asyncio.sleep(WEB3_REQUEST_WAIT_TIME)
                            continue
                        raise ServiceUnavailableError("Block synchronization is down")
                    self.endpoint_uri = endpoint_uri
                    try:
                        return await super().make_request(method, params)
                    except _ASYNC_RETRYABLE_RPC_EXCEPTIONS:
                        # NOTE:
                        #  JSONDecodeError will be raised if a request is sent
                        #  while Quorum is terminating.
                        self._clear_cached_endpoint_uri()
                        failed_endpoint_uris.add(endpoint_uri)
                        LOG.warning(
                            f"Retry web3 request due to connection fail: endpoint={endpoint_uri}, method={method}, params={params}"
                        )
                        counter += 1
                        if counter <= WEB3_REQUEST_RETRY_COUNT:
                            await asyncio.sleep(WEB3_REQUEST_WAIT_TIME)
                            continue
                        raise ServiceUnavailableError("Block synchronization is down")
            else:  # Use default provider
                self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                return await super().make_request(method, params)
            raise ServiceUnavailableError("Block synchronization is down")
        finally:
            await db_session.close()

    @staticmethod
    def set_fail_over_mode(use_fail_over: bool):
        AsyncFailOverHTTPProvider.fail_over_mode = use_fail_over
