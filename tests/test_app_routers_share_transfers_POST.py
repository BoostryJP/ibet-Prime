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
from app.model.utils import E2EEUtils
from app.exceptions import SendTransactionError
from tests.account_config import config_eth_account


class TestAppRoutersShareTransfersPOST:
    # target API endpoint
    test_url = "/share/transfers"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @mock.patch("app.model.blockchain.token.IbetShareContract.transfer")
    def test_normal_1(self, IbetShareContract_mock, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _transfer_from_account = config_eth_account("user2")
        _transfer_from = _transfer_from_account["address"]

        _transfer_to_account = config_eth_account("user3")
        _transfer_to = _transfer_to_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # mock
        IbetShareContract_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "transfer_from": _transfer_from,
            "transfer_to": _transfer_to,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address
            }
        )

        # assertion
        IbetShareContract_mock.assert_any_call(
            data=req_param,
            tx_from=_admin_address,
            private_key=ANY
        )

        assert resp.status_code == 200

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: token_address, transfer_from, transfer_to, amount
    def test_error_1(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _transfer_from = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _transfer_to = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address

        # request target API
        req_param = {
            "token_address": _token_address,
            "transfer_from": _transfer_from,
            "transfer_to": _transfer_to,
            "amount": -1  # negative value
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address
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
                }, {
                    "loc": ["body", "transfer_from"],
                    "msg": "transfer_from is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", "transfer_to"],
                    "msg": "transfer_to is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", "amount"],
                    "msg": "amount must be greater than 0",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2>
    # RequestValidationError: headers and body required
    def test_error_2(self, client, db):
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

    # <Error_3>
    # RequestValidationError: issuer-address
    def test_error_3(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _transfer_from_account = config_eth_account("user2")
        _transfer_from = _transfer_from_account["address"]

        _transfer_to_account = config_eth_account("user3")
        _transfer_to = _transfer_to_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "transfer_from": _transfer_from,
            "transfer_to": _transfer_to,
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
            "detail": [{
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }]
        }

    # <Error_4>
    # InvalidParameterError: issuer does not exist
    def test_error_4(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _transfer_from_account = config_eth_account("user2")
        _transfer_from = _transfer_from_account["address"]

        _transfer_to_account = config_eth_account("user3")
        _transfer_to = _transfer_to_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "transfer_from": _transfer_from,
            "transfer_to": _transfer_to,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address  # Non-existent issuer
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

    # <Error_5>
    # InvalidParameterError: token not found
    def test_error_5(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _transfer_from_account = config_eth_account("user2")
        _transfer_from = _transfer_from_account["address"]

        _transfer_to_account = config_eth_account("user3")
        _transfer_to = _transfer_to_account["address"]

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
            "transfer_from": _transfer_from,
            "transfer_to": _transfer_to,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address
            }
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
        }

    # <Error_6>
    # Send Transaction Error
    @mock.patch("app.model.blockchain.token.IbetShareContract.transfer",
                MagicMock(side_effect=SendTransactionError()))
    def test_error_6(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _transfer_from_account = config_eth_account("user2")
        _transfer_from = _transfer_from_account["address"]

        _transfer_to_account = config_eth_account("user3")
        _transfer_to = _transfer_to_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _admin_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        req_param = {
            "token_address": _token_address,
            "transfer_from": _transfer_from,
            "transfer_to": _transfer_to,
            "amount": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address
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
