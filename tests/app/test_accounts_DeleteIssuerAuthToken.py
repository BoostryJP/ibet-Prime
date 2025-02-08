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

import hashlib
from datetime import datetime

import pytest
from sqlalchemy import select

from app.model.db import Account, AuthToken
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestDeleteIssuerAuthToken:
    # target API endpoint
    apiurl = "/accounts/{}/auth_token"

    eoa_password = "password"
    auth_token = "test_auth_token"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # Authorization by eoa_password
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        auth_token.usage_start = datetime(2022, 7, 15, 12, 34, 56)
        auth_token.valid_duration = 120
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.apiurl.format(test_account["address"]),
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        assert resp.status_code == 200

        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

    # Normal_2
    # Authorization by auth_token
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        auth_token.valid_duration = 0
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.apiurl.format(test_account["address"]),
            headers={"auth-token": self.auth_token},
        )

        # assertion
        assert resp.status_code == 200

        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # RequestValidationError
    # issuer-address is not a valid address
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        auth_token.usage_start = datetime(2022, 7, 15, 12, 34, 56)
        auth_token.valid_duration = 120
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.apiurl.format(test_account["address"][::-1]),  # invalid issue address
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": test_account["address"][::-1],
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is not None

    # Error_2
    # RequestValidationError
    # eoa-password is not a Base64-encoded encrypted data
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        auth_token.usage_start = datetime(2022, 7, 15, 12, 34, 56)
        auth_token.valid_duration = 120
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.apiurl.format(test_account["address"]),
            headers={"eoa-password": self.eoa_password},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": self.eoa_password,
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                }
            ],
        }

        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is not None

    # Error_3_1
    # AuthorizationError
    # eoa-password (or auth-token) not set
    @pytest.mark.asyncio
    async def test_error_3_1(self, async_client, async_db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        auth_token.usage_start = datetime(2022, 7, 15, 12, 34, 56)
        auth_token.valid_duration = 120
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.apiurl.format(test_account["address"]),
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is not None

    # Error_3_2
    # AuthorizationError
    # eoa-password (or auth-token) is not correct
    @pytest.mark.asyncio
    async def test_error_3_2(self, async_client, async_db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        auth_token.usage_start = datetime(2022, 7, 15, 12, 34, 56)
        auth_token.valid_duration = 120
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.apiurl.format(test_account["address"]),
            headers={
                "eoa-password": E2EEUtils.encrypt("incorrect_password")
            },  # incorrect password
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is not None

    # Error_4
    # NotFound
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.apiurl.format(test_account["address"]),
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "auth token does not exist",
        }
