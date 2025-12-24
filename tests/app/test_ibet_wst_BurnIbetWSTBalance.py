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
from unittest.mock import AsyncMock

import pytest
from eth_utils import to_checksum_address
from sqlalchemy import select

from app.model.db import (
    EthIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    Token,
    TokenType,
    TokenVersion,
)
from app.model.eth import IbetWST, IbetWSTDigestHelper
from app.utils.eth_contract_utils import EthWeb3
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestBurnIbetWSTBalance:
    # API endpoint
    api_url = "/ibet_wst/balances/{account_address}/{ibet_wst_address}/burn"

    relayer = default_eth_account("user1")
    issuer = default_eth_account("user2")
    user1 = default_eth_account("user3")

    ibet_wst_address = to_checksum_address("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd")

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Burn WST balance
    @mock.patch(
        "app.routers.misc.ibet_wst.IbetWST.balance_of", AsyncMock(return_value=1000)
    )
    @mock.patch(
        "app.routers.misc.ibet_wst.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    async def test_normal_1(self, async_db, async_client):
        # Prepare data: Token
        token = Token()
        token.token_address = self.ibet_wst_address
        token.issuer_address = self.issuer["address"]
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_09
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address
        async_db.add(token)
        await async_db.commit()

        # Generate nonce
        nonce = secrets.token_bytes(32)

        # Get domain separator
        token_st = IbetWST(self.ibet_wst_address)
        domain_separator = await token_st.domain_separator()

        # Generate digest
        digest = IbetWSTDigestHelper.generate_burn_digest(
            domain_separator=domain_separator,
            from_address=self.user1["address"],
            value=1000,
            nonce=nonce,
        )

        # Sign the digest from the authorizer's private key
        signature = EthWeb3.eth.account.unsafe_sign_hash(
            digest, bytes.fromhex(self.user1["private_key"])
        )

        # Send request
        resp = await async_client.post(
            self.api_url.format(
                account_address=self.user1["address"],
                ibet_wst_address=self.ibet_wst_address,
            ),
            json={
                "from_address": self.user1["address"],
                "value": 1000,
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
        assert wst_tx.tx_type == IbetWSTTxType.BURN
        assert wst_tx.version == IbetWSTVersion.V_1
        assert wst_tx.status == IbetWSTTxStatus.PENDING
        assert wst_tx.ibet_wst_address == self.ibet_wst_address
        assert wst_tx.tx_params == {
            "from_address": self.user1["address"],
            "value": 1000,
        }
        assert wst_tx.tx_sender == self.relayer["address"]
        assert wst_tx.authorizer == self.user1["address"]
        assert wst_tx.authorization == {
            "nonce": nonce.hex(),
            "v": signature.v,
            "r": signature.r.to_bytes(32).hex(),
            "s": signature.s.to_bytes(32).hex(),
        }
        assert wst_tx.client_ip == "127.0.0.1"

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Missing required fields in request body
    async def test_error_1(self, async_client):
        # Send request
        resp = await async_client.post(
            self.api_url.format(
                account_address=self.user1["address"],
                ibet_wst_address=self.ibet_wst_address,
            ),
            json={},
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "value"],
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

    # <Error_2>
    # Input value validations
    async def test_error_2(self, async_client):
        # Send request
        resp = await async_client.post(
            self.api_url.format(
                account_address=self.user1["address"],
                ibet_wst_address=self.ibet_wst_address,
            ),
            json={
                "value": 0,
                "authorizer": "invalid_address",
                "authorization": {
                    "nonce": "test_nonce",
                    "v": 27,
                    "r": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "s": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                },
            },
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "greater_than",
                    "loc": ["body", "value"],
                    "msg": "Input should be greater than 0",
                    "input": 0,
                    "ctx": {"gt": 0},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "authorizer"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_3>
    # IbetWST token not found
    async def test_error_3(self, async_db, async_client):
        # Generate nonce
        nonce = secrets.token_bytes(32)

        # Get domain separator
        token_st = IbetWST(self.ibet_wst_address)
        domain_separator = await token_st.domain_separator()

        # Generate digest
        digest = IbetWSTDigestHelper.generate_burn_digest(
            domain_separator=domain_separator,
            from_address=self.user1["address"],
            value=1000,
            nonce=nonce,
        )

        # Sign the digest from the authorizer's private key
        signature = EthWeb3.eth.account.unsafe_sign_hash(
            digest, bytes.fromhex(self.user1["private_key"])
        )

        # Send request
        resp = await async_client.post(
            self.api_url.format(
                account_address=self.user1["address"],
                ibet_wst_address=self.ibet_wst_address,
            ),
            json={
                "from_address": self.user1["address"],
                "value": 1000,
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
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "IbetWST token not found",
        }

    # <Error_4>
    # Insufficient WST balance
    @mock.patch(
        "app.routers.misc.ibet_wst.IbetWST.balance_of", AsyncMock(return_value=999)
    )
    async def test_error_4(self, async_db, async_client):
        # Prepare data: Token
        token = Token()
        token.token_address = self.ibet_wst_address
        token.issuer_address = self.issuer["address"]
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_09
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address
        async_db.add(token)
        await async_db.commit()

        # Generate nonce
        nonce = secrets.token_bytes(32)

        # Get domain separator
        token_st = IbetWST(self.ibet_wst_address)
        domain_separator = await token_st.domain_separator()

        # Generate digest
        digest = IbetWSTDigestHelper.generate_burn_digest(
            domain_separator=domain_separator,
            from_address=self.user1["address"],
            value=1000,
            nonce=nonce,
        )

        # Sign the digest from the authorizer's private key
        signature = EthWeb3.eth.account.unsafe_sign_hash(
            digest, bytes.fromhex(self.user1["private_key"])
        )

        # Send request
        resp = await async_client.post(
            self.api_url.format(
                account_address=self.user1["address"],
                ibet_wst_address=self.ibet_wst_address,
            ),
            json={
                "from_address": self.user1["address"],
                "value": 1000,
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
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 13, "title": "IbetWSTInsufficientBalanceError"},
            "detail": "",
        }
