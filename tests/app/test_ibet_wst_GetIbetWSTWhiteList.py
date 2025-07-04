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
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
class TestGetIbetWSTWhiteList:
    # API endpoint
    api_url = "/ibet_wst/whitelists/{account_address}/{ibet_wst_address}"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Return whitelist status of account
    @mock.patch(
        "app.routers.misc.ibet_wst.IbetWST.account_white_list",
        AsyncMock(return_value=True),
    )
    async def test_normal_1(self, async_client):
        # Define parameters
        account_address = "0x1234567890abcdef1234567890abcdef12345678"
        ibet_wst_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"

        # Send request
        resp = await async_client.get(
            self.api_url.format(
                account_address=account_address,
                ibet_wst_address=ibet_wst_address,
            )
        )

        # Check response status code
        assert resp.status_code == 200
        assert resp.json() == {"whitelisted": True}

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Invalid addresses
    async def test_error_1(self, async_client):
        # Send request with invalid addresses
        resp = await async_client.get(
            self.api_url.format(
                account_address="invalid_address",
                ibet_wst_address="invalid_address",
            )
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["path", "ibet_wst_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["path", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
            ],
        }
