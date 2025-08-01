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
class TestGetERC20Balance:
    # API endpoint
    api_url = "/ibet_wst/erc20/balance"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Return balance of account
    @mock.patch(
        "app.routers.misc.ibet_wst.ERC20.balance_of", AsyncMock(return_value=1000)
    )
    async def test_normal_1(self, async_client, async_db):
        # Define parameters
        account_address = "0x234567890abCDEf1234567890aBCdEf123456789"
        token_address = "0xbCDEfAbcDefaBcDEfaBcdEfABcdEFAbcDefAbCdE"

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "token_address": token_address,
                "account_address": account_address,
            },
        )

        # Check response status code
        assert resp.status_code == 200
        assert resp.json() == {"balance": 1000}

    # <Normal_2>
    # Return 0 balance if token does not exist
    async def test_normal_2(self, async_client, async_db):
        # Define parameters
        account_address = "0x234567890abCDEf1234567890aBCdEf123456789"
        token_address = "0xbCDEfAbcDefaBcDEfaBcdEfABcdEFAbcDefAbCdE"

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "token_address": token_address,
                "account_address": account_address,
            },
        )

        # Check response status code
        assert resp.status_code == 200
        assert resp.json() == {"balance": 0}

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Missing parameters
    # - Return 422 error
    async def test_error_1(self, async_client):
        # Send request
        resp = await async_client.get(
            self.api_url,
            params={},
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["query", "token_address"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["query", "account_address"],
                    "msg": "Field required",
                    "input": {},
                },
            ],
        }

    # <Error_2>
    # Invalid addresses
    # - Return 422 error
    async def test_error_2(self, async_client):
        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "token_address": "invalid_address",
                "account_address": "invalid_address",
            },
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["query", "token_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
            ],
        }
