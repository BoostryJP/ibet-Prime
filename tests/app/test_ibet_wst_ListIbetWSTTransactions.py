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

import uuid

import pytest

from app.model.db import (
    EthIbetWSTTx,
    IbetWSTEventLogTransfer,
    IbetWSTTxParamsMint,
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

    # <Normal_2>
    # Return transactions for the specified address
    async def test_normal_2(self, async_db, async_client):
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
                },
            ],
        }

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
