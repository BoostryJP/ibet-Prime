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

from app.model.db.ibet_wst import IDXEthIbetWSTTrade


@pytest.mark.asyncio
class TestListIbetWSTTrades:
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
    async def insert_trade(async_db, trade_data):
        """Insert a trade record into the database."""
        trade = IDXEthIbetWSTTrade(**trade_data)
        async_db.add(trade)
        await async_db.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    async def test_normal_1(self, async_client, async_db):
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
        await self.insert_trade(async_db, trade1)
        await self.insert_trade(async_db, trade2)

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

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    async def test_error_1(self, async_client, async_db):
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
