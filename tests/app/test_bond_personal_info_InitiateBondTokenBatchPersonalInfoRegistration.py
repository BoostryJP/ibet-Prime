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
from typing import Optional
from unittest.mock import ANY

from sqlalchemy import select

from app.model.db import (
    Account,
    AuthToken,
    BatchRegisterPersonalInfo,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestInitiateBondTokenBatchPersonalInfoRegistration:
    # target API endpoint
    test_url = "/bond/tokens/{}/personal_info/batch"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Authorization by eoa-password
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
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        personal_info = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        # request target API
        req_param = [personal_info for _ in range(0, 10)]
        resp = client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "batch_id": ANY,
            "status": BatchRegisterPersonalInfoUploadStatus.PENDING.value,
            "created": ANY,
        }

        _upload: Optional[BatchRegisterPersonalInfoUpload] = db.scalars(
            select(BatchRegisterPersonalInfoUpload).limit(1)
        ).first()
        assert _upload.status == BatchRegisterPersonalInfoUploadStatus.PENDING.value
        assert _upload.issuer_address == _issuer_address

        _register_list: list[BatchRegisterPersonalInfo] = db.scalars(
            select(BatchRegisterPersonalInfo)
        ).all()
        assert len(_register_list) == 10

    # <Normal_2>
    # Authorization by auth-token
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

        auth_token = AuthToken()
        auth_token.issuer_address = _issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        db.add(auth_token)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        personal_info = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        # request target API
        req_param = [personal_info for _ in range(0, 10)]
        resp = client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "auth-token": "test_auth_token",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "batch_id": ANY,
            "status": BatchRegisterPersonalInfoUploadStatus.PENDING.value,
            "created": ANY,
        }

        _upload: Optional[BatchRegisterPersonalInfoUpload] = db.scalars(
            select(BatchRegisterPersonalInfoUpload).limit(1)
        ).first()
        assert _upload.status == BatchRegisterPersonalInfoUploadStatus.PENDING.value
        assert _upload.issuer_address == _issuer_address

        _register_list: list[BatchRegisterPersonalInfo] = db.scalars(
            select(BatchRegisterPersonalInfo)
        ).all()
        assert len(_register_list) == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError
    # headers and body required
    def test_error_1_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        resp = client.post(self.test_url.format(_token_address))

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

    # <Error_1_2>
    # RequestValidationError
    # personal_info
    def test_error_1_2(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        personal_info = {
            "account_address": None,
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        # request target API
        req_param = [personal_info for _ in range(0, 10)]
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        details = []
        for i in range(0, 10):
            details.append(
                {
                    "loc": ["body", i, "account_address"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed",
                }
            )
            details.append(
                {
                    "loc": ["body", i, "key_manager"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed",
                }
            )
        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "string_type",
                    "loc": ["body", 0, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 1, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 2, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 3, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 4, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 5, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 6, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 7, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 8, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
                {
                    "type": "string_type",
                    "loc": ["body", 9, "key_manager"],
                    "msg": "Input should be a valid string",
                    "input": None,
                },
            ],
        }

    # <Error_1_3>
    # RequestValidationError
    # personal_info.account_address is invalid
    def test_error_1_3(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        personal_info = {
            "account_address": "test",
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        # request target API
        req_param = [personal_info for _ in range(0, 10)]
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
                    "type": "value_error",
                    "loc": ["body", 0, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 1, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 2, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 3, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 4, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 5, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 6, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 7, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 8, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", 9, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "test",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_1_4>
    # RequestValidationError
    # issuer_address
    def test_error_1_4(self, client, db):
        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = [
            {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
        ]
        resp = client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": "test_issuer_address",
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test_issuer_address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_1_5>
    # RequestValidationError
    # eoa-password not encrypted
    def test_error_1_5(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = [
            {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
        ]
        resp = client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": "not_encrypted_password",
            },
        )

        # assertion
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

    # <Error_2_1>
    # AuthorizationError
    # issuer does not exist
    def test_error_2_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = [
            {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
        ]
        resp = client.post(
            self.test_url.format(_token_address),
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

    # <Error_2_2>
    # AuthorizationError
    # password mismatch
    def test_error_2_2(self, client, db):
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
        req_param = [
            {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
        ]
        resp = client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("mismatch_password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_3>
    # HTTPException 404
    # token not found
    def test_error_3(self, client, db):
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
        req_param = [
            {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
        ]
        resp = client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_4_1>
    # InvalidParameterError
    # processing token
    def test_error_4_1(self, client, db):
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
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = [
            {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
        ]
        resp = client.post(
            self.test_url.format(_token_address),
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

    # <Error_4_2>
    # InvalidParameterError
    # personal info list is empty
    def test_error_4_2(self, client, db):
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
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 1
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = []
        resp = client.post(
            self.test_url.format(_token_address),
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
            "detail": "personal information list must not be empty",
        }
