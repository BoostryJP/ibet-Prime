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

from app.exceptions import SendTransactionError
from app.model.blockchain.tx_params.ibet_straight_bond import ForcedTransferParams
from app.model.db import Account, AuthToken, Token, TokenType, TokenVersion
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestTransferBondTokenOwnership:
    # target API endpoint
    test_url = "/bond/transfers"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Authorization by eoa-password
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.forced_transfer")
    def test_normal_1(self, IbetStraightBondContract_mock, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        IbetStraightBondContract_mock.assert_any_call(
            data=ForcedTransferParams(
                **{
                    "from_address": _from_address,
                    "to_address": _to_address,
                    "amount": 10,
                }
            ),
            tx_from=_admin_address,
            private_key=ANY,
        )

        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_2>
    # Authorization by auth-token
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.forced_transfer")
    def test_normal_2(self, IbetStraightBondContract_mock, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = _admin_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        db.add(auth_token)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": _admin_address, "auth-token": "test_auth_token"},
        )

        # assertion
        IbetStraightBondContract_mock.assert_any_call(
            data=ForcedTransferParams(
                **{
                    "from_address": _from_address,
                    "to_address": _to_address,
                    "amount": 10,
                }
            ),
            tx_from=_admin_address,
            private_key=ANY,
        )

        assert resp.status_code == 200
        assert resp.json() is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: token_address, from_address, to_address, amount(min)
    def test_error_1(self, client, db):
        _from_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _to_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 0,
        }
        resp = client.post(
            self.test_url, json=req_param, headers={"issuer-address": "issuer-address"}
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
                    "loc": ["body", "from_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                },
                {
                    "ctx": {"error": {}},
                    "input": "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78",
                    "loc": ["body", "to_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                },
                {
                    "ctx": {"ge": 1},
                    "input": 0,
                    "loc": ["body", "amount"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "greater_than_equal",
                },
            ],
        }

    # <Error_2>
    # RequestValidationError: amount(max)
    def test_error_2(self, client, db):
        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]
        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]
        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 1_000_000_000_001,
        }
        resp = client.post(
            self.test_url, json=req_param, headers={"issuer-address": "issuer-address"}
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

    # <Error_3>
    # RequestValidationError: headers and body required
    def test_error_3(self, client, db):
        # request target API
        resp = client.post(self.test_url)

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

    # <Error_4>
    # RequestValidationError: issuer-address
    def test_error_4(self, client, db):
        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url, json=req_param, headers={"issuer-address": "issuer-address"}
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

    # <Error_5>
    # RequestValidationError: eoa-password(not decrypt)
    def test_error_5(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": _admin_address, "eoa-password": "password"},
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

    # <Error_6>
    # AuthorizationError: issuer does not exist
    def test_error_6(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,  # Non-existent issuer
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_7>
    # AuthorizationError: password mismatch
    def test_error_7(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
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

    # <Error_8>
    # InvalidParameterError: token not found
    def test_error_8(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
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

    # <Error_9>
    # InvalidParameterError: processing token
    def test_error_9(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
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

    # <Error_10>
    # Send Transaction Error
    @mock.patch(
        "app.model.blockchain.token.IbetStraightBondContract.forced_transfer",
        MagicMock(side_effect=SendTransactionError()),
    )
    def test_error_10(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _from_address_account = config_eth_account("user2")
        _from_address = _from_address_account["address"]

        _to_address_account = config_eth_account("user3")
        _to_address = _to_address_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }
