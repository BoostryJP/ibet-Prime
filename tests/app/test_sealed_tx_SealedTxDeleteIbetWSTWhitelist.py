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
from eth_utils.address import to_checksum_address
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.db import (
    Account,
    AccountRsaStatus,
    AvaIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    IbetWSTWhitelistKYCDelegatedEoa,
    Token,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import default_eth_account
from tests.app.utils.generate_signature import generate_sealed_tx_signature


@pytest.mark.asyncio
class TestSealedTxDeleteIbetWSTWhitelist:
    api_url = "/sealed_tx/ibet_wst/whitelists/delete"

    issuer = default_eth_account("user1")
    delegate = default_eth_account("user2")
    user1 = default_eth_account("user3")
    relayer = default_eth_account("user4")

    token_address = to_checksum_address("0x1234567890abcdef1234567890abcdef12345678")
    ibet_wst_address = to_checksum_address("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd")

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Delete account from IbetWST whitelist by sealed tx
    # - blockchain_platform = "avalanche"
    @mock.patch(
        "app.routers.misc.sealed_tx.AVA_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    async def test_normal_1(self, async_db: AsyncSession, async_client: AsyncClient):
        # Prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        delegate = IbetWSTWhitelistKYCDelegatedEoa()
        delegate.key_manager = self.issuer["address"]
        delegate.account_address = self.delegate["address"]
        async_db.add(delegate)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = self.issuer["address"]
        token.token_address = self.token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        token.set_ibet_wst_deployed("avalanche", True)
        token.set_ibet_wst_address("avalanche", self.ibet_wst_address)
        async_db.add(token)

        await async_db.commit()

        # Derive a signature
        params = {
            "token_address": self.token_address,
            "st_account_address": self.user1["address"],
            "blockchain_platform": "avalanche",
        }
        sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.api_url,
            private_key=self.delegate["private_key"],
            json=params,
        )

        # Call API
        resp = await async_client.post(
            self.api_url,
            json=params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {"tx_id": mock.ANY}

        wst_tx = (await async_db.scalars(select(AvaIbetWSTTx).limit(1))).first()
        assert wst_tx is not None
        assert wst_tx.tx_type == IbetWSTTxType.DELETE_WHITELIST
        assert wst_tx.version == IbetWSTVersion.V_1
        assert wst_tx.status == IbetWSTTxStatus.PENDING
        assert wst_tx.ibet_wst_address == self.ibet_wst_address
        assert wst_tx.tx_params == {"st_account": self.user1["address"]}
        assert wst_tx.tx_sender == self.relayer["address"]
        assert wst_tx.authorizer == self.issuer["address"]
        assert wst_tx.authorization == {
            "nonce": mock.ANY,
            "v": mock.ANY,
            "r": mock.ANY,
            "s": mock.ANY,
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # - Missing X-SealedTx-Signature header
    async def test_error_1(self, async_db: AsyncSession, async_client: AsyncClient):
        # Call API
        resp = await async_client.post(
            self.api_url,
            json={
                "token_address": self.token_address,
                "st_account_address": self.user1["address"],
            },
            headers={
                "Content-Type": "application/json",
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "X-SealedTx-Signature"],
                    "msg": "Field required",
                    "input": None,
                }
            ],
        }

    # <Error_2>
    # RequestValidationError
    # - Missing required field: token_address
    async def test_error_2(self, async_db: AsyncSession, async_client: AsyncClient):
        # Derive a signature
        params = {
            "st_account_address": self.user1["address"],
        }
        sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.api_url,
            private_key=self.delegate["private_key"],
            json=params,
        )

        # Call API
        resp = await async_client.post(
            self.api_url,
            json=params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "token_address"],
                    "msg": "Field required",
                    "input": {
                        "st_account_address": self.user1["address"],
                    },
                }
            ],
        }

    # <Error_3>
    # Token not found
    async def test_error_3(self, async_db: AsyncSession, async_client: AsyncClient):
        # Derive a signature
        params = {
            "token_address": self.token_address,
            "st_account_address": self.user1["address"],
        }
        sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.api_url,
            private_key=self.delegate["private_key"],
            json=params,
        )

        # Call API
        resp = await async_client.post(
            self.api_url,
            json=params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "Token not found",
        }

    # <Error_4>
    # InvalidParameterError
    # - Token is temporarily unavailable while token status is pending
    async def test_error_4(self, async_db: AsyncSession, async_client: AsyncClient):
        # Prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        delegate = IbetWSTWhitelistKYCDelegatedEoa()
        delegate.key_manager = self.issuer["address"]
        delegate.account_address = self.delegate["address"]
        async_db.add(delegate)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = self.issuer["address"]
        token.token_address = self.token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        token.token_status = TokenStatus.PENDING
        token.set_ibet_wst_deployed("ethereum", True)
        token.set_ibet_wst_address("ethereum", self.ibet_wst_address)
        async_db.add(token)
        await async_db.commit()

        # Derive a signature
        params = {
            "token_address": self.token_address,
            "st_account_address": self.user1["address"],
        }
        sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.api_url,
            private_key=self.delegate["private_key"],
            json=params,
        )

        # Call API
        resp = await async_client.post(
            self.api_url,
            json=params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "This token is temporarily unavailable",
        }

    # <Error_5>
    # InvalidParameterError
    # - delegated EOA is not registered for IbetWST whitelist KYC operations
    async def test_error_5(self, async_db: AsyncSession, async_client: AsyncClient):
        # Prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = self.issuer["address"]
        token.token_address = self.token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        token.set_ibet_wst_deployed("ethereum", True)
        token.set_ibet_wst_address("ethereum", self.ibet_wst_address)
        async_db.add(token)
        await async_db.commit()

        # Derive a signature
        params = {
            "token_address": self.token_address,
            "st_account_address": self.user1["address"],
        }
        sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.api_url,
            private_key=self.delegate["private_key"],
            json=params,
        )

        # Call API
        resp = await async_client.post(
            self.api_url,
            json=params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "delegated EOA is not authorized",
        }

    # <Error_6>
    # Issuer account not found
    async def test_error_6(self, async_db: AsyncSession, async_client: AsyncClient):
        # Prepare data
        delegate = IbetWSTWhitelistKYCDelegatedEoa()
        delegate.key_manager = self.issuer["address"]
        delegate.account_address = self.delegate["address"]
        async_db.add(delegate)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = self.issuer["address"]
        token.token_address = self.token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        token.set_ibet_wst_deployed("ethereum", True)
        token.set_ibet_wst_address("ethereum", self.ibet_wst_address)
        async_db.add(token)
        await async_db.commit()

        # Derive a signature
        params = {
            "token_address": self.token_address,
            "st_account_address": self.user1["address"],
        }
        sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.api_url,
            private_key=self.delegate["private_key"],
            json=params,
        )

        # Call API
        resp = await async_client.post(
            self.api_url,
            json=params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "Issuer account not found",
        }
