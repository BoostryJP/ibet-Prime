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

from sqlalchemy import select

from app.model.db import Account, Token, TokenHolderExtraInfo, TokenType, TokenVersion
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestRegisterBondTokenHolderExtraInfo:
    # target API endpoint
    test_url = "/bond/tokens/{}/holders/{}/holder_extra_info"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Register token holder's extra information
    def test_normal_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        extra_info = db.scalars(select(TokenHolderExtraInfo).limit(1)).first()
        assert extra_info.json() == {
            "token_address": _token_address,
            "account_address": _test_account_address,
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }

    # <Normal_2>
    # Optional input parameters
    def test_normal_2(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = {}
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        extra_info = db.scalars(select(TokenHolderExtraInfo).limit(1)).first()
        assert extra_info.json() == {
            "token_address": _token_address,
            "account_address": _test_account_address,
            "external_id_1_type": None,
            "external_id_1": None,
            "external_id_2_type": None,
            "external_id_2": None,
            "external_id_3_type": None,
            "external_id_3": None,
        }

    # <Normal_3>
    # Overwrite the already registered data
    def test_normal_3(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        extra_info_bf = TokenHolderExtraInfo()
        extra_info_bf.token_address = _token_address
        extra_info_bf.account_address = _test_account_address
        extra_info_bf.external_id_1_type = "test_id_type_1_bf"
        extra_info_bf.external_id_1 = "test_id_1_bf"
        extra_info_bf.external_id_2_type = "test_id_type_2_bf"
        extra_info_bf.external_id_2 = "test_id_2_bf"
        extra_info_bf.external_id_3_type = "test_id_type_3_bf"
        extra_info_bf.external_id_3 = "test_id_3_bf"
        db.add(extra_info_bf)
        db.commit()

        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        extra_info = db.scalars(select(TokenHolderExtraInfo).limit(1)).first()
        assert extra_info.json() == {
            "token_address": _token_address,
            "account_address": _test_account_address,
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # - headers and body required
    def test_error_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "input": None,
                },
                {
                    "type": "missing",
                    "loc": ["body"],
                    "msg": "Field required",
                    "input": None,
                },
            ],
        }

    # <Error_2>
    # RequestValidationError
    # - invalid issuer_address format
    def test_error_2(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": "test_issuer_address",  # invalid address
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "msg": "issuer-address is not a valid address",
                    "loc": ["header", "issuer-address"],
                    "input": "test_issuer_address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_3>
    # RequestValidationError
    # - eoa-password not encrypted
    def test_error_3(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": "password",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "loc": ["header", "eoa-password"],
                    "input": "password",
                    "type": "value_error",
                }
            ],
        }

    # <Error_4>
    # RequestValidationError
    # - external_id: string_too_long
    def test_error_4(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "external_id_1_type": "a" * 51,
            "external_id_1": "a" * 51,
            "external_id_2_type": "a" * 51,
            "external_id_2": "a" * 51,
            "external_id_3_type": "a" * 51,
            "external_id_3": "a" * 51,
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
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
                    "type": "string_too_long",
                    "loc": ["body", "external_id_1_type"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_1"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_2_type"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_2"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_3_type"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_3"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
            ],
        }

    # <Error_5_1>
    # AuthorizationError
    # - issuer does not exist
    def test_error_5_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_5_2>
    # AuthorizationError
    # - password mismatch
    def test_error_5_2(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("invalid_password"),
            },
        )

        # Assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_6_1>
    # Token not found
    def test_error_6_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)
        db.commit()

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_6_2>
    # Token is temporarily unavailable
    def test_error_6_2(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        token.token_status = 0
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
