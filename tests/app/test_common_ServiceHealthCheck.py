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

from app.model.db import Node


class TestServiceHealthCheck:
    # target API endpoint
    apiurl = "/healthcheck"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        _node = Node()
        _node.endpoint_uri = "http://test1"
        _node.priority = 0
        _node.is_synced = False
        db.add(_node)

        _node = Node()
        _node.endpoint_uri = "http://test2"
        _node.priority = 1
        _node.is_synced = True
        db.add(_node)

        db.commit()

        # request target api
        resp = client.get(self.apiurl)

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
    def test_error_1(self, client, db):
        _node = Node()
        _node.endpoint_uri = "http://test1"
        _node.priority = 0
        _node.is_synced = False
        db.add(_node)

        _node = Node()
        _node.endpoint_uri = "http://test2"
        _node.priority = 1
        _node.is_synced = False
        db.add(_node)

        db.commit()

        # request target api
        resp = client.get(self.apiurl)

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 1, "title": "ServiceUnavailableError"},
            "detail": [
                "Ethereum node's block synchronization is down",
                "Setting E2EE key is invalid",
            ],
        }

    # <Error_2>
    # DB connect error
    def test_error_2(self, client, db):
        # request target api
        with mock.patch(
            "sqlalchemy.ext.asyncio.AsyncSession.connection",
            MagicMock(side_effect=Exception()),
        ):
            resp = client.get(self.apiurl)

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 1, "title": "ServiceUnavailableError"},
            "detail": [
                "Can't connect to database",
            ],
        }
