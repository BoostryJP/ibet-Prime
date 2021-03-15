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
from app.model.db import Account, Token, TokenType, \
    BulkTransfer, BulkTransferUpload
from tests.account_config import config_eth_account


class TestAppRoutersBondBulkTransferGET:

    # target API endpoint
    test_url = "/bond/bulk_transfer"

    ###########################################################################
    # Normal Case
    ###########################################################################

    upload_issuer_list = [
       {
           "address" : config_eth_account("user1")["address"],
           "keyfile" : config_eth_account("user1")["keyfile_json"]
       },{
           "address" : config_eth_account("user2")["address"],
           "keyfile" : config_eth_account("user2")["keyfile_json"]
       },{
           "address" : config_eth_account("user3")["address"],
           "keyfile" : config_eth_account("user3")["keyfile_json"]
       }
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",  # 0: under progress
        "de778f46-864e-4ec0-b566-21bd31cf63ff",  # 1: succeeded
        "cf33d48f-9e6e-4a36-a55e-5bbcbda69c80"   # 2: failed
    ]

    # <Normal_1>
    def test_normal_1(self, client, db):
        for _issuer in self.upload_issuer_list:
            # prepare data : Account(Issuer)
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            db.add(account)

        for i in range(0, 3):
            # prepare data : BulkTransferUpload
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
            bulk_transfer_upload.status = i
            db.add(bulk_transfer_upload)

        resp = client.get(
            self.test_url,
            headers={"issuer-address": self.upload_issuer_list[1]["address"]}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = [
            {
                "issuer_address": self.upload_issuer_list[1]["address"],
                "token_type": TokenType.IBET_STRAIGHT_BOND,
                "upload_id": self.upload_id_list[1],
                "status": 1
            }
        ]
        assert resp.json() == assumed_response

    # <Normal_2>
    def test_normal_2(self, client, db):
        for _issuer in self.upload_issuer_list:
            # prepare data : Account(Issuer)
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            db.add(account)

        for i in range(0, 3):
            # prepare data : BulkTransferUpload
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
            bulk_transfer_upload.status = i
            db.add(bulk_transfer_upload)

        resp = client.get(
            self.test_url
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = []
        for i in range(0,3):
            assumed_response.append({
                "issuer_address": self.upload_issuer_list[i]["address"],
                "token_type": TokenType.IBET_STRAIGHT_BOND,
                "upload_id": self.upload_id_list[i],
                "status": i
            })

        assert sorted(resp.json(), key=lambda x:x['upload_id']) == sorted(assumed_response, key=lambda x:x['upload_id'])
        
    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError 
    # invalid type
    def test_error_1(self, client, db):

        resp = client.get(
            self.test_url,
            headers={"issuer-address": "DUMMY ADDRESS"}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail":  [
                {
                    "loc": ["header", "issuer-address"], 
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2>
    # Upload id Not Found
    def test_error_2(self, client, db):

        # request target API
        resp = client.get(
            self.test_url
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "bulk transfer upload list not found",
        }
