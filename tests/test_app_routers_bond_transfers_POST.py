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

from app.model.db import (
    Account,
    AuthToken,
    Token,
    TokenType
)
from app.utils.e2ee_utils import E2EEUtils
from app.exceptions import SendTransactionError
from tests.account_config import config_eth_account


class TestAppRoutersBondTransfersPOST:
    # target API endpoint
    test_url = "/bond/transfers"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Authorization by eoa-password
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.transfer")
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
        db.add(token)

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        IbetStraightBondContract_mock.assert_any_call(
            data=req_param,
            tx_from=_admin_address,
            private_key=ANY
        )

        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_2>
    # Authorization by auth-token
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.transfer")
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
        db.add(token)

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "auth-token": "test_auth_token"
            }
        )

        # assertion
        IbetStraightBondContract_mock.assert_any_call(
            data=req_param,
            tx_from=_admin_address,
            private_key=ANY
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
            "amount": 0
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": "issuer-address"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "token_address"],
                    "msg": "token_address is not a valid address",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "from_address"],
                    "msg": "from_address is not a valid address",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "to_address"],
                    "msg": "to_address is not a valid address",
                    "type": "value_error"
                },
                {
                    "ctx": {
                        "limit_value": 1
                    },
                    "loc": [
                        "body",
                        "amount"
                    ],
                    "msg": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                },
            ]
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
            "amount": 1_000_000_000_001
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": "issuer-address"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "ctx": {
                        "limit_value": 1_000_000_000_000
                    },
                    "loc": [
                        "body",
                        "amount"
                    ],
                    "msg": "ensure this value is less than or equal to 1000000000000",
                    "type": "value_error.number.not_le"
                },
            ]
        }

    # <Error_3>
    # RequestValidationError: headers and body required
    def test_error_3(self, client, db):
        # request target API
        resp = client.post(
            self.test_url
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_4>
    # RequestValidationError: issuer-address
    def test_normal_4(self, client, db):
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
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": "issuer-address"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_5>
    # RequestValidationError: eoa-password(not decrypt)
    def test_normal_5(self, client, db):
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
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": "password"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["header", "eoa-password"],
                "msg": "eoa-password is not a Base64-encoded encrypted data",
                "type": "value_error"
            }]
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
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,  # Non-existent issuer
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
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

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password_test")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
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

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "token not found"
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
        db.add(token)

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "this token is temporarily unavailable"
        }

    # <Error_10>
    # Send Transaction Error
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.transfer",
                MagicMock(side_effect=SendTransactionError()))
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
        db.add(token)

        # request target API
        req_param = {
            "token_address": _token_address,
            "from_address": _from_address,
            "to_address": _to_address,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 2,
                "title": "SendTransactionError"
            },
            "detail": "failed to send transaction"
        }
