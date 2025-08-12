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

from app.model.db import (
    IDXPersonalInfo,
    PersonalInfoDataSource,
    Token,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from app.model.eth.wst import IbetWSTWhiteList


@pytest.mark.asyncio
class TestGetIbetWSTWhiteList:
    # API endpoint
    api_url = "/tokens/{token_address}/ibet_wst/whitelists/{account_address}"

    issuer_address = "0x1234567890abcdef1234567890abcdef12345678"
    ibet_token_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    ibet_wst_address = "0xbcdefabcdefabcdefabcdefabcdefabcdefabcde"

    st_account_address = "0x1234567890abcdef1234567890abcdef12345678"
    sc_account_address_in = "0x234567890abcdef1234567890abcdef123456789"
    sc_account_address_out = "0x34567890abcdef1234567890abcdef1234567890"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # Return whitelist status of account
    # - Personal information is not registered
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
        # Prepare data
        token = Token(
            type=TokenType.IBET_STRAIGHT_BOND,
            tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            issuer_address=to_checksum_address(self.issuer_address),
            token_address=to_checksum_address(self.ibet_token_address),
            version=TokenVersion.V_25_09,
            abi={},
            token_status=TokenStatus.SUCCEEDED,
            ibet_wst_activated=True,
            ibet_wst_deployed=True,
            ibet_wst_address=to_checksum_address(self.ibet_wst_address),
        )
        async_db.add(token)
        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url.format(
                token_address=self.ibet_token_address,
                account_address=self.st_account_address,
            ),
            headers={"issuer-address": self.issuer_address},
        )

        # Check response status code
        assert resp.status_code == 200
        assert resp.json() == {
            "st_account_address": to_checksum_address(self.st_account_address),
            "st_account_personal_info": None,
            "sc_account_address_in": to_checksum_address(self.sc_account_address_in),
            "sc_account_address_out": to_checksum_address(self.sc_account_address_out),
            "listed": True,
        }

    # <Normal_1_2>
    # Return whitelist status of account
    # - Personal information is registered
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
    async def test_normal_2(self, async_client, async_db):
        # Prepare data
        token = Token(
            type=TokenType.IBET_STRAIGHT_BOND,
            tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            issuer_address=to_checksum_address(self.issuer_address),
            token_address=to_checksum_address(self.ibet_token_address),
            version=TokenVersion.V_25_09,
            abi={},
            token_status=TokenStatus.SUCCEEDED,
            ibet_wst_activated=True,
            ibet_wst_deployed=True,
            ibet_wst_address=to_checksum_address(self.ibet_wst_address),
        )
        async_db.add(token)

        account_personal_info = IDXPersonalInfo(
            account_address=to_checksum_address(self.st_account_address),
            issuer_address=to_checksum_address(self.issuer_address),
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
        async_db.add(account_personal_info)
        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url.format(
                token_address=self.ibet_token_address,
                account_address=self.st_account_address,
            ),
            headers={"issuer-address": self.issuer_address},
        )

        # Check response status code
        assert resp.status_code == 200
        assert resp.json() == {
            "st_account_address": to_checksum_address(self.st_account_address),
            "st_account_personal_info": {
                "key_manager": "test_key_manager",
                "name": "User One",
                "postal_code": "1234567",
                "address": "123 User Street",
                "email": "test@example.com",
                "birth": "19900101",
                "is_corporate": False,
                "tax_category": 0,
            },  # Personal information
            "sc_account_address_in": to_checksum_address(self.sc_account_address_in),
            "sc_account_address_out": to_checksum_address(self.sc_account_address_out),
            "listed": True,
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Missing issuer address in request header
    # - Expected to return 422
    async def test_error_1(self, async_client):
        # Send request without issuer address in header
        resp = await async_client.get(
            self.api_url.format(
                token_address=self.ibet_token_address,
                account_address=self.st_account_address,
            ),
        )

        # Check response status code
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
    # Invalid addresses
    # - Expected to return 422
    async def test_error_2(self, async_client):
        # Send request with invalid addresses
        resp = await async_client.get(
            self.api_url.format(
                token_address="invalid_address",
                account_address="invalid_address",
            ),
            headers={"issuer-address": self.issuer_address},
        )

        # Check response status code
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

    # <Error_3>
    # Token not found
    # - Expected to return 404
    async def test_error_3(self, async_client, async_db):
        # Prepare data
        # Send request
        resp = await async_client.get(
            self.api_url.format(
                token_address=self.ibet_token_address,
                account_address=self.st_account_address,
            ),
            headers={"issuer-address": self.issuer_address},
        )

        # Check response status code
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "Token not found",
        }
