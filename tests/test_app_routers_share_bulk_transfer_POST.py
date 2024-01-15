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

from sqlalchemy import select

from app.model.db import (
    Account,
    AuthToken,
    BulkTransfer,
    BulkTransferUpload,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareBulkTransferPOST:
    # target API endpoint
    test_url = "/share/bulk_transfer"

    ###########################################################################
    # Normal Case
    ###########################################################################

    admin_account = config_eth_account("user1")
    admin_address = admin_account["address"]
    admin_keyfile = admin_account["keyfile_json"]

    from_address_account = config_eth_account("user2")
    from_address = from_address_account["address"]

    to_address_account = config_eth_account("user3")
    to_address = to_address_account["address"]

    req_tokens = [
        "0xbB4138520af85fAfdDAACc7F0AabfE188334D0ca",
        "0x55e20Fa9F4Fa854Ef06081734872b734c105916b",
        "0x1d2E98AD049e978B08113fD282BD42948F265DDa",
        "0x2413a63D91eb10e1472a18aD4b9628fBE4aac8B8",
        "0x6f9486251F4034C251ecb8Fa0f087CDDb3cDe6d7",
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",  # 0: under progress
        "de778f46-864e-4ec0-b566-21bd31cf63ff",  # 1: succeeded
        "cf33d48f-9e6e-4a36-a55e-5bbcbda69c80",  # 2: failed
    ]

    # <Normal_1>
    # Authorization by eoa-password
    def test_normal_1(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : Tokens
        for _t in self.req_tokens:
            _token = Token()
            _token.type = TokenType.IBET_SHARE.value
            _token.tx_hash = ""
            _token.issuer_address = self.admin_address
            _token.token_address = _t
            _token.abi = ""
            _token.version = TokenVersion.V_22_12
            db.add(_token)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
                {
                    "token_address": self.req_tokens[1],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                },
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200

        bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).where(
                BulkTransferUpload.upload_id == resp.json()["upload_id"]
            )
        ).all()
        assert len(bulk_transfer_upload) == 1
        assert bulk_transfer_upload[0].issuer_address == self.admin_address
        assert bulk_transfer_upload[0].transaction_compression is None
        assert bulk_transfer_upload[0].status == 0

        bulk_transfer = db.scalars(
            select(BulkTransfer)
            .where(BulkTransfer.upload_id == resp.json()["upload_id"])
            .order_by(BulkTransfer.id)
        ).all()
        assert len(bulk_transfer) == 2
        assert bulk_transfer[0].issuer_address == self.admin_address
        assert bulk_transfer[0].token_address == self.req_tokens[0]
        assert bulk_transfer[0].token_type == TokenType.IBET_SHARE.value
        assert bulk_transfer[0].from_address == self.from_address
        assert bulk_transfer[0].to_address == self.to_address
        assert bulk_transfer[0].amount == 5
        assert bulk_transfer[0].status == 0
        assert bulk_transfer[1].issuer_address == self.admin_address
        assert bulk_transfer[1].token_address == self.req_tokens[1]
        assert bulk_transfer[1].token_type == TokenType.IBET_SHARE.value
        assert bulk_transfer[1].from_address == self.from_address
        assert bulk_transfer[1].to_address == self.to_address
        assert bulk_transfer[1].amount == 10
        assert bulk_transfer[1].status == 0

    # <Normal_2>
    # Authorization by auth-token
    def test_normal_2(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : AuthToken
        auth_token = AuthToken()
        auth_token.issuer_address = self.admin_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        db.add(auth_token)

        # prepare data : Tokens
        for _t in self.req_tokens:
            _token = Token()
            _token.type = TokenType.IBET_SHARE.value
            _token.tx_hash = ""
            _token.issuer_address = self.admin_address
            _token.token_address = _t
            _token.abi = ""
            _token.version = TokenVersion.V_22_12
            db.add(_token)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
                {
                    "token_address": self.req_tokens[1],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                },
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "auth-token": "test_auth_token",
            },
        )

        # assertion
        assert resp.status_code == 200

        bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).where(
                BulkTransferUpload.upload_id == resp.json()["upload_id"]
            )
        ).all()
        assert len(bulk_transfer_upload) == 1
        assert bulk_transfer_upload[0].issuer_address == self.admin_address
        assert bulk_transfer_upload[0].transaction_compression is None
        assert bulk_transfer_upload[0].status == 0

        bulk_transfer = db.scalars(
            select(BulkTransfer)
            .where(BulkTransfer.upload_id == resp.json()["upload_id"])
            .order_by(BulkTransfer.id)
        ).all()
        assert len(bulk_transfer) == 2
        assert bulk_transfer[0].issuer_address == self.admin_address
        assert bulk_transfer[0].token_address == self.req_tokens[0]
        assert bulk_transfer[0].token_type == TokenType.IBET_SHARE.value
        assert bulk_transfer[0].from_address == self.from_address
        assert bulk_transfer[0].to_address == self.to_address
        assert bulk_transfer[0].amount == 5
        assert bulk_transfer[0].status == 0
        assert bulk_transfer[1].issuer_address == self.admin_address
        assert bulk_transfer[1].token_address == self.req_tokens[1]
        assert bulk_transfer[1].token_type == TokenType.IBET_SHARE.value
        assert bulk_transfer[1].from_address == self.from_address
        assert bulk_transfer[1].to_address == self.to_address
        assert bulk_transfer[1].amount == 10
        assert bulk_transfer[1].status == 0

    # <Normal_3>
    # transaction_compression = True
    def test_normal_3(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.from_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : Tokens
        for _t in self.req_tokens:
            _token = Token()
            _token.type = TokenType.IBET_SHARE.value
            _token.tx_hash = ""
            _token.issuer_address = self.from_address
            _token.token_address = _t
            _token.abi = ""
            _token.version = TokenVersion.V_22_12
            db.add(_token)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                },
            ],
            "transaction_compression": True,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.from_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200

        bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).where(
                BulkTransferUpload.upload_id == resp.json()["upload_id"]
            )
        ).all()
        assert len(bulk_transfer_upload) == 1
        assert bulk_transfer_upload[0].issuer_address == self.from_address
        assert bulk_transfer_upload[0].transaction_compression is True
        assert bulk_transfer_upload[0].status == 0

        bulk_transfer = db.scalars(
            select(BulkTransfer)
            .where(BulkTransfer.upload_id == resp.json()["upload_id"])
            .order_by(BulkTransfer.id)
        ).all()
        assert len(bulk_transfer) == 2
        assert bulk_transfer[0].issuer_address == self.from_address
        assert bulk_transfer[0].token_address == self.req_tokens[0]
        assert bulk_transfer[0].token_type == TokenType.IBET_SHARE.value
        assert bulk_transfer[0].from_address == self.from_address
        assert bulk_transfer[0].to_address == self.to_address
        assert bulk_transfer[0].amount == 5
        assert bulk_transfer[0].status == 0
        assert bulk_transfer[1].issuer_address == self.from_address
        assert bulk_transfer[1].token_address == self.req_tokens[0]
        assert bulk_transfer[1].token_type == TokenType.IBET_SHARE.value
        assert bulk_transfer[1].from_address == self.from_address
        assert bulk_transfer[1].to_address == self.to_address
        assert bulk_transfer[1].amount == 10
        assert bulk_transfer[1].status == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # invalid type
    def test_error_1(self, client, db):
        _token_address_int = 10  # integer
        _from_address_long = (
            "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D7811"  # long address
        )
        _to_address_short = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        req_param = {
            "transfer_list": [
                {
                    "token_address": _token_address_int,
                    "from_address": _from_address_long,
                    "to_address": _to_address_short,
                    "amount": 0,
                },
            ]
        }

        # request target API
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "transfer_list", 0, "token_address"],
                    "msg": "Value error, value must be of string",
                    "input": 10,
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "transfer_list", 0, "from_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D7811",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "transfer_list", 0, "to_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78",
                    "ctx": {"error": {}},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "transfer_list", 0, "amount"],
                    "msg": "Input should be greater than or equal to 1",
                    "input": 0,
                    "ctx": {"ge": 1},
                },
            ],
        }

    # <Error_2>
    # RequestValidationError
    # invalid type(max value)
    def test_error_2(self, client, db):
        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 1_000_000_000_001,
                }
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "less_than_equal",
                    "loc": ["body", "transfer_list", 0, "amount"],
                    "msg": "Input should be less than or equal to 1000000000000",
                    "input": 1000000000001,
                    "ctx": {"le": 1000000000000},
                }
            ],
        }

    # <Error_3>
    # RequestValidationError
    # headers and body required
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
    # RequestValidationError
    # issuer-address
    def test_error_4(self, client, db):
        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
            ]
        }
        resp = client.post(
            self.test_url, json=req_param, headers={"issuer-address": "admin_address"}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "admin_address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_5>
    # RequestValidationError
    # eoa-password(not decrypt)
    def test_error_5(self, client, db):
        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address, "eoa-password": "password"},
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
    # InvalidParameterError
    # list length is 0
    def test_error_6(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = {"transfer_list": []}
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "too_short",
                    "loc": ["body", "transfer_list"],
                    "msg": "List should have at least 1 item after validation, not 0",
                    "input": [],
                    "ctx": {"field_type": "List", "min_length": 1, "actual_length": 0},
                }
            ],
        }

    # <Error_7>
    # AuthorizationError
    # issuer does not exist
    def test_error_7(self, client, db):
        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
                {
                    "token_address": self.req_tokens[1],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                },
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
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
    # AuthorizationError
    # password mismatch
    def test_error_8(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                }
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_9>
    # InvalidParameterError
    # token not found
    def test_error_9(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                }
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": f"token not found: {self.req_tokens[0]}",
        }

    # <Error_10>
    # InvalidParameterError
    # processing token
    def test_error_10(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : Tokens
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.issuer_address = self.admin_address
        _token.token_address = self.req_tokens[0]
        _token.abi = ""
        _token.token_status = 0
        _token.version = TokenVersion.V_22_12
        db.add(_token)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                }
            ]
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": f"this token is temporarily unavailable: {self.req_tokens[0]}",
        }

    # <Error_11_1>
    # transaction_compression = True
    # Token addresses are not the same
    def test_error_11_1(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.from_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : Tokens
        for _t in self.req_tokens:
            _token = Token()
            _token.type = TokenType.IBET_SHARE.value
            _token.tx_hash = ""
            _token.issuer_address = self.from_address
            _token.token_address = _t
            _token.abi = ""
            _token.version = TokenVersion.V_22_12
            db.add(_token)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
                {
                    "token_address": self.req_tokens[1],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                },
            ],
            "transaction_compression": True,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.from_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "When using transaction compression, all token_address must be the same.",
        }

    # <Error_11_2>
    # transaction_compression = True
    # From addresses are not the same
    def test_error_11_2(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.from_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : Tokens
        for _t in self.req_tokens:
            _token = Token()
            _token.type = TokenType.IBET_SHARE.value
            _token.tx_hash = ""
            _token.issuer_address = self.from_address
            _token.token_address = _t
            _token.abi = ""
            _token.version = TokenVersion.V_22_12
            db.add(_token)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.to_address,  # Wrong from_address
                    "to_address": self.to_address,
                    "amount": 10,
                },
            ],
            "transaction_compression": True,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.from_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "When using transaction compression, all from_address must be the same.",
        }

    # <Error_11_3>
    # transaction_compression = True
    # from_address and issuer_address are different
    def test_error_11_3(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : Tokens
        for _t in self.req_tokens:
            _token = Token()
            _token.type = TokenType.IBET_SHARE.value
            _token.tx_hash = ""
            _token.issuer_address = self.admin_address
            _token.token_address = _t
            _token.abi = ""
            _token.version = TokenVersion.V_22_12
            db.add(_token)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 5,
                },
                {
                    "token_address": self.req_tokens[0],
                    "from_address": self.from_address,
                    "to_address": self.to_address,
                    "amount": 10,
                },
            ],
            "transaction_compression": True,
        }
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "When using transaction compression, from_address must be the same as issuer_address.",
        }
