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

import datetime
import uuid

import pytest

from app.model.db import (
    EthIbetWSTTx,
    IbetWSTEventLogMint,
    IbetWSTEventLogTradeRequested,
    IbetWSTTxParamsMint,
    IbetWSTTxParamsRequestTrade,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
)
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestGetIbetWSTTransaction:
    # API endpoint
    api_url = "/ibet_wst/transactions/{tx_id}"

    authorizer = default_eth_account("user1")
    tx_sender = default_eth_account("user2")
    user1 = default_eth_account("user3")

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # Return transaction details
    async def test_normal_1_1(self, async_db, async_client):
        # Prepare data
        tx_id = str(uuid.uuid4())
        tx = EthIbetWSTTx()
        tx.tx_id = tx_id
        tx.tx_type = IbetWSTTxType.MINT
        tx.version = IbetWSTVersion.V_1
        tx.status = IbetWSTTxStatus.SUCCEEDED
        tx.ibet_wst_address = "0x1234567890abcdef1234567890abcdef12345678"
        tx.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx.tx_sender = self.tx_sender["address"]
        tx.authorizer = self.authorizer["address"]
        tx.authorization = {}
        tx.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx.block_number = 12345678
        tx.finalized = True
        tx.event_log = IbetWSTEventLogMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx)
        await async_db.commit()

        # Send request
        resp = await async_client.get(self.api_url.format(tx_id=tx_id))

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "tx_id": tx_id,
            "tx_type": IbetWSTTxType.MINT,
            "version": IbetWSTVersion.V_1,
            "status": IbetWSTTxStatus.SUCCEEDED,
            "ibet_wst_address": "0x1234567890abcdef1234567890abcdef12345678",
            "tx_sender": self.tx_sender["address"],
            "authorizer": self.authorizer["address"],
            "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "block_number": 12345678,
            "finalized": True,
            "event_log": {
                "to_address": self.user1["address"],
                "value": 1000,
            },
            "created": "2025-01-02T12:04:05+09:00",
        }

    # <Normal_1_2>
    # Return transaction details
    # - For trade-related transactions, display_sc_value is set based on sc_value and sc_decimals
    async def test_normal_1_2(self, async_db, async_client):
        # Prepare data
        tx_id = str(uuid.uuid4())
        tx = EthIbetWSTTx()
        tx.tx_id = tx_id
        tx.tx_type = IbetWSTTxType.REQUEST_TRADE
        tx.version = IbetWSTVersion.V_1
        tx.status = IbetWSTTxStatus.SUCCEEDED
        tx.ibet_wst_address = "0x1234567890abcdef1234567890abcdef12345678"
        tx.tx_params = IbetWSTTxParamsRequestTrade(
            seller_st_account="0x1234567890AbcdEF1234567890aBcdef12345678",
            buyer_st_account="0x234567890abCDEf1234567890aBCdEf123456789",
            sc_token_address="0x34567890abCdEF1234567890abcDeF1234567890",
            st_value=100,
            sc_value=1234567890,
            memo="Test trade request",
        )
        tx.tx_sender = self.tx_sender["address"]
        tx.authorizer = self.authorizer["address"]
        tx.authorization = {}
        tx.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx.block_number = 12345678
        tx.finalized = True
        tx.event_log = IbetWSTEventLogTradeRequested(
            index=111,
            seller_st_account_address="0x1234567890AbcdEF1234567890aBcdef12345678",
            buyer_st_account_address="0x234567890abCDEf1234567890aBCdEf123456789",
            sc_token_address="0x34567890abCdEF1234567890abcDeF1234567890",
            seller_sc_account_address="0x1234567890AbcdEF1234567890aBcdef12345678",
            buyer_sc_account_address="0x234567890abCDEf1234567890aBCdEf123456789",
            st_value=100,
            sc_value=1234567890,
            sc_decimals=8,
        )
        tx.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx)
        await async_db.commit()

        # Send request
        resp = await async_client.get(self.api_url.format(tx_id=tx_id))

        # Check response
        assert resp.status_code == 200
        assert (
            resp.json()
            == {
                "tx_id": tx_id,
                "tx_type": IbetWSTTxType.REQUEST_TRADE,
                "version": IbetWSTVersion.V_1,
                "status": IbetWSTTxStatus.SUCCEEDED,
                "ibet_wst_address": "0x1234567890abcdef1234567890abcdef12345678",
                "tx_sender": self.tx_sender["address"],
                "authorizer": self.authorizer["address"],
                "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "block_number": 12345678,
                "finalized": True,
                "event_log": {
                    "index": 111,
                    "seller_st_account_address": "0x1234567890AbcdEF1234567890aBcdef12345678",
                    "buyer_st_account_address": "0x234567890abCDEf1234567890aBCdEf123456789",
                    "sc_token_address": "0x34567890abCdEF1234567890abcDeF1234567890",
                    "seller_sc_account_address": "0x1234567890AbcdEF1234567890aBcdef12345678",
                    "buyer_sc_account_address": "0x234567890abCDEf1234567890aBCdEf123456789",
                    "st_value": 100,
                    "sc_value": 1234567890,
                    "display_sc_value": "12.3456789",  # Calculated from sc_value and sc_decimals
                    "sc_decimals": 8,
                },
                "created": "2025-01-02T12:04:05+09:00",
            }
        )

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Transaction not found
    async def test_error_1(self, async_client):
        # Send request with non-existent transaction ID
        resp = await async_client.get(self.api_url.format(tx_id=str(uuid.uuid4())))

        # Check response
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "Transaction not found",
        }
