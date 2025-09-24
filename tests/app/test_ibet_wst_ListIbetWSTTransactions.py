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
    IbetWSTEventLogTradeRequested,
    IbetWSTEventLogTransfer,
    IbetWSTTxParamsMint,
    IbetWSTTxParamsRequestTrade,
    IbetWSTTxParamsTransfer,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
)
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestListIbetWSTTransactions:
    # API endpoint
    api_url = "/ibet_wst/transactions"

    tx_sender = default_eth_account("user1")
    user1 = default_eth_account("user2")
    user2 = default_eth_account("user3")
    authorizer_1 = default_eth_account("user4")
    authorizer_2 = default_eth_account("user5")

    wst_token_address_1 = "0x1234567890AbcdEF1234567890aBcdef12345678"
    wst_token_address_2 = "0x234567890abCDEf1234567890aBCdEf123456789"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Return empty list when no transactions found for the specified address
    async def test_normal_1(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_2  # Different address
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        async_db.add(tx_1)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0,
            },
            "transactions": [],
        }

    # <Normal_2_1>
    # Return transactions for the specified address
    async def test_normal_2_1(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.MINT
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SENT
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_2["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = False
        tx_2.event_log = None
        tx_2.created = datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_2,
                    "tx_type": IbetWSTTxType.MINT,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SENT,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_2["address"],
                    "tx_hash": "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 23456789,
                    "finalized": False,
                    "event_log": None,
                    "created": "2025-02-03T13:05:06+09:00",
                },
                {
                    "tx_id": tx_id_1,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 12345678,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-02T12:04:05+09:00",
                },
            ],
        }

    # <Normal_2_2>
    # Return transactions for the specified address
    # - For trade-related transactions, display_sc_value is set based on sc_value and sc_decimals
    async def test_normal_2_2(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.REQUEST_TRADE
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsRequestTrade(
            seller_st_account="0x1234567890AbcdEF1234567890aBcdef12345678",
            buyer_st_account="0x234567890abCDEf1234567890aBCdEf123456789",
            sc_token_address="0x34567890abCdEF1234567890abcDeF1234567890",
            st_value=100,
            sc_value=1234567890,
            memo="Test trade request",
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTradeRequested(
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
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
            },
        )

        # Check response
        assert resp.status_code == 200
        assert (
            resp.json()
            == {
                "result_set": {
                    "count": 1,
                    "offset": None,
                    "limit": None,
                    "total": 1,
                },
                "transactions": [
                    {
                        "tx_id": tx_id_1,
                        "tx_type": IbetWSTTxType.REQUEST_TRADE,
                        "version": IbetWSTVersion.V_1,
                        "status": IbetWSTTxStatus.SUCCEEDED,
                        "ibet_wst_address": self.wst_token_address_1,
                        "tx_sender": self.tx_sender["address"],
                        "authorizer": self.authorizer_1["address"],
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
                    },
                ],
            }
        )

    # <Normal_3_1>
    # Filter by tx_id
    async def test_normal_3_1(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.MINT
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SENT
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_2["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = False
        tx_2.event_log = None
        tx_2.created = datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "tx_id": tx_id_1,  # Filter by tx_id
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_1,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 12345678,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-02T12:04:05+09:00",
                }
            ],
        }

    # <Normal_3_2>
    # Filter by tx_type
    async def test_normal_3_2(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.MINT
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SENT
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_2["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = False
        tx_2.event_log = None
        tx_2.created = datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "tx_type": "transfer",  # Filter by tx_type
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_1,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 12345678,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-02T12:04:05+09:00",
                }
            ],
        }

    # <Normal_3_3>
    # Filter by tx_hash
    async def test_normal_3_3(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.MINT
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SENT
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_2["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = False
        tx_2.event_log = None
        tx_2.created = datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",  # Filter by tx_hash
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_1,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 12345678,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-02T12:04:05+09:00",
                }
            ],
        }

    # <Normal_3_4>
    # Filter by authorizer
    async def test_normal_3_4(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.MINT
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SENT
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_2["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = False
        tx_2.event_log = None
        tx_2.created = datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "authorizer": self.authorizer_1["address"],  # Filter by authorizer
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_1,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 12345678,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-02T12:04:05+09:00",
                }
            ],
        }

    # <Normal_3_5>
    # Filter by finalized status
    async def test_normal_3_5(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.MINT
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SENT
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_2["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = False
        tx_2.event_log = None
        tx_2.created = datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={"ibet_wst_address": self.wst_token_address_1, "finalized": True},
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_1,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 12345678,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-02T12:04:05+09:00",
                }
            ],
        }

    # <Normal_3_6>
    # Filter by created date range
    async def test_normal_3_6(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2024, 12, 31, 14, 59, 59, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.TRANSFER
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SUCCEEDED
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_1["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = True
        tx_2.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_2.created = datetime.datetime(2024, 12, 31, 15, 0, 0, tzinfo=None)
        async_db.add(tx_2)

        tx_id_3 = str(uuid.uuid4())
        tx_3 = EthIbetWSTTx()
        tx_3.tx_id = tx_id_3
        tx_3.tx_type = IbetWSTTxType.TRANSFER
        tx_3.version = IbetWSTVersion.V_1
        tx_3.status = IbetWSTTxStatus.SENT
        tx_3.ibet_wst_address = self.wst_token_address_1
        tx_3.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_3.tx_sender = self.tx_sender["address"]
        tx_3.authorizer = self.authorizer_1["address"]
        tx_3.authorization = {}
        tx_3.tx_hash = (
            "0x34567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_3.block_number = 34567890
        tx_3.finalized = False
        tx_3.event_log = None
        tx_3.created = datetime.datetime(2025, 1, 31, 15, 0, 1, tzinfo=None)
        async_db.add(tx_3)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "created_from": "2025-01-01 00:00:00",
                "created_to": "2025-02-01 00:00:00",
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 3,
            },
            "transactions": [
                {
                    "tx_id": tx_id_2,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 23456789,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-01T00:00:00+09:00",
                }
            ],
        }

    # <Normal_3_7>
    # Filter by status
    async def test_normal_3_7(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2024, 12, 31, 14, 59, 59, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.TRANSFER
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.FAILED
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_1["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = True
        tx_2.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_2.created = datetime.datetime(2024, 12, 31, 15, 0, 0, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "status": 3,  # Filter by status
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_2,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.FAILED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 23456789,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-01T00:00:00+09:00",
                }
            ],
        }

    # <Normal_4>
    # Return transactions with pagination
    async def test_normal_4(self, async_db, async_client):
        # Prepare data
        tx_id_1 = str(uuid.uuid4())
        tx_1 = EthIbetWSTTx()
        tx_1.tx_id = tx_id_1
        tx_1.tx_type = IbetWSTTxType.TRANSFER
        tx_1.version = IbetWSTVersion.V_1
        tx_1.status = IbetWSTTxStatus.SUCCEEDED
        tx_1.ibet_wst_address = self.wst_token_address_1
        tx_1.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        tx_1.tx_sender = self.tx_sender["address"]
        tx_1.authorizer = self.authorizer_1["address"]
        tx_1.authorization = {}
        tx_1.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_1.block_number = 12345678
        tx_1.finalized = True
        tx_1.event_log = IbetWSTEventLogTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
        )
        tx_1.created = datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=None)
        async_db.add(tx_1)

        tx_id_2 = str(uuid.uuid4())
        tx_2 = EthIbetWSTTx()
        tx_2.tx_id = tx_id_2
        tx_2.tx_type = IbetWSTTxType.MINT
        tx_2.version = IbetWSTVersion.V_1
        tx_2.status = IbetWSTTxStatus.SENT
        tx_2.ibet_wst_address = self.wst_token_address_1
        tx_2.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        tx_2.tx_sender = self.tx_sender["address"]
        tx_2.authorizer = self.authorizer_2["address"]
        tx_2.authorization = {}
        tx_2.tx_hash = (
            "0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx_2.block_number = 23456789
        tx_2.finalized = False
        tx_2.event_log = None
        tx_2.created = datetime.datetime(2025, 2, 3, 4, 5, 6, tzinfo=None)
        async_db.add(tx_2)

        await async_db.commit()

        # Send request with pagination
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "limit": 1,
                "offset": 1,
            },
        )

        # Check response
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": 1,
                "limit": 1,
                "total": 2,
            },
            "transactions": [
                {
                    "tx_id": tx_id_1,
                    "tx_type": IbetWSTTxType.TRANSFER,
                    "version": IbetWSTVersion.V_1,
                    "status": IbetWSTTxStatus.SUCCEEDED,
                    "ibet_wst_address": self.wst_token_address_1,
                    "tx_sender": self.tx_sender["address"],
                    "authorizer": self.authorizer_1["address"],
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "block_number": 12345678,
                    "finalized": True,
                    "event_log": {
                        "from_address": self.user1["address"],
                        "to_address": self.user2["address"],
                        "value": 1000,
                    },
                    "created": "2025-01-02T12:04:05+09:00",
                }
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Return error when required query parameter is missing
    async def test_error_1(self, async_db, async_client):
        # Send request with pagination
        resp = await async_client.get(self.api_url, params={})

        # Check response
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["query", "ibet_wst_address"],
                    "msg": "Field required",
                    "input": {},
                }
            ],
        }

    # <Error_2>
    # Return error when query parameters are invalid
    async def test_error_2(self, async_db, async_client):
        # Send request with pagination
        resp = await async_client.get(
            self.api_url,
            params={
                "ibet_wst_address": self.wst_token_address_1,
                "tx_type": "invalid-type",  # Invalid tx_type
                "status": 999,  # Invalid status
                "authorizer": "invalid-address",  # Invalid authorizer address
                "created_from": "invalid-date",  # Invalid date format
                "created_to": "invalid-date",  # Invalid date format
            },
        )

        # Check response
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "literal_error",
                    "loc": ["query", "tx_type"],
                    "msg": "Input should be 'deploy', 'mint', 'burn', 'force_burn', 'add_whitelist', 'delete_whitelist', 'transfer', 'request_trade', 'cancel_trade', 'accept_trade' or 'reject_trade'",
                    "input": "invalid-type",
                    "ctx": {
                        "expected": "'deploy', 'mint', 'burn', 'force_burn', 'add_whitelist', 'delete_whitelist', 'transfer', 'request_trade', 'cancel_trade', 'accept_trade' or 'reject_trade'"
                    },
                },
                {
                    "type": "enum",
                    "loc": ["query", "status"],
                    "msg": "Input should be 0, 1, 2 or 3",
                    "input": "999",
                    "ctx": {"expected": "0, 1, 2 or 3"},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "authorizer"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid-address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "created_from"],
                    "msg": "Value error, value must be of string datetime format",
                    "input": "invalid-date",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "created_to"],
                    "msg": "Value error, value must be of string datetime format",
                    "input": "invalid-date",
                    "ctx": {"error": {}},
                },
            ],
        }
