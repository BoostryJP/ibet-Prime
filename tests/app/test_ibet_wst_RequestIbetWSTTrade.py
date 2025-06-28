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

import secrets
from unittest import mock

import pytest
from eth_utils import to_checksum_address
from sqlalchemy import select

from app.model.db import (
    EthIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
)
from app.model.eth import IbetWST, IbetWSTDigestHelper
from app.utils.eth_contract_utils import EthWeb3
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestAddIbetWSTWhitelist:
    # API endpoint
    api_url = "/ibet_wst/trades/{ibet_wst_address}/request"

    relayer = default_eth_account("user1")
    user1 = default_eth_account("user2")
    user2 = default_eth_account("user3")

    sc_token_address = to_checksum_address("0x1234567890abcdef1234567890abcdef12345678")
    ibet_wst_address = to_checksum_address("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd")

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Add account to whitelist
    @mock.patch(
        "app.routers.misc.ibet_wst.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    async def test_normal_1(self, async_db, async_client):
        # Generate nonce
        nonce = secrets.token_bytes(32)

        # Get domain separator
        token_st = IbetWST(self.ibet_wst_address)
        domain_separator = await token_st.domain_separator()

        # Generate digest
        digest = IbetWSTDigestHelper.generate_request_trade_digest(
            domain_separator=domain_separator,
            seller_st_account_address=self.user1["address"],
            buyer_st_account_address=self.user2["address"],
            sc_token_address=self.sc_token_address,
            seller_sc_account_address=self.user1["address"],
            buyer_sc_account_address=self.user2["address"],
            st_value=1000,
            sc_value=2000,
            memo="Test Trade",
            nonce=nonce,
        )

        # Sign the digest from the authorizer's private key
        signature = EthWeb3.eth.account.unsafe_sign_hash(
            digest, bytes.fromhex(self.user1["private_key"])
        )

        # Send request
        resp = await async_client.post(
            self.api_url.format(ibet_wst_address=self.ibet_wst_address),
            json={
                "seller_st_account_address": self.user1["address"],
                "buyer_st_account_address": self.user2["address"],
                "sc_token_address": self.sc_token_address,
                "seller_sc_account_address": self.user1["address"],
                "buyer_sc_account_address": self.user2["address"],
                "st_value": 1000,
                "sc_value": 2000,
                "memo": "Test Trade",
                "authorizer": self.user1["address"],
                "authorization": {
                    "nonce": nonce.hex(),
                    "v": signature.v,
                    "r": signature.r.to_bytes(32).hex(),
                    "s": signature.s.to_bytes(32).hex(),
                },
            },
        )

        # Check response status code and content
        assert resp.status_code == 200
        assert resp.json() == {"tx_id": mock.ANY}

        # Check transaction creation
        wst_tx = (await async_db.scalars(select(EthIbetWSTTx).limit(1))).first()
        assert wst_tx.tx_type == IbetWSTTxType.REQUEST_TRADE
        assert wst_tx.version == IbetWSTVersion.V_1
        assert wst_tx.status == IbetWSTTxStatus.PENDING
        assert wst_tx.ibet_wst_address == self.ibet_wst_address
        assert wst_tx.tx_params == {
            "seller_st_account_address": self.user1["address"],
            "buyer_st_account_address": self.user2["address"],
            "sc_token_address": self.sc_token_address,
            "seller_sc_account_address": self.user1["address"],
            "buyer_sc_account_address": self.user2["address"],
            "st_value": 1000,
            "sc_value": 2000,
            "memo": "Test Trade",
        }
        assert wst_tx.tx_sender == self.relayer["address"]
        assert wst_tx.authorizer == self.user1["address"]
        assert wst_tx.authorization == {
            "nonce": nonce.hex(),
            "v": signature.v,
            "r": signature.r.to_bytes(32).hex(),
            "s": signature.s.to_bytes(32).hex(),
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Missing required fields in request body
    async def test_error_1(self, async_client):
        # Send request
        resp = await async_client.post(
            self.api_url.format(ibet_wst_address=self.ibet_wst_address), json={}
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "seller_st_account_address"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "buyer_st_account_address"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "sc_token_address"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "seller_sc_account_address"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "buyer_sc_account_address"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "st_value"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "sc_value"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "memo"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "authorizer"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "authorization"],
                    "msg": "Field required",
                    "input": {},
                },
            ],
        }
