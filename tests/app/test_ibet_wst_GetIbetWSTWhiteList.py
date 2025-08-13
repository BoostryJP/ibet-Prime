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
from eth_utils import to_checksum_address

from app.model.db import Token, TokenType, TokenVersion
from app.model.eth.wst import IbetWSTWhiteList


@pytest.mark.asyncio
class TestGetIbetWSTWhiteList:
    # API endpoint
    api_url = "/ibet_wst/whitelists/{ibet_wst_address}/{account_address}"

    st_account_address = "0x1234567890abcdef1234567890abcdef12345678"
    sc_account_address_in = "0x234567890abcdef1234567890abcdef123456789"
    sc_account_address_out = "0x34567890abcdef1234567890abcdef1234567890"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Return whitelist status of account
    @mock.patch(
        "app.routers.misc.ibet_wst.IbetWST.account_white_list",
        AsyncMock(
            return_value=IbetWSTWhiteList(
                st_account=to_checksum_address(st_account_address),
                sc_account_in=to_checksum_address(sc_account_address_in),
                sc_account_out=to_checksum_address(sc_account_address_out),
                listed=True,
            )
        ),
    )
    async def test_normal_1(self, async_client, async_db):
        # Define parameters
        issuer_address = "0x1234567890abcdef1234567890abcdef12345678"
        ibet_token_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        ibet_wst_address = "0xbcdefabcdefabcdefabcdefabcdefabcdefabcde"

        # Prepare data: Token
        token = Token()
        token.token_address = to_checksum_address(ibet_token_address)
        token.issuer_address = to_checksum_address(issuer_address)
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_09
        token.ibet_wst_deployed = True
        token.ibet_wst_address = to_checksum_address(ibet_wst_address)
        async_db.add(token)
        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url.format(
                account_address=self.st_account_address,
                ibet_wst_address=ibet_wst_address,
            )
        )

        # Check response status code
        assert resp.status_code == 200
        assert resp.json() == {
            "st_account_address": to_checksum_address(self.st_account_address),
            "sc_account_address_in": to_checksum_address(self.sc_account_address_in),
            "sc_account_address_out": to_checksum_address(self.sc_account_address_out),
            "listed": True,
        }

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

    # <Error_2>
    # ibet-WST token not found
    async def test_error_2(self, async_client, async_db):
        # Define parameters
        account_address = "0x234567890abcdef1234567890abcdef123456789"
        ibet_wst_address = "0xbcdefabcdefabcdefabcdefabcdefabcdefabcde"

        # Send request
        resp = await async_client.get(
            self.api_url.format(
                account_address=account_address,
                ibet_wst_address=ibet_wst_address,
            )
        )

        # Check response status code
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "IbetWST token not found",
        }
