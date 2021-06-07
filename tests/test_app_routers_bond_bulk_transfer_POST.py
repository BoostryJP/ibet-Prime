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
from app.model.db import (
    Account,
    Token,
    TokenType,
    BulkTransfer,
    BulkTransferUpload
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersBondBulkTransferPOST:
    # target API endpoint
    test_url = "/bond/bulk_transfer"

    ###########################################################################
    # Normal Case
    ###########################################################################

    admin_account = config_eth_account("user1")
    admin_address = admin_account["address"]
    admin_keyfile = admin_account["keyfile_json"]

    transfer_from_account = config_eth_account("user2")
    transfer_from = transfer_from_account["address"]

    transfer_to_account = config_eth_account("user3")
    transfer_to = transfer_to_account["address"]

    req_tokens = [
        "0xbB4138520af85fAfdDAACc7F0AabfE188334D0ca",
        "0x55e20Fa9F4Fa854Ef06081734872b734c105916b",
        "0x1d2E98AD049e978B08113fD282BD42948F265DDa",
        "0x2413a63D91eb10e1472a18aD4b9628fBE4aac8B8",
        "0x6f9486251F4034C251ecb8Fa0f087CDDb3cDe6d7"
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",  # 0: under progress
        "de778f46-864e-4ec0-b566-21bd31cf63ff",  # 1: succeeded
        "cf33d48f-9e6e-4a36-a55e-5bbcbda69c80"  # 2: failed
    ]

    # <Normal_1>
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
            _token.type = TokenType.IBET_STRAIGHT_BOND
            _token.tx_hash = ""
            _token.issuer_address = self.admin_address
            _token.token_address = _t
            _token.abi = ""
            db.add(_token)

        # request target API
        req_param = [
            {
                "token_address": self.req_tokens[0],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 5
            }, {
                "token_address": self.req_tokens[1],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 10
            }
        ]
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 200

        bulk_transfer_upload = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.upload_id == resp.json()["upload_id"]). \
            all()
        assert len(bulk_transfer_upload) == 1
        assert bulk_transfer_upload[0].issuer_address == self.admin_address
        assert bulk_transfer_upload[0].status == 0

        bulk_transfer = db.query(BulkTransfer). \
            filter(BulkTransfer.upload_id == resp.json()["upload_id"]). \
            order_by(BulkTransfer.id). \
            all()
        assert len(bulk_transfer) == 2
        assert bulk_transfer[0].issuer_address == self.admin_address
        assert bulk_transfer[0].token_address == self.req_tokens[0]
        assert bulk_transfer[0].token_type == TokenType.IBET_STRAIGHT_BOND
        assert bulk_transfer[0].from_address == self.transfer_from
        assert bulk_transfer[0].to_address == self.transfer_to
        assert bulk_transfer[0].amount == 5
        assert bulk_transfer[0].status == 0
        assert bulk_transfer[1].issuer_address == self.admin_address
        assert bulk_transfer[1].token_address == self.req_tokens[1]
        assert bulk_transfer[1].token_type == TokenType.IBET_STRAIGHT_BOND
        assert bulk_transfer[1].from_address == self.transfer_from
        assert bulk_transfer[1].to_address == self.transfer_to
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
        _transfer_from_long = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D7811"  # long address
        _transfer_to_short = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        req_param = [
            {
                "token_address": _token_address_int,
                "transfer_from": _transfer_from_long,
                "transfer_to": _transfer_to_short,
                "amount": -1
            },
        ]

        # request target API
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
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
                    "loc": ["body", 0, "token_address"],
                    "msg": "token_address is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", 0, "transfer_from"],
                    "msg": "transfer_from is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", 0, "transfer_to"],
                    "msg": "transfer_to is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", 0, "amount"],
                    "msg": "amount must be greater than 0",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2>
    # RequestValidationError
    # headers and body required
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
    # RequestValidationError
    # issuer-address, eoa-password(required)
    def test_error_3(self, client, db):
        # request target API
        req_param = []
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": "admin_address"
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
                "loc": ["header", "eoa-password"],
                "msg": "field required",
                "type": "value_error.missing"
            }]
        }

    # <Error_4>
    # RequestValidationError
    # eoa-password(not decrypt)
    def test_error_4(self, client, db):
        # request target API
        req_param = []
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
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

    # <Error_5>
    # InvalidParameterError
    # list length is 0
    def test_error_5(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = []
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
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
            "detail": "list length is zero"
        }

    # <Error_6>
    # AuthorizationError
    # issuer does not exist
    def test_error_6(self, client, db):
        # request target API
        req_param = [
            {
                "token_address": self.req_tokens[0],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 5
            }, {
                "token_address": self.req_tokens[1],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 10
            }
        ]
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
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
    # AuthorizationError
    # password mismatch
    def test_error_7(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = [
            {
                "token_address": self.req_tokens[0],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 10
            }
        ]
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password_test")
            }
        )

        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
        }

    # <Error_8>
    # InvalidParameterError
    # token not found
    def test_error_8(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = [
            {
                "token_address": self.req_tokens[0],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 10
            }
        ]
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": f"token not found: {self.req_tokens[0]}"
        }

    # <Error_9>
    # InvalidParameterError
    # processing token
    def test_error_9(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : Tokens
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = self.admin_address
        _token.token_address = self.req_tokens[0]
        _token.abi = ""
        _token.token_status = 0
        db.add(_token)

        # request target API
        req_param = [
            {
                "token_address": self.req_tokens[0],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 10
            }
        ]
        resp = client.post(
            self.test_url,
            json=req_param,
            headers={
                "issuer-address": self.admin_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": f"wait for a while as the token is being processed: {self.req_tokens[0]}"
        }
