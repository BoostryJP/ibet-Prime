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

import pytest
from eth_utils import to_checksum_address
from sqlalchemy import select

from app.model.db import (
    Account,
    EthIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import default_eth_account


@pytest.mark.asyncio
class TestAddIbetWSTWhitelist:
    # API endpoint
    api_url = "/tokens/{token_address}/ibet_wst/whitelists/add"

    issuer = default_eth_account("user1")
    user1 = default_eth_account("user2")
    relayer = default_eth_account("user3")

    token_address = to_checksum_address("0x1234567890abcdef1234567890abcdef12345678")
    ibet_wst_address = to_checksum_address("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd")

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Add account to whitelist
    @mock.patch(
        "app.routers.issuer.token_common.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    async def test_normal_1(self, async_db, async_client):
        # Prepare data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = self.issuer["address"]
        token.token_address = self.token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address
        async_db.add(token)

        await async_db.commit()

        # Send request
        resp = await async_client.post(
            self.api_url.format(token_address=self.token_address),
            json={"account_address": self.user1["address"]},
            headers={
                "issuer-address": self.issuer["address"],
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Check response status code and content
        assert resp.status_code == 200
        assert resp.json() == {"tx_id": mock.ANY}

        # Check transaction creation
        wst_tx = (await async_db.scalars(select(EthIbetWSTTx).limit(1))).first()
        assert wst_tx.tx_type == IbetWSTTxType.ADD_WHITELIST
        assert wst_tx.version == IbetWSTVersion.V_1
        assert wst_tx.status == IbetWSTTxStatus.PENDING
        assert wst_tx.ibet_wst_address == self.ibet_wst_address
        assert wst_tx.tx_params == {
            "account_address": self.user1["address"],
        }
        assert wst_tx.tx_sender == self.relayer["address"]
        assert wst_tx.authorizer == self.issuer["address"]
        assert wst_tx.authorization == {
            "nonce": mock.ANY,
            "v": mock.ANY,
            "r": mock.ANY,
            "s": mock.ANY,
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Invalid account address
    async def test_error_1(self, async_db, async_client):
        # Send request with invalid account address
        resp = await async_client.post(
            self.api_url.format(token_address=self.token_address),
            json={"account_address": "invalid_account_address"},
            headers={
                "issuer-address": self.issuer["address"],
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_account_address",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_2>
    # Invalid issuer address and password
    async def test_error_2(self, async_db, async_client):
        # Send request
        resp = await async_client.post(
            self.api_url.format(token_address=self.token_address),
            json={"account_address": self.user1["address"]},
            headers={
                "issuer-address": "invalid_issuer_address",
                "eoa-password": "invalid_password",
            },
        )

        # Check response status code
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "msg": "issuer-address is not a valid address",
                    "loc": ["header", "issuer-address"],
                    "input": "invalid_issuer_address",
                    "type": "value_error",
                },
                {
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "loc": ["header", "eoa-password"],
                    "input": "invalid_password",
                    "type": "value_error",
                },
            ],
        }

    # <Error_3>

    async def test_error_3(self, async_db, async_client):
        # Prepare data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = self.issuer["address"]
        token.token_address = self.token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address
        async_db.add(token)

        await async_db.commit()

        # Send request
        resp = await async_client.post(
            self.api_url.format(token_address=self.token_address),
            json={"account_address": self.user1["address"]},
            headers={
                "issuer-address": self.issuer["address"],
                "eoa-password": E2EEUtils.encrypt("invalid_password"),
            },
        )

        # Check response status code
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_4>
    # Token not found
    async def test_error_4(self, async_db, async_client):
        # Prepare data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Send request
        resp = await async_client.post(
            self.api_url.format(token_address=self.token_address),
            json={"account_address": self.user1["address"]},
            headers={
                "issuer-address": self.issuer["address"],
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Check response status code
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "Token not found",
        }
