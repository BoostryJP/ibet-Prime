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
class TestListIbetWSTTrades:
    # API URL for testing
    apiurl = "/ibet_wst/trades/{ibet_wst_address}"

    # Test IbetWST and token addresses
    ibet_wst_address_1 = "0x1234567890123456789012345678900000000001"
    ibet_wst_address_2 = "0x1234567890123456789012345678900000000002"

    # Test user addresses
    user_address_1 = "0x1234567890123456789012345678900000001000"
    user_address_2 = "0x1234567890123456789012345678900000002000"

    # Test SC token addresses
    sc_token_address_1 = "0x1234567890123456789012345678900000001001"
    sc_token_address_2 = "0x1234567890123456789012345678900000001002"

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
    # Fetch trades for a specific IbetWST address
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
        trade3 = {
            "ibet_wst_address": self.ibet_wst_address_2,  # Different IbetWST address (not targeted)
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",
            "memo": "test3",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)
        await self.insert_trade_eth(async_db, trade3)

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1)
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
                },
                {
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
                },
            ],
        }

    # <Normal_1_2>
    # Fetch trades for a specific IbetWST address
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
        trade3 = {
            "ibet_wst_address": self.ibet_wst_address_2,  # Different IbetWST address (not targeted)
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",
            "memo": "test3",
        }
        await self.insert_trade_ava(async_db, trade1)
        await self.insert_trade_ava(async_db, trade2)
        await self.insert_trade_ava(async_db, trade3)

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"blockchain_platform": "avalanche"},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
                },
                {
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
                },
            ],
        }

    # <Normal_1_3>
    # Fetch rejected trades via the state filter.
    async def test_normal_1_3(self, async_client: AsyncClient, async_db: AsyncSession):
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
            "state": "Rejected",
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
            "state": "Pending",
            "memo": "test2",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)

        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"state": "Rejected"},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
                    "index": 1,
                    "seller_st_account_address": self.user_address_1,
                    "buyer_st_account_address": self.user_address_2,
                    "sc_token_address": self.sc_token_address_1,
                    "seller_sc_account_address": self.user_address_1,
                    "buyer_sc_account_address": self.user_address_2,
                    "st_value": 1000,
                    "sc_value": 2000,
                    "state": "Rejected",
                    "memo": "test1",
                }
            ],
        }

    # <Normal_2_1>
    # Search filtering: seller_st_account_address
    async def test_normal_2_1(self, async_client: AsyncClient, async_db: AsyncSession):
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
            "seller_st_account_address": self.user_address_2,  # Different address (not targeted)
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

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"seller_st_account_address": self.user_address_1},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
            ],
        }

    # <Normal_2_2>
    # Search filtering: buyer_st_account_address
    async def test_normal_2_2(self, async_client: AsyncClient, async_db: AsyncSession):
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
            "buyer_st_account_address": self.user_address_1,  # Different address (not targeted)
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

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"buyer_st_account_address": self.user_address_2},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
            ],
        }

    # <Normal_2_3>
    # Search filtering: sc_token_address
    async def test_normal_2_3(self, async_client: AsyncClient, async_db: AsyncSession):
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
            "sc_token_address": self.sc_token_address_2,  # Different address (not targeted)
            "seller_sc_account_address": self.user_address_2,
            "buyer_sc_account_address": self.user_address_1,
            "st_value": 3000,
            "sc_value": 4000,
            "state": "Executed",
            "memo": "test2",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"sc_token_address": self.sc_token_address_1},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
            ],
        }

    # <Normal_2_4>
    # Search filtering: seller_sc_account_address
    async def test_normal_2_4(self, async_client: AsyncClient, async_db: AsyncSession):
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
            "seller_sc_account_address": self.user_address_2,  # Different address (not targeted)
            "buyer_sc_account_address": self.user_address_1,
            "st_value": 3000,
            "sc_value": 4000,
            "state": "Executed",
            "memo": "test2",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"seller_sc_account_address": self.user_address_1},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
            ],
        }

    # <Normal_2_5>
    # Search filtering: buyer_sc_account_address
    async def test_normal_2_5(self, async_client: AsyncClient, async_db: AsyncSession):
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
            "buyer_sc_account_address": self.user_address_1,  # Different address (not targeted)
            "st_value": 3000,
            "sc_value": 4000,
            "state": "Executed",
            "memo": "test2",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"buyer_sc_account_address": self.user_address_2},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
            ],
        }

    # <Normal_2_6>
    # Search filtering: state
    async def test_normal_2_6(self, async_client: AsyncClient, async_db: AsyncSession):
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
            "state": "Executed",  # Different state (not targeted)
            "memo": "test2",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"state": "Pending"},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "trades": [
                {
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
            ],
        }

    # <Normal_3>
    # Pagination: offset and limit
    async def test_normal_3(self, async_client: AsyncClient, async_db: AsyncSession):
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
        trade3 = {
            "ibet_wst_address": self.ibet_wst_address_1,
            "index": 3,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 5000,
            "sc_value": 6000,
            "state": "Pending",
            "memo": "test3",
        }
        await self.insert_trade_eth(async_db, trade1)
        await self.insert_trade_eth(async_db, trade2)
        await self.insert_trade_eth(async_db, trade3)

        # API call
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={"offset": 1, "limit": 1},
        )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "trades": [
                {
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
                },
            ],
        }

    # <Normal_4>
    # Boundary values: st_value and sc_value with maximum values for int64 and uint256
    # RESPONSE_VALIDATION_MODE is set False to allow testing of large values without validation errors
    async def test_normal_4(self, async_client: AsyncClient, async_db: AsyncSession):
        # Create test data
        trade1 = {
            "ibet_wst_address": self.ibet_wst_address_1,
            "index": 1,
            "seller_st_account_address": self.user_address_1,
            "buyer_st_account_address": self.user_address_2,
            "sc_token_address": self.sc_token_address_1,
            "seller_sc_account_address": self.user_address_1,
            "buyer_sc_account_address": self.user_address_2,
            "st_value": 2**63 - 1,  # Maximum value for int64
            "sc_value": 2**256 - 1,  # Maximum value for uint256
            "state": "Pending",
            "memo": "test1",
        }
        await self.insert_trade_eth(async_db, trade1)

        # API call
        with mock.patch("app.main.RESPONSE_VALIDATION_MODE", False):
            resp = await async_client.get(
                self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1)
            )

        # Response validation
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "trades": [
                {
                    "index": 1,
                    "seller_st_account_address": self.user_address_1,
                    "buyer_st_account_address": self.user_address_2,
                    "sc_token_address": self.sc_token_address_1,
                    "seller_sc_account_address": self.user_address_1,
                    "buyer_sc_account_address": self.user_address_2,
                    "st_value": 2**63 - 1,
                    "sc_value": 2**256 - 1,
                    "state": "Pending",
                    "memo": "test1",
                },
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Invalid IbetWST address format
    async def test_error_1(self, async_client: AsyncClient):
        # Call API with an invalid IbetWST address
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address="invalid_address")
        )

        # Validate response
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

    # <Error_2>
    async def test_error_2(self, async_client: AsyncClient, async_db: AsyncSession):
        # Call API with various invalid query parameters
        resp = await async_client.get(
            self.apiurl.format(ibet_wst_address=self.ibet_wst_address_1),
            params={
                "seller_st_account_address": "invalid_address",
                "buyer_st_account_address": "invalid_address",
                "sc_token_address": "invalid_address",
                "seller_sc_account_address": "invalid_address",
                "buyer_sc_account_address": "invalid_address",
                "state": "InvalidState",
                "offset": -1,
                "limit": -1,
            },
        )

        # Response validation
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "greater_than_equal",
                    "loc": ["query", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": "-1",
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["query", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": "-1",
                    "ctx": {"ge": 0},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "seller_st_account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "buyer_st_account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "sc_token_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "seller_sc_account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "buyer_sc_account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "literal_error",
                    "loc": ["query", "state"],
                    "msg": "Input should be 'Pending', 'Executed', 'Cancelled' or 'Rejected'",
                    "input": "InvalidState",
                    "ctx": {
                        "expected": "'Pending', 'Executed', 'Cancelled' or 'Rejected'"
                    },
                },
            ],
        }
