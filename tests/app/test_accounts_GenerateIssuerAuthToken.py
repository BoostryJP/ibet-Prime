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
from tests.account_config import default_eth_account


class TestGenerateIssuerAuthToken:
    # target API endpoint
    apiurl = "/accounts/{}/auth_token"

    eoa_password = "password"
    auth_token = "test_auth_token"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # New token
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)
        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": 120},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token.issuer_address == test_account["address"]
        assert auth_token.usage_start == datetime(2022, 7, 15, 12, 34, 56)
        assert auth_token.valid_duration == 120

        assert resp.status_code == 200
        response = resp.json()
        assert (
            hashlib.sha256(response["auth_token"].encode()).hexdigest()
            == auth_token.auth_token
        )
        assert response["usage_start"] == "2022-07-15T21:34:56+09:00"
        assert response["valid_duration"] == 120

    # Normal_2
    # Update token
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = "hashed_token"
        auth_token.usage_start = datetime(
            2022, 7, 15, 12, 32, 55
        )  # 2022-07-15 12:34:56 - 121sec
        auth_token.valid_duration = 120
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": 120},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        auth_token: AuthToken = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token.issuer_address == test_account["address"]
        assert auth_token.usage_start == datetime(2022, 7, 15, 12, 34, 56)
        assert auth_token.valid_duration == 120

        assert resp.status_code == 200
        response = resp.json()
        assert (
            hashlib.sha256(response["auth_token"].encode()).hexdigest()
            == auth_token.auth_token
        )
        assert response["usage_start"] == "2022-07-15T21:34:56+09:00"
        assert response["valid_duration"] == 120

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1_1
    # RequestValidationError
    # [header] missing
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]), json={"valid_duration": 120}
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "eoa-password"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
        }

    # Error_1_2
    # RequestValidationError
    # [body] missing
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # Error_2
    # RequestValidationError
    # issuer-address is not a valid address
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"][::-1]),  # invalid address
            json={"valid_duration": 120},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "649F59B9E7FcB7b4A8bDfC7D8a64cc2d228fe6Dex0",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # Error_3
    # RequestValidationError
    # [header] eoa-password is not a Base64-encoded encrypted data
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": 120},
            headers={
                "eoa-password": "not_encrypted_password"
            },  # not encrypted password
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "not_encrypted_password",
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                }
            ],
        }

    # Error_4_1
    # RequestValidationError
    # [body] type error
    @pytest.mark.asyncio
    async def test_error_4_1(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": "invalid_duration"},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "invalid_duration",
                    "loc": ["body", "valid_duration"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                }
            ],
        }

    # Error_4_2
    # RequestValidationError
    # [body] valid_duration is greater than or equal to 0
    @pytest.mark.asyncio
    async def test_error_4_2(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": -1},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "valid_duration"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                }
            ],
        }

    # Error_4_3
    # RequestValidationError
    # [body] valid_duration is less than or equal to 259200
    @pytest.mark.asyncio
    async def test_error_4_3(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": 259201},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"le": 259200},
                    "input": 259201,
                    "loc": ["body", "valid_duration"],
                    "msg": "Input should be less than or equal to 259200",
                    "type": "less_than_equal",
                }
            ],
        }

    # Error_5
    # AuthorizationError
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": 120},
            headers={
                "eoa-password": E2EEUtils.encrypt("mismatch_password")
            },  # incorrect password
        )

        # assertion
        auth_token = (
            await async_db.scalars(
                select(AuthToken)
                .where(AuthToken.issuer_address == test_account["address"])
                .limit(1)
            )
        ).first()
        assert auth_token is None

        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # Error_6_1
    # AuthTokenAlreadyExistsError
    # valid_duration = 0
    @pytest.mark.asyncio
    async def test_error_6_1(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = "hashed_token"
        auth_token.usage_start = datetime(2022, 7, 15, 12, 32, 55)
        auth_token.valid_duration = 0  # endless
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": 120},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 3, "title": "AuthTokenAlreadyExistsError"}
        }

    # Error_6_2
    # AuthTokenAlreadyExistsError
    # valid token already exists
    @pytest.mark.asyncio
    async def test_error_6_2(self, async_client, async_db, freezer):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = "hashed_token"
        auth_token.usage_start = datetime(
            2022, 7, 15, 12, 32, 56
        )  # 2022-07-15 12:34:56 - 120sec
        auth_token.valid_duration = 120
        async_db.add(auth_token)

        await async_db.commit()

        # request target api
        freezer.move_to("2022-07-15 12:34:56")
        resp = await async_client.post(
            self.apiurl.format(test_account["address"]),
            json={"valid_duration": 120},
            headers={"eoa-password": E2EEUtils.encrypt(self.eoa_password)},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 3, "title": "AuthTokenAlreadyExistsError"}
        }
