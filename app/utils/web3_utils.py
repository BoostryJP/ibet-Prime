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
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import (
    RPCEndpoint,
    RPCResponse
)
from eth_typing import URI

from config import (
    WEB3_HTTP_PROVIDER,
    DATABASE_URL,
    DB_ECHO
)
from app.model.db import Node
from app.exceptions import ServiceUnavailableError

engine = create_engine(DATABASE_URL, echo=DB_ECHO)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)

thread_local = threading.local()


class Web3Wrapper:

    @property
    def eth(self):
        web3 = self._get_web3()
        return web3.eth

    @property
    def parity(self):
        web3 = self._get_web3()
        return web3.parity

    @property
    def geth(self):
        web3 = self._get_web3()
        return web3.geth

    @property
    def net(self):
        web3 = self._get_web3()
        return web3.net

    def _get_web3(self) -> Web3:
        # Get web3 for each threads because make to FailOverHTTPProvider thread-safe
        try:
            web3 = thread_local.web3
        except AttributeError:
            web3 = Web3(FailOverHTTPProvider())
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            thread_local.web3 = web3

        return web3


class FailOverHTTPProvider(Web3.HTTPProvider):
    # Note: It set True or False when loaded module.
    is_default = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint_uri = None

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:

        if FailOverHTTPProvider.is_default is not None and not FailOverHTTPProvider.is_default:
            # Switch alive node
            _node = db_session.query(Node). \
                filter(Node.is_synced == True). \
                order_by(Node.priority). \
                order_by(Node.id). \
                first()
            db_session.rollback()
            if _node is None:
                raise ServiceUnavailableError("block synchronization is down")
            self.endpoint_uri = URI(_node.endpoint_uri)
        else:
            # Use default(primary) node
            self.endpoint_uri = URI(WEB3_HTTP_PROVIDER)
            FailOverHTTPProvider.set_is_default()

        # Call RPC method
        return super().make_request(method, params)

    @staticmethod
    def set_is_default():
        node = db_session.query(Node). \
            filter(Node.endpoint_uri != None). \
            first()
        db_session.rollback()
        if node is None:
            FailOverHTTPProvider.is_default = True
        else:
            FailOverHTTPProvider.is_default = False


# NOTE: Loaded module before DB table create when executed from Pytest.
if "pytest" not in sys.modules:
    # First loaded module
    if FailOverHTTPProvider.is_default is None:
        # If never running the block monitor processor, use default(primary) node.
        FailOverHTTPProvider.set_is_default()
