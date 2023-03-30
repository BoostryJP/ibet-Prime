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
from unittest.mock import MagicMock

from app.exceptions import ServiceUnavailableError


class TestAppRoutersBlockNumberGET:
    # target API endpoint
    apiurl = "/block_number"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @mock.patch("web3.eth.Eth.block_number", 100)
    def test_normal_1(self, client, db):
        # request target api
        resp = client.get(self.apiurl)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {"block_number": 100}

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Unable to connect ibet
    @mock.patch(
        "web3.eth.eth.Eth.get_block_number",
        MagicMock(side_effect=ServiceUnavailableError("")),
    )
    def test_error_1(self, client, db):
        # request target api
        resp = client.get(self.apiurl)

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 1, "title": "ServiceUnavailableError"},
            "detail": "",
        }
