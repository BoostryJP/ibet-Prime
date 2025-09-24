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

from app.model.db import (
    IDXEthIbetWSTWhitelist,
    IDXPersonalInfo,
    PersonalInfoDataSource,
    Token,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestRetrieveIbetWSTWhitelistAccountsWithPersonalInfo:
    # API endpoint
    api_url = "/tokens/{token_address}/ibet_wst/whitelists"

    issuer = default_eth_account("user1")
    user1 = default_eth_account("user2")
    user2 = default_eth_account("user3")

    token_address_1 = "0x1234567890abcdef1234567890abcdef12345678"
    wst_token_address_1 = "0xabcdef1234567890abcdef1234567890abcdef12"

    token_address_2 = "0x234567890abcdef1234567890abcdef123456789"
    wst_token_address_2 = "0xbcdef1234567890abcdef1234567890abcdef123"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Whitelist account is not registered for the specified WST token address.
    async def test_normal_1(self, async_db, async_client):
        # Prepare test data
        token = Token(
            type=TokenType.IBET_STRAIGHT_BOND,
            tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            issuer_address=self.issuer["address"],
            token_address=to_checksum_address(self.token_address_1),
            version=TokenVersion.V_25_09,
            abi={},
            token_status=TokenStatus.SUCCEEDED,
            ibet_wst_activated=True,
            ibet_wst_deployed=True,
            ibet_wst_address=to_checksum_address(self.wst_token_address_1),
        )
        async_db.add(token)

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
            self.api_url.format(token_address=self.token_address_1),
            headers={"issuer-address": self.issuer["address"]},
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
        token = Token(
            type=TokenType.IBET_STRAIGHT_BOND,
            tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            issuer_address=self.issuer["address"],
            token_address=to_checksum_address(self.token_address_1),
            version=TokenVersion.V_25_09,
            abi={},
            token_status=TokenStatus.SUCCEEDED,
            ibet_wst_activated=True,
            ibet_wst_deployed=True,
            ibet_wst_address=to_checksum_address(self.wst_token_address_1),
        )
        async_db.add(token)

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

        user1_personal_info = IDXPersonalInfo(
            account_address=self.user1["address"],
            issuer_address=self.issuer["address"],
            _personal_info={
                "key_manager": "test_key_manager",
                "name": "User One",
                "postal_code": "1234567",
                "address": "123 User Street",
                "email": "test@example.com",
                "birth": "19900101",
                "is_corporate": False,
                "tax_category": 0,
            },
            data_source=PersonalInfoDataSource.OFF_CHAIN,
        )
        async_db.add(user1_personal_info)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url.format(token_address=self.token_address_1),
            headers={"issuer-address": self.issuer["address"]},
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "whitelist_accounts": [
                {
                    "st_account_address": self.user2["address"],
                    "st_account_personal_info": None,
                    "sc_account_address_in": self.user2["address"],
                    "sc_account_address_out": self.user2["address"],
                },
                {
                    "st_account_address": self.user1["address"],
                    "st_account_personal_info": {
                        "key_manager": "test_key_manager",
                        "name": "User One",
                        "postal_code": "1234567",
                        "address": "123 User Street",
                        "email": "test@example.com",
                        "birth": "19900101",
                        "is_corporate": False,
                        "tax_category": 0,
                    },
                    "sc_account_address_in": self.user1["address"],
                    "sc_account_address_out": self.user1["address"],
                },
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Request without issuer address
    # - Expected to return 422
    async def test_error_1(self, async_client):
        # Send request without issuer address in header
        resp = await async_client.get(
            self.api_url.format(token_address=self.token_address_1),
        )

        # Check response
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "input": None,
                }
            ],
        }

    # <Error_2>
    # Invalid token address format
    # - Expected to return 422
    async def test_error_2(self, async_client):
        # Send request with invalid token address format
        resp = await async_client.get(
            self.api_url.format(token_address="invalid_address"),
            headers={"issuer-address": self.issuer["address"]},
        )

        # Check response
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["path", "token_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_3>
    # Token not found for the specified address
    # - Expected to return 404
    async def test_error_3(self, async_client):
        # Send request with a token address that does not exist
        resp = await async_client.get(
            self.api_url.format(token_address=self.token_address_1),
            headers={"issuer-address": self.issuer["address"]},
        )

        # Check response
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "Token not found",
        }
