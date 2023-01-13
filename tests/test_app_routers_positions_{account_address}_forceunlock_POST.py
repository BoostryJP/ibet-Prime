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
from app.exceptions import (
    SendTransactionError,
    ContractRevertError
)
from tests.account_config import config_eth_account


class TestAppRoutersForceUnlockPOST:

    # target API endpoint
    test_url = "/positions/{account_address}/force_unlock"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Authorization by eoa-password
    @mock.patch("app.model.blockchain.token.IbetSecurityTokenInterface.force_unlock")
    def test_normal_1(self, IbetSecurityTokenInterface_mock, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

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
        IbetSecurityTokenInterface_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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
        IbetSecurityTokenInterface_mock.assert_any_call(
            data={
                "lock_address": _lock_address,
                "account_address": _admin_address,
                "recipient_address": _recipient_address,
                "value": 10,
                "data": ""
            },
            tx_from=_admin_address,
            private_key=ANY
        )

        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_2>
    # Authorization by auth-token
    @mock.patch("app.model.blockchain.token.IbetSecurityTokenInterface.force_unlock")
    def test_normal_2(self, IbetSecurityTokenInterface_mock, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

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
        IbetSecurityTokenInterface_mock.side_effect = [None]

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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
        IbetSecurityTokenInterface_mock.assert_any_call(
            data={
                "lock_address": _lock_address,
                "account_address": _admin_address,
                "recipient_address": _recipient_address,
                "value": 10,
                "data": ""
            },
            tx_from=_admin_address,
            private_key=ANY
        )

        assert resp.status_code == 200
        assert resp.json() is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError
    # Required fields are not set
    def test_error_1(self, client, db):
        # request target API
        req_param = {}
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
            'meta': {
                'code': 1,
                'title': 'RequestValidationError'
            },
            'detail': [
                {
                    'loc': ['body', 'token_address'],
                    'msg': 'field required',
                    'type': 'value_error.missing'
                },
                {
                    'loc': ['body', 'lock_address'],
                    'msg': 'field required',
                    'type': 'value_error.missing'
                },
                {
                    'loc': ['body', 'account_address'],
                    'msg': 'field required',
                    'type': 'value_error.missing'
                },
                {
                    'loc': ['body', 'recipient_address'],
                    'msg': 'field required',
                    'type': 'value_error.missing'
                },
                {
                    'loc': ['body', 'value'],
                    'msg': 'field required',
                    'type': 'value_error.missing'
                }
            ]
        }

    # <Error_1_2>
    # RequestValidationError
    # - address is invalid
    # - value is not greater than 0
    def test_error_1_2(self, client, db):
        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _lock_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _admin_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        _recipient_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 0
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
            'meta': {
                'code': 1,
                'title': 'RequestValidationError'
            },
            'detail': [
                {
                    'loc': ['body', 'token_address'],
                    'msg': 'token_address is not a valid address',
                    'type': 'value_error'
                },
                {
                    'loc': ['body', 'lock_address'],
                    'msg': 'lock_address is not a valid address',
                    'type': 'value_error'
                },
                {
                    'loc': ['body', 'account_address'],
                    'msg': 'account_address is not a valid address',
                    'type': 'value_error'
                },
                {
                    'loc': ['body', 'recipient_address'],
                    'msg': 'recipient_address is not a valid address',
                    'type': 'value_error'
                },
                {
                    'loc': ['body', 'value'],
                    'msg': 'ensure this value is greater than 0',
                    'type': 'value_error.number.not_gt',
                    'ctx': {'limit_value': 0}
                }
            ]
        }

    # <Error_3>
    # RequestValidationError
    # Header and body are required
    def test_error_1_3(self, client, db):
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
    # RequestValidationError
    # issuer-address is not a valid address
    def test_error_1_4(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": "issuer-address"  # dummy address
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

    # <Error_1_5>
    # RequestValidationError
    # eoa-password is not a Base64-encoded encrypted data
    def test_error_1_5(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": _admin_address,
                "eoa-password": "password" # not encrypted
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

    # <Error_2_1>
    # AuthorizationError
    # Issuer does not exist
    def test_error_2_1(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "token_address": _token_address,
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
        }

    # <Error_2_2>
    # AuthorizationError
    # Password mismatch
    def test_error_2_2(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

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
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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

    # <Error_3_1>
    # InvalidParameterError
    # token not found
    def test_error_3_1(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

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
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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

    # <Error_3_2>
    # InvalidParameterError
    # token is temporarily unavailable
    def test_error_3_2(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

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
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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

    # <Error_4>
    # ContractRevertError
    @mock.patch("app.model.blockchain.token.IbetSecurityTokenInterface.force_unlock",
                MagicMock(side_effect=ContractRevertError(code_msg="111201")))
    def test_error_4(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

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
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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
            'meta': {
                'code': 111201,
                'title': 'ContractRevertError'
            },
            'detail': 'Unlock amount is greater than locked amount.'
        }

    # <Error_5>
    # SendTransactionError
    @mock.patch("app.model.blockchain.token.IbetSecurityTokenInterface.force_unlock",
                MagicMock(side_effect=SendTransactionError()))
    def test_error_5(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        _lock_address = config_eth_account("user2")["address"]
        _recipient_address = config_eth_account("user3")["address"]

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
            "lock_address": _lock_address,
            "account_address": _admin_address,
            "recipient_address": _recipient_address,
            "value": 10
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