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

from typing import Any
from unittest import mock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.db.ibet_wst import IDXAvaIbetWSTTrade, IDXEthIbetWSTTrade


@pytest.mark.asyncio
class TestGetIbetWSTTrade:
    # API URL for testing
    apiurl = "/ibet_wst/trades/{ibet_wst_address}/{index}"

    # Test IbetWST and token address
    ibet_wst_address_1 = "0x1234567890123456789012345678900000000001"

    # Test user addresses
    user_address_1 = "0x1234567890123456789012345678900000001000"
    user_address_2 = "0x1234567890123456789012345678900000002000"

    # Test SC token address
    sc_token_address_1 = "0x1234567890123456789012345678900000001001"

    @staticmethod
    async def insert_trade_eth(
        async_db: AsyncSession, trade_data: dict[str, Any]
    ) -> None:
        """Insert a trade record into the database."""
        trade = IDXEthIbetWSTTrade(**trade_data)
        async_db.add(trade)
        await async_db.commit()

    @staticmethod
    async def insert_trade_ava(
        async_db: AsyncSession, trade_data: dict[str, Any]
    ) -> None:
        """Insert a trade record into the database."""
        trade = IDXAvaIbetWSTTrade(**trade_data)
        async_db.add(trade)
        await async_db.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # Test normal case with typical values for all fields.
    # This verifies that the API can retrieve and return trade details correctly.
    # - blockchain_platform = "ethereum" (default)
    async def test_normal_1_1(self, async_client: AsyncClient, async_db: AsyncSession):
        # Create test data
        trade1 = {
            "ibet_wst_address": self.ibet_wst_address_1,
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",
            "memo": "test1",
        }
        trade2 = {
            "ibet_wst_address": self.ibet_wst_address_1,
            "index": 2,
            "seller_st_account_address": self.user_address_2,
            "buyer_st_account_address": self.user_address_1,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_2,
            "buyer_sc_account_address": self.user_address_1,
            "st_value": 3000,
            "sc_value": 4000,
            "state": "Executed",
            "memo": "test2",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)

        # Call API
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1, index=1)
        )

        # Validate response
        assert resp.status_code == 200
        assert resp.json() == {
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",
            "memo": "test1",
        }

    # <Normal_1_2>
    # Test normal case with typical values for all fields.
    # This verifies that the API can retrieve and return trade details correctly.
    # - blockchain_platform = "avalanche"
    async def test_normal_1_2(self, async_client: AsyncClient, async_db: AsyncSession):
        # Create test data
        trade1 = {
            "ibet_wst_address": self.ibet_wst_address_1,
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",
            "memo": "test1",
        }
        await self.insert_trade_ava(async_db, trade1)

        # Call API
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1, index=1),
            params={"blockchain_platform": "avalanche"},
        )

        # Validate response
        assert resp.status_code == 200
        assert resp.json() == {
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",
            "memo": "test1",
        }

    # <Normal_1_3>
    # Test that rejected trades are returned without response validation errors.
    async def test_normal_1_3(self, async_client: AsyncClient, async_db: AsyncSession):
        trade = {
            "ibet_wst_address": self.ibet_wst_address_1,
            "index": 3,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 5000,
            "sc_value": 6000,
            "state": "Rejected",
            "memo": "test3",
        }
        await self.insert_trade_eth(async_db, trade)

        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1, index=3)
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "index": 3,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 5000,
            "sc_value": 6000,
            "state": "Rejected",
            "memo": "test3",
        }

    # <Normal_2>
    # This test verifies that the API can handle and return maximum uint256 values correctly.
    # RESPONSE_VALIDATION_MODE is set False to allow the API to return large integers without validation errors.
    async def test_normal_2(self, async_client: AsyncClient, async_db: AsyncSession):
        # Create test data
        trade1 = {
            "ibet_wst_address": self.ibet_wst_address_1,
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 2**63 - 1,  # Maximum int64 value
            "sc_value": 2**256 - 1,  # Maximum uint256 value
            "state": "Pending",
            "memo": "test1",
        }
        await self.insert_trade_eth(async_db, trade1)

        # Call API
        with mock.patch("app.main.RESPONSE_VALIDATION_MODE", False):
            resp = await async_client.get(
                self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1, index=1)
            )

        # Validate response
        assert resp.status_code == 200
        assert resp.json() == {
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 2**63 - 1,  # Maximum int64 value should be returned correctly
            "sc_value": 2**256
            - 1,  # Maximum uint256 value should be returned correctly
            "state": "Pending",
            "memo": "test1",
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    async def test_error_1(self, async_client: AsyncClient, async_db: AsyncSession):
        # Call API with a non-existent IbetWST address
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1, index=1)
        )

        # Validate response
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "Trade not found",
        }
