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

import pytest
from eth_utils import to_checksum_address

from app.model.db import IDXEthIbetWSTWhitelist
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestRetrieveIbetWSTWhitelistAccounts:
    # API endpoint
    api_url = "/ibet_wst/whitelists/{ibet_wst_address}"

    user1 = default_eth_account("user1")
    user2 = default_eth_account("user2")

    wst_token_address_1 = "0x1234567890abcdef1234567890abcdef12345678"
    wst_token_address_2 = "0x234567890abcdef1234567890abcdef123456789"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Whitelist account is not registered for the specified WST token address.
    async def test_normal_1(self, async_db, async_client):
        # Prepare test data
        whitelist = IDXEthIbetWSTWhitelist(
            ibet_wst_address=to_checksum_address(
                self.wst_token_address_2
            ),  # WST token address not to be queried
            st_account_address=self.user1["address"],
            sc_account_address_in=self.user1["address"],
            sc_account_address_out=self.user1["address"],
        )
        async_db.add(whitelist)
        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url.format(ibet_wst_address=self.wst_token_address_1),
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "whitelist_accounts": [],
        }

    # <Normal_2>
    # Whitelist accounts are registered for the specified WST token address.
    async def test_normal_2(self, async_db, async_client):
        # Prepare test data
        whitelist_1 = IDXEthIbetWSTWhitelist(
            ibet_wst_address=to_checksum_address(self.wst_token_address_1),
            st_account_address=self.user1["address"],
            sc_account_address_in=self.user1["address"],
            sc_account_address_out=self.user1["address"],
        )
        whitelist_2 = IDXEthIbetWSTWhitelist(
            ibet_wst_address=to_checksum_address(self.wst_token_address_1),
            st_account_address=self.user2["address"],
            sc_account_address_in=self.user2["address"],
            sc_account_address_out=self.user2["address"],
        )
        async_db.add(whitelist_1)
        async_db.add(whitelist_2)
        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url.format(ibet_wst_address=self.wst_token_address_1),
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "whitelist_accounts": [
                {
                    "st_account_address": self.user2["address"],
                    "sc_account_address_in": self.user2["address"],
                    "sc_account_address_out": self.user2["address"],
                },
                {
                    "st_account_address": self.user1["address"],
                    "sc_account_address_in": self.user1["address"],
                    "sc_account_address_out": self.user1["address"],
                },
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Invalid WST token address format.
    async def test_error_1(self, async_client):
        # Send request with invalid WST token address format
        resp = await async_client.get(
            self.api_url.format(ibet_wst_address="invalid_address"),
        )

        # Check response
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
                }
            ],
        }
