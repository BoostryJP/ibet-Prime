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
from unittest import mock
from unittest.mock import ANY, MagicMock

import pytest

from app.exceptions import SendTransactionError
from app.model.db import Account, AuthToken, Token, TokenType, TokenVersion
from app.model.ibet.tx_params.ibet_straight_bond import RedeemParams
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import default_eth_account


class TestRedeemBond:
    # target API endpoint
    base_url = "/bond/tokens/{}/redeem"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Authorization by eoa-password
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.redeem")
    @pytest.mark.asyncio
    async def test_normal_1(
        self, IbetStraightBondContract_mock, async_client, async_db
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        IbetStraightBondContract_mock.assert_any_call(
            data=RedeemParams(**req_param), tx_from=_issuer_address, private_key=ANY
        )

        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_2>
    # Authorization by auth-token
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.redeem")
    @pytest.mark.asyncio
    async def test_normal_2(
        self, IbetStraightBondContract_mock, async_client, async_db
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = _issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        async_db.add(auth_token)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "auth-token": "test_auth_token",
            },
        )

        # assertion
        IbetStraightBondContract_mock.assert_any_call(
            data=RedeemParams(**req_param), tx_from=_issuer_address, private_key=ANY
        )

        assert resp.status_code == 200
        assert resp.json() is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: account_address
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {"account_address": "0x0", "amount": 10}

        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": "0x0",
                    "loc": ["body", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2>
    # RequestValidationError: amount(min)
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 0}

        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 1},
                    "input": 0,
                    "loc": ["body", "amount"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "greater_than_equal",
                }
            ],
        }

    # <Error_3>
    # RequestValidationError: amount(max)
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 1_000_000_000_001}

        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"le": 1000000000000},
                    "input": 1000000000001,
                    "loc": ["body", "amount"],
                    "msg": "Input should be less than or equal to 1000000000000",
                    "type": "less_than_equal",
                }
            ],
        }

    # <Error_4>
    # RequestValidationError: headers and body required
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        _token_address = "token_address_test"

        # request target API
        resp = await async_client.post(self.base_url.format(_token_address))

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_5>
    # RequestValidationError: issuer-address
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}

        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": "issuer-address"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "issuer-address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_6>
    # RequestValidationError: eoa-password(not decrypt)
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address, "eoa-password": "password"},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "password",
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                }
            ],
        }

    # <Error_7>
    # issuer does not exist
    @pytest.mark.asyncio
    async def test_error_7(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}

        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_8>
    # password mismatch
    @pytest.mark.asyncio
    async def test_error_8(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_9>
    # token not found
    @pytest.mark.asyncio
    async def test_error_9(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_10>
    # Processing Token
    @pytest.mark.asyncio
    async def test_error_10(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data¬
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.token_status = 0
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # <Error_11>
    # Send Transaction Error
    @mock.patch(
        "app.model.ibet.token.IbetStraightBondContract.redeem",
        MagicMock(side_effect=SendTransactionError()),
    )
    @pytest.mark.asyncio
    async def test_error_11(self, async_client, async_db):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data¬
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {"account_address": _issuer_address, "amount": 10}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }
