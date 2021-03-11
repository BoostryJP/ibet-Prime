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
import json

from unittest import mock
from unittest.mock import ANY, MagicMock

from app.model.db import Account, Token, TokenType, \
     BulkTransfer, BulkTransferUpload, IDXTransfer
from app.exceptions import SendTransactionError
from tests.account_config import config_eth_account


class TestAppRoutersBondTransferPOST:
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

    under_transfer = [
        "0x35C02f7e6700234d8AB9b4Af472ef84FF0e046Ab"
    ]
    under_bulk_transfer = [
        "0x0B6C75Dc8432367894E19c8B93075C619906e8b0",
        "0x0a7860820Ba29a13A72c75aF123508ec614D88B5"
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643", # 0: under progress
        "de778f46-864e-4ec0-b566-21bd31cf63ff", # 1: succeeded
        "cf33d48f-9e6e-4a36-a55e-5bbcbda69c80"  # 2: failed
    ]

    # <Normal_1> : No skip access_token
    def test_normal_1(self, client, db):

        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        db.add(account)

        # prepare data : Tokens
        _all_tokens=[]
        for _t in self.req_tokens + self.under_transfer + self.under_bulk_transfer:
            _token = Token()
            _token.type = TokenType.IBET_STRAIGHT_BOND
            _token.tx_hash = ""
            _token.issuer_address = self.admin_address
            _token.token_address= _t
            _token.abi = ""
            _all_tokens.append(_token)
        db.add_all(_all_tokens)

        # prepare data : IDXTransfer
        for _t in self.under_transfer:
            _idx_transfer = IDXTransfer()
            _idx_transfer.token_address = _t
            _idx_transfer.eth_account = self.admin_address
            _idx_transfer.transfer_from = self.transfer_from
            _idx_transfer.transfer_to = self.transfer_to
            _idx_transfer.amount = 100
            db.add(_idx_transfer)

        # prepare data : BulkTransferUpload
        for _status in range(0, 2):
            _bulk_transfer_upload = BulkTransferUpload()
            _bulk_transfer_upload.upload_id = self.upload_id_list[_status]
            _bulk_transfer_upload.eth_account = self.admin_address
            _bulk_transfer_upload.status =  _status
            db.add(_bulk_transfer_upload)

        # prepare data : BulkTransfer
        for _under_bt_ta in self.under_bulk_transfer:
            _bulk_transfer = BulkTransfer()
            _bulk_transfer.eth_account =  self.admin_address
            _bulk_transfer.upload_id = self.upload_id_list[0] # under transfer
            _bulk_transfer.token_address = _under_bt_ta
            _bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND
            _bulk_transfer.from_address = self.transfer_from
            _bulk_transfer.to_address = self.transfer_to
            _bulk_transfer.amount = 100
            _bulk_transfer.status = 0
            db.add(_bulk_transfer)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.req_tokens[0],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 5
                },{
                    "token_address": self.req_tokens[1],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 10
                }
            ]
        }

        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
        )

        assert resp.status_code == 200
        assert resp.json()['skipped_transfer'] == []

        #Check DB upload
        bulk_transfer_upload=db.query(BulkTransferUpload). \
                            filter(BulkTransferUpload.upload_id == resp.json()['upload_id']). \
                            all()
        assert len(bulk_transfer_upload) == 1
        assert bulk_transfer_upload[0].eth_account == self.admin_address
        assert bulk_transfer_upload[0].status == 0

        bulk_transfer=db.query(BulkTransfer). \
                         filter(BulkTransfer.upload_id == resp.json()['upload_id']). \
                         all()

        assert len(bulk_transfer) == 2
        assert bulk_transfer[0].eth_account == self.admin_address
        assert bulk_transfer[0].token_address == self.req_tokens[0]
        assert bulk_transfer[0].token_type == TokenType.IBET_STRAIGHT_BOND
        assert bulk_transfer[0].from_address == self.transfer_from
        assert bulk_transfer[0].to_address == self.transfer_to
        assert bulk_transfer[0].amount == 5
        assert bulk_transfer[0].status == 0

        assert bulk_transfer[1].eth_account == self.admin_address
        assert bulk_transfer[1].token_address == self.req_tokens[1]
        assert bulk_transfer[1].token_type == TokenType.IBET_STRAIGHT_BOND
        assert bulk_transfer[1].from_address == self.transfer_from
        assert bulk_transfer[1].to_address == self.transfer_to
        assert bulk_transfer[1].amount == 10
        assert bulk_transfer[1].status == 0

    # <Normal_2> : skip access_token
    def test_normal_2(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        db.add(account)

        # prepare data : Tokens
        _all_tokens=[]
        for _t in self.req_tokens + self.under_transfer + self.under_bulk_transfer:
            _token = Token()
            _token.type = TokenType.IBET_STRAIGHT_BOND
            _token.tx_hash = ""
            _token.issuer_address = self.admin_address
            _token.token_address= _t
            _token.abi = ""
            _all_tokens.append(_token)
        db.add_all(_all_tokens)

        # prepare data : IDXTransfer
        for _t in self.under_transfer:
            _idx_transfer = IDXTransfer()
            _idx_transfer.token_address = _t
            _idx_transfer.eth_account = self.admin_address
            _idx_transfer.transfer_from = self.transfer_from
            _idx_transfer.transfer_to = self.transfer_to
            _idx_transfer.amount = 100
            db.add(_idx_transfer)

        # prepare data : BulkTransferUpload
        for _status in range(0, 2):
            _bulk_transfer_upload = BulkTransferUpload()
            _bulk_transfer_upload.upload_id = self.upload_id_list[_status]
            _bulk_transfer_upload.eth_account = self.admin_address
            _bulk_transfer_upload.status =  _status
            db.add(_bulk_transfer_upload)

        # prepare data : BulkTransfer
        for _under_bt_ta in self.under_bulk_transfer:
            _bulk_transfer = BulkTransfer()
            _bulk_transfer.eth_account =  self.admin_address
            _bulk_transfer.upload_id = self.upload_id_list[0] # under transfer
            _bulk_transfer.token_address = _under_bt_ta
            _bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND
            _bulk_transfer.from_address = self.transfer_from
            _bulk_transfer.to_address = self.transfer_to
            _bulk_transfer.amount = 100
            _bulk_transfer.status = 0
            db.add(_bulk_transfer)

        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.under_transfer[0],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 1
                },{
                    "token_address": self.under_bulk_transfer[0],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 5
                },{
                    "token_address": self.under_bulk_transfer[1],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount":6
                },{
                    "token_address": self.req_tokens[2],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 10
                },{
                    "token_address": self.req_tokens[3],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 15
                },{
                    "token_address": self.req_tokens[4],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 20
                }
            ]
        }

        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
        )

        assert resp.status_code == 200
        assert resp.json()['upload_id'] != None
        assert resp.json()['skipped_transfer'] == [
            {
                "amount": 1,
                "token_address": "0x35C02f7e6700234d8AB9b4Af472ef84FF0e046Ab",
                "transfer_from": "0x3Ec9E2880285FAC4fF92514754924E5d0E6264Cb",
                "transfer_to": "0x85a8b8887a4bD76859751b10C8aC8EC5f3aA1bDB"
            },{
                "amount": 5,
                "token_address": "0x0B6C75Dc8432367894E19c8B93075C619906e8b0",
                "transfer_from": "0x3Ec9E2880285FAC4fF92514754924E5d0E6264Cb",
                "transfer_to": "0x85a8b8887a4bD76859751b10C8aC8EC5f3aA1bDB"
            },{
                "amount": 6,
                "token_address": "0x0a7860820Ba29a13A72c75aF123508ec614D88B5",
                "transfer_from": "0x3Ec9E2880285FAC4fF92514754924E5d0E6264Cb",
                "transfer_to": "0x85a8b8887a4bD76859751b10C8aC8EC5f3aA1bDB"
            }
        ]

        #Check DB upload
        bulk_transfer_upload=db.query(BulkTransferUpload). \
                            filter(BulkTransferUpload.upload_id == resp.json()['upload_id']). \
                            all()
        assert len(bulk_transfer_upload) == 1
        assert bulk_transfer_upload[0].eth_account == self.admin_address
        assert bulk_transfer_upload[0].status == 0

        bulk_transfer=db.query(BulkTransfer). \
                         filter(BulkTransfer.upload_id == resp.json()['upload_id']). \
                         all()

        assert len(bulk_transfer) == 3
        assert bulk_transfer[0].eth_account == self.admin_address
        assert bulk_transfer[0].token_address == self.req_tokens[2]
        assert bulk_transfer[0].token_type == TokenType.IBET_STRAIGHT_BOND
        assert bulk_transfer[0].from_address == self.transfer_from
        assert bulk_transfer[0].to_address == self.transfer_to
        assert bulk_transfer[0].amount == 10
        assert bulk_transfer[0].status == 0

        assert bulk_transfer[1].eth_account == self.admin_address
        assert bulk_transfer[1].token_address == self.req_tokens[3]
        assert bulk_transfer[1].token_type == TokenType.IBET_STRAIGHT_BOND
        assert bulk_transfer[1].from_address == self.transfer_from
        assert bulk_transfer[1].to_address == self.transfer_to
        assert bulk_transfer[1].amount == 15
        assert bulk_transfer[1].status == 0

        assert bulk_transfer[2].eth_account == self.admin_address
        assert bulk_transfer[2].token_address == self.req_tokens[4]
        assert bulk_transfer[2].token_type == TokenType.IBET_STRAIGHT_BOND
        assert bulk_transfer[2].from_address == self.transfer_from
        assert bulk_transfer[2].to_address == self.transfer_to
        assert bulk_transfer[2].amount == 20
        assert bulk_transfer[2].status == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: transfer list is string
    def test_error_1(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        db.add(account)
        req_param = {
            "transfer_list": "this is string, not list."
        }

        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail" :[
                {
                    "loc": ["body", "transfer_list"],
                    "msg": "value is not a valid list",
                    "type": "type_error.list"
                }
            ]
        }

    # <Error_2>
    # RequestValidationError: list length is 0
    def test_error_2(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        db.add(account)
        req_param = {
            "transfer_list": []
        }

        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail" :[
                 {
                    "loc": ["body", "transfer_list"],
                    "msg": "bulk transfer must contain more than 1 transfer",
                    "type": "value_error"
                 }
            ]
        }

    # <Error_3>
    # RequestValidationError
    def test_error_3(self, client, db):
        _token_address_int = 10 # Integer
        _transfer_from_long = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D7811"  # long address
        _transfer_to_short = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D78"  # short address
        req_param = {
            "transfer_list": [
                {
                    "token_address": _token_address_int,
                    "transfer_from": _transfer_from_long,
                    "transfer_to": _transfer_to_short,
                    "amount": -1
                },
             ]
        }

        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "transfer_list", 0, "token_address"],
                    "msg": "token_address is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", "transfer_list", 0,"transfer_from"],
                    "msg": "transfer_from is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", "transfer_list", 0,"transfer_to"],
                    "msg": "transfer_to is not a valid address",
                    "type": "value_error"
                }, {
                    "loc": ["body", "transfer_list", 0,"amount"],
                    "msg": "amount must be greater than 0",
                    "type": "value_error"
                }
            ]
        }

    # <Error_4>
    # InvalidParameterError: issuer does not exist
    def test_error_4(self, client, db):
        # prepare data : Tokens
        _all_tokens=[]
        for _t in self.req_tokens + self.under_transfer + self.under_bulk_transfer:
            _token = Token()
            _token.type = TokenType.IBET_STRAIGHT_BOND
            _token.tx_hash = ""
            _token.issuer_address = self.admin_address
            _token.token_address= _t
            _token.abi = ""
            _all_tokens.append(_token)
        db.add_all(_all_tokens)

        # no need prepare data : IDXTransfer, BulkTransferUpload, BulkTransfer
        # request target API
        req_param = {
            "transfer_list": [
                {
                    "token_address": self.under_transfer[0],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 1
                },
                {
                    "token_address": self.req_tokens[0],
                    "transfer_from": self.transfer_from,
                    "transfer_to": self.transfer_to,
                    "amount": 10
                }
            ]
        }

        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "issuer does not exist"
        }

    # <Error_5>
    # InvalidParameterError: Invalid token
    def test_error_5(self, client, db):
        # prepare data : Account(Issuer)
        account = Account()
        account.issuer_address = self.admin_address
        account.keyfile = self.admin_keyfile
        db.add(account)

        # not prepare data : Token


        req_param = {
            "transfer_list": [
                {
                "token_address": self.req_tokens[0],
                "transfer_from": self.transfer_from,
                "transfer_to": self.transfer_to,
                "amount": 10
                }
            ]
        }

        resp = client.post(
            self.test_url,
            json=req_param,
            headers={"issuer-address": self.admin_address}
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail" : "token_adderess:0xbB4138520af85fAfdDAACc7F0AabfE188334D0ca does not exist"
        }
