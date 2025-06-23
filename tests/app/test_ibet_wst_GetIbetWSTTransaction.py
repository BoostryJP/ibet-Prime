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

from app.model.db import EthIbetWSTTx, IbetWSTTxStatus, IbetWSTTxType, IbetWSTVersion
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestGetIbetWSTTransaction:
    # API endpoint
    api_url = "/ibet_wst/transactions/{tx_id}"

    authorizer = default_eth_account("user1")
    tx_sender = default_eth_account("user2")

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Return transaction details
    async def test_normal_1(self, async_db, async_client):
        # Prepare data
        tx_id = str(uuid.uuid4())
        tx = EthIbetWSTTx()
        tx.tx_id = tx_id
        tx.tx_type = IbetWSTTxType.MINT
        tx.version = IbetWSTVersion.V_1
        tx.status = IbetWSTTxStatus.SUCCEEDED
        tx.tx_params = {}
        tx.tx_sender = self.tx_sender["address"]
        tx.authorizer = self.authorizer["address"]
        tx.authorization = {}
        tx.tx_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        tx.block_number = 12345678
        tx.finalized = True
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
            "tx_sender": self.tx_sender["address"],
            "authorizer": self.authorizer["address"],
            "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "block_number": 12345678,
            "finalized": True,
        }

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
