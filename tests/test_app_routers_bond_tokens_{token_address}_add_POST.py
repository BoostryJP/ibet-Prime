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
from unittest.mock import ANY, MagicMock

from app.model.db import Account, Token, TokenType
from app.model.schema.utils import SecureValueUtils
from app.exceptions import SendTransactionError
from tests.account_config import config_eth_account


class TestAppRoutersBondTokensTokenAddressAddPOST:
    # target API endpoint
    base_url = "/bond/tokens/{}/add"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.add_supply")
    def test_normal_1(self, IbetStraightBondContract_mock, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {
            "account_address": _issuer_address,
            "amount": 10
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "password": SecureValueUtils.encrypt("password")
            }
        )

        # assertion
        IbetStraightBondContract_mock.assert_any_call(
            contract_address=_token_address,
            data=req_param,
            tx_from=_issuer_address,
            private_key=ANY
        )

        assert resp.status_code == 200

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: account_address
    def test_error_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        req_param = {
            "account_address": "0x0",
            "amount": 10
        }

        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "password": SecureValueUtils.encrypt("password")
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
                    "loc": [
                        "body",
                        "account_address"
                    ],
                    "msg": "account_address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2>
    # RequestValidationError: amount
    def test_error_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        req_param = {
            "account_address": _issuer_address,
            "amount": -1
        }

        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "password": SecureValueUtils.encrypt("password")
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
                    "loc": [
                        "body",
                        "amount"
                    ],
                    "msg": "amount must be greater than 0",
                    "type": "value_error"
                }
            ]
        }

    # <Error_3>
    # RequestValidationError: headers and body required
    def test_error_3(self, client, db):
        _token_address = "token_address_test"

        # request target API
        resp = client.post(
            self.base_url.format(_token_address)
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
                    "loc": ["header", "password"],
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
    # RequestValidationError: issuer-address, password
    def test_error_4(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        req_param = {
            "account_address": _issuer_address,
            "amount": 10
        }

        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": "issuer-address",
                "password": "password"
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
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }, {
                "loc": ["header", "password"],
                "msg": "password is not a Base64-decoded encrypted data",
                "type": "value_error"
            }]
        }

    # <Error_5>
    # issuer does not exist
    def test_error_5(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        req_param = {
            "account_address": _issuer_address,
            "amount": 10
        }

        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "password": SecureValueUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1, 
                "title": "InvalidParameterError"
            }, 
            "detail": "issuer does not exist"
        }

    # <Error_6>
    # password is mismatch
    def test_error_6(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        req_param = {
            "account_address": _issuer_address,
            "amount": 10
        }

        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "password": SecureValueUtils.encrypt("passwordtest")
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "password is mismatch"
        }

    # <Error_7>
    # token not found
    def test_error_7(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        db.add(account)

        # request target API
        req_param = {
            "account_address": _issuer_address,
            "amount": 10
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "password": SecureValueUtils.encrypt("password")
            }
        )

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
        }

    # <Error_8>
    # Send Transaction Error
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.add_supply",
                MagicMock(side_effect=SendTransactionError()))
    def test_error_8(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        req_param = {
            "account_address": _issuer_address,
            "amount": 10
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "password": SecureValueUtils.encrypt("password")
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
