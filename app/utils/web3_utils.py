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
import sys
import threading
import time
from json.decoder import JSONDecodeError
from typing import Any

from eth_typing import URI
from requests.exceptions import ConnectionError, HTTPError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import RPCEndpoint, RPCResponse

from app.exceptions import ServiceUnavailableError
from app.model.db import Node
from config import (
    DATABASE_URL,
    DB_ECHO,
    WEB3_HTTP_PROVIDER,
    WEB3_REQUEST_RETRY_COUNT,
    WEB3_REQUEST_WAIT_TIME,
)

engine = create_engine(DATABASE_URL, echo=DB_ECHO, pool_pre_ping=True)
thread_local = threading.local()


class Web3Wrapper:
    def __init__(self):
        if "pytest" not in sys.modules:
            FailOverHTTPProvider.set_fail_over_mode(True)

    @property
    def eth(self):
        web3 = self._get_web3()
        return web3.eth

    @property
    def geth(self):
        web3 = self._get_web3()
        return web3.geth

    @property
    def net(self):
        web3 = self._get_web3()
        return web3.net

    @staticmethod
    def _get_web3() -> Web3:
        # Get web3 for each threads because make to FailOverHTTPProvider thread-safe
        try:
            web3 = thread_local.web3
        except AttributeError:
            web3 = Web3(FailOverHTTPProvider())
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            thread_local.web3 = web3

        return web3


class FailOverHTTPProvider(Web3.HTTPProvider):
    fail_over_mode = False  # If False, use only the default(primary) provider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint_uri = None

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            if FailOverHTTPProvider.fail_over_mode is True:
                # If never running the block monitoring processor,
                # use default(primary) node.
                if db_session.query(Node).first() is None:
                    self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                    return super().make_request(method, params)
                else:
                    counter = 0
                    while counter <= WEB3_REQUEST_RETRY_COUNT:
                        # Switch alive node
                        _node = (
                            db_session.query(Node)
                            .filter(Node.is_synced == True)
                            .order_by(Node.priority)
                            .order_by(Node.id)
                            .first()
                        )
                        if _node is None:
                            counter += 1
                            if counter <= WEB3_REQUEST_RETRY_COUNT:
                                time.sleep(WEB3_REQUEST_WAIT_TIME)
                                continue
                            raise ServiceUnavailableError(
                                "Block synchronization is down"
                            )
                        self.endpoint_uri = URI(_node.endpoint_uri)
                        try:
                            return super().make_request(method, params)
                        except (ConnectionError, JSONDecodeError, HTTPError):
                            # NOTE:
                            #  JSONDecodeError will be raised if a request is sent
                            #  while Quorum is terminating.
                            counter += 1
                            if counter <= WEB3_REQUEST_RETRY_COUNT:
                                time.sleep(WEB3_REQUEST_WAIT_TIME)
                                continue
                            raise ServiceUnavailableError(
                                "Block synchronization is down"
                            )
            else:  # Use default provider
                self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
                return super().make_request(method, params)
        finally:
            db_session.close()

    @staticmethod
    def set_fail_over_mode(use_fail_over: bool):
        FailOverHTTPProvider.fail_over_mode = use_fail_over
