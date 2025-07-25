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
import json
from unittest import mock
from unittest.mock import ANY, MagicMock

import pytest

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import Account, AuthToken, Token, TokenType, TokenVersion
from app.model.ibet.tx_params.ibet_security_token import ForceUnlockParams
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import default_eth_account


class TestForceUnlock:
    # target API endpoint
    test_url = "/positions/{account_address}/force_unlock"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Authorization by eoa-password
    # message is not set
    @mock.patch("app.model.ibet.token.IbetSecurityTokenInterface.force_unlock")
    @pytest.mark.asyncio
    async def test_normal_1_1(
        self, IbetSecurityTokenInterface_mock, async_client, async_db
    ):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # mock
        IbetSecurityTokenInterface_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        IbetSecurityTokenInterface_mock.assert_any_call(
            tx_params=ForceUnlockParams(
                **{
                    "lock_address": _lock_address,
                    "account_address": account_address,
                    "recipient_address": _recipient_address,
                    "value": 10,
                    "data": json.dumps(
                        {"message": "force_unlock"}, separators=(",", ":")
                    ),
                }
            ),
            tx_sender=_admin_address,
            tx_sender_key=ANY,
        )

        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_1_2>
    # Authorization by eoa-password
    # -message is set
    @mock.patch("app.model.ibet.token.IbetSecurityTokenInterface.force_unlock")
    @pytest.mark.asyncio
    async def test_normal_1_2(
        self, IbetSecurityTokenInterface_mock, async_client, async_db
    ):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # mock
        IbetSecurityTokenInterface_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "message": "garnishment",
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        IbetSecurityTokenInterface_mock.assert_any_call(
            tx_params=ForceUnlockParams(
                **{
                    "lock_address": _lock_address,
                    "account_address": account_address,
                    "recipient_address": _recipient_address,
                    "value": 10,
                    "data": json.dumps(
                        {"message": "garnishment"}, separators=(",", ":")
                    ),
                }
            ),
            tx_sender=_admin_address,
            tx_sender_key=ANY,
        )

        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_2>
    # Authorization by auth-token
    @mock.patch("app.model.ibet.token.IbetSecurityTokenInterface.force_unlock")
    @pytest.mark.asyncio
    async def test_normal_2(
        self, IbetSecurityTokenInterface_mock, async_client, async_db
    ):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = _admin_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        async_db.add(auth_token)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # mock
        IbetSecurityTokenInterface_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={"issuer-address": _admin_address, "auth-token": "test_auth_token"},
        )

        # assertion
        IbetSecurityTokenInterface_mock.assert_any_call(
            tx_params=ForceUnlockParams(
                **{
                    "lock_address": _lock_address,
                    "account_address": account_address,
                    "recipient_address": _recipient_address,
                    "value": 10,
                    "data": json.dumps(
                        {"message": "force_unlock"}, separators=(",", ":")
                    ),
                }
            ),
            tx_sender=_admin_address,
            tx_sender_key=ANY,
        )

        assert resp.status_code == 200
        assert resp.json() is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError
    # Required fields are not set
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={"issuer-address": "issuer-address"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": {},
                    "loc": ["body", "token_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["body", "lock_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["body", "recipient_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["body", "value"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_1_2>
    # RequestValidationError
    # - address is invalid
    # - value is not greater than 0
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _lock_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _recipient_address = (
            "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        )

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 0,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={"issuer-address": "issuer-address"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78",
                    "loc": ["body", "token_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                },
                {
                    "ctx": {"error": {}},
                    "input": "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78",
                    "loc": ["body", "lock_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                },
                {
                    "ctx": {"error": {}},
                    "input": "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78",
                    "loc": ["body", "recipient_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                },
                {
                    "ctx": {"gt": 0},
                    "input": 0,
                    "loc": ["body", "value"],
                    "msg": "Input should be greater than 0",
                    "type": "greater_than",
                },
            ],
        }

    # <Error_1_3>
    # RequestValidationError
    # Header and body are required
    @pytest.mark.asyncio
    async def test_error_1_3(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"
        # request target API
        resp = await async_client.post(
            self.test_url.format(account_address=account_address)
        )

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

    # <Error_1_4>
    # RequestValidationError
    # issuer-address is not a valid address
    @pytest.mark.asyncio
    async def test_error_1_4(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={"issuer-address": "issuer-address"},  # dummy address
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

    # <Error_1_5>
    # RequestValidationError
    # eoa-password is not a Base64-encoded encrypted data
    @pytest.mark.asyncio
    async def test_error_1_5(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": "password",  # not encrypted
            },
        )

        # assertion
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

    # <Error_1_6>
    # RequestValidationError
    # Invalid message
    @pytest.mark.asyncio
    async def test_error_1_6(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)
        await async_db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "message": "invalid_message",
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["body", "message"],
                    "msg": "Input should be 'garnishment', "
                    "'force_unlock' or 'ibet_wst_bridge'",
                    "input": "invalid_message",
                    "ctx": {
                        "expected": "'garnishment', 'force_unlock' or 'ibet_wst_bridge'"
                    },
                }
            ],
        }

    # <Error_2_1>
    # AuthorizationError
    # Issuer does not exist
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_2_2>
    # AuthorizationError
    # Password mismatch
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_3_1>
    # InvalidParameterError
    # account_address is not a valid address
    @pytest.mark.asyncio
    async def test_error_3_1(self, async_client, async_db):
        account_address = "invalid_address"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "account_address is not a valid address",
        }

    # <Error_3_2>
    # InvalidParameterError
    # token not found
    @pytest.mark.asyncio
    async def test_error_3_2(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "token not found",
        }

    # <Error_3_3>
    # InvalidParameterError
    # token is temporarily unavailable
    @pytest.mark.asyncio
    async def test_error_3_3(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = {}
        token.token_status = 0
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # <Error_4>
    # ContractRevertError
    @mock.patch(
        "app.model.ibet.token.IbetSecurityTokenInterface.force_unlock",
        MagicMock(side_effect=ContractRevertError(code_msg="111201")),
    )
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 111201, "title": "ContractRevertError"},
            "detail": "Unlock amount is greater than locked amount.",
        }

    # <Error_5>
    # SendTransactionError
    @mock.patch(
        "app.model.ibet.token.IbetSecurityTokenInterface.force_unlock",
        MagicMock(side_effect=SendTransactionError()),
    )
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = default_eth_account("user2")["address"]
        _recipient_address = default_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "recipient_address": _recipient_address,
            "value": 10,
        }
        resp = await async_client.post(
            self.test_url.format(account_address=account_address),
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }
