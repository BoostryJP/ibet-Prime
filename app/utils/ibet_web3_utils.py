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
from requests.exceptions import ConnectionError, HTTPError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from web3 import AsyncHTTPProvider, AsyncWeb3, HTTPProvider, Web3
from web3.eth import AsyncEth
from web3.geth import AsyncGeth
from web3.middleware import ExtraDataToPOAMiddleware
from web3.net import AsyncNet
from web3.types import RPCEndpoint, RPCResponse

from app.database import async_engine, engine
from app.exceptions import ServiceUnavailableError
from app.model.db import Node
from config import WEB3_HTTP_PROVIDER, WEB3_REQUEST_RETRY_COUNT, WEB3_REQUEST_WAIT_TIME

thread_local = threading.local()

AsyncWeb3TimeoutKey = tuple[Any, Any, Any, Any]
AsyncWeb3CacheMap = dict[AsyncWeb3TimeoutKey, AsyncWeb3[Any]]


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
            AsyncFailOverHTTPProvider(request_kwargs={"timeout": timeout})
        )
        async_web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return async_web3


class FailOverHTTPProvider(HTTPProvider):
    fail_over_mode = False  # If False, use only the default(primary) provider

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.endpoint_uri: URI | None = None

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            if FailOverHTTPProvider.fail_over_mode is True:
                # If never running the block monitoring processor,
                # use default(primary) node.
                if db_session.scalars(select(Node).limit(1)).first() is None:
                    self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                    return super().make_request(method, params)
                counter = 0
                while counter <= WEB3_REQUEST_RETRY_COUNT:
                    # Switch alive node
                    _node = db_session.scalars(
                        select(Node)
                        .where(Node.is_synced == True)
                        .order_by(Node.priority, Node.id)
                        .limit(1)
                    ).first()
                    if _node is None:
                        counter += 1
                        if counter <= WEB3_REQUEST_RETRY_COUNT:
                            time.sleep(WEB3_REQUEST_WAIT_TIME)
                            continue
                        raise ServiceUnavailableError("Block synchronization is down")
                    assert _node.endpoint_uri is not None
                    self.endpoint_uri = URI(_node.endpoint_uri)
                    try:
                        return super().make_request(method, params)
                    except ConnectionError, JSONDecodeError, HTTPError:
                        # NOTE:
                        #  JSONDecodeError will be raised if a request is sent
                        #  while Quorum is terminating.
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


class AsyncFailOverHTTPProvider(AsyncHTTPProvider):
    fail_over_mode = False  # If False, use only the default(primary) provider

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.endpoint_uri: URI | None = None

    async def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            if AsyncFailOverHTTPProvider.fail_over_mode is True:
                # If never running the block monitoring processor,
                # use default(primary) node.
                if (await db_session.scalars(select(Node).limit(1))).first() is None:
                    self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                    return await super().make_request(method, params)
                counter = 0
                while counter <= WEB3_REQUEST_RETRY_COUNT:
                    # Switch alive node
                    _node = (
                        await db_session.scalars(
                            select(Node)
                            .where(Node.is_synced == True)
                            .order_by(Node.priority, Node.id)
                            .limit(1)
                        )
                    ).first()
                    if _node is None:
                        counter += 1
                        if counter <= WEB3_REQUEST_RETRY_COUNT:
                            await asyncio.sleep(WEB3_REQUEST_WAIT_TIME)
                            continue
                        raise ServiceUnavailableError("Block synchronization is down")
                    assert _node.endpoint_uri is not None
                    self.endpoint_uri = URI(_node.endpoint_uri)
                    try:
                        return await super().make_request(method, params)
                    except ClientError, JSONDecodeError:
                        # NOTE:
                        #  JSONDecodeError will be raised if a request is sent
                        #  while Quorum is terminating.
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
