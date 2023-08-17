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
    BatchRegisterPersonalInfo,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    Token,
    TokenType,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressPersonalInfoBatchBatchIdGET:
    # target API endpoint
    base_url = "/share/tokens/{}/personal_info/batch/{}"

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",
        "0e778f46-864e-4ec0-b566-21bd31cf63ff",
        "0f33d48f-9e6e-4a36-a55e-5bbcbda69c80",
        "1c961f7d-e1ad-40e5-988b-cca3d6009643",
        "1e778f46-864e-4ec0-b566-21bd31cf63ff",
        "1f33d48f-9e6e-4a36-a55e-5bbcbda69c80",
    ]

    account_list = [
        {
            "address": config_eth_account("user1")["address"],
            "keyfile": config_eth_account("user1")["keyfile_json"],
        },
        {
            "address": config_eth_account("user2")["address"],
            "keyfile": config_eth_account("user2")["keyfile_json"],
        },
        {
            "address": config_eth_account("user3")["address"],
            "keyfile": config_eth_account("user3")["keyfile_json"],
        },
        {
            "address": config_eth_account("user4")["address"],
            "keyfile": config_eth_account("user4")["keyfile_json"],
        },
        {
            "address": config_eth_account("user5")["address"],
            "keyfile": config_eth_account("user5")["keyfile_json"],
        },
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
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
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.status = (
            BatchRegisterPersonalInfoUploadStatus.PENDING.value
        )
        db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        for i in range(0, 3):
            batch_register = BatchRegisterPersonalInfo()
            batch_register.upload_id = self.upload_id_list[0]
            batch_register.token_address = _token_address
            batch_register.account_address = self.account_list[i]["address"]
            batch_register.status = 0
            batch_register.personal_info = {
                "key_manager": "test_value",
                "name": "test_value",
                "postal_code": "1000001",
                "address": "test_value",
                "email": "test_value@a.test",
                "birth": "19900101",
                "is_corporate": True,
                "tax_category": 3,
            }
            db.add(batch_register)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "status": BatchRegisterPersonalInfoUploadStatus.PENDING.value,
            "results": [
                {
                    "status": 0,
                    "account_address": self.account_list[0]["address"],
                    "key_manager": "test_value",
                    "name": "test_value",
                    "postal_code": "1000001",
                    "address": "test_value",
                    "email": "test_value@a.test",
                    "birth": "19900101",
                    "is_corporate": True,
                    "tax_category": 3,
                },
                {
                    "status": 0,
                    "account_address": self.account_list[1]["address"],
                    "key_manager": "test_value",
                    "name": "test_value",
                    "postal_code": "1000001",
                    "address": "test_value",
                    "email": "test_value@a.test",
                    "birth": "19900101",
                    "is_corporate": True,
                    "tax_category": 3,
                },
                {
                    "status": 0,
                    "account_address": self.account_list[2]["address"],
                    "key_manager": "test_value",
                    "name": "test_value",
                    "postal_code": "1000001",
                    "address": "test_value",
                    "email": "test_value@a.test",
                    "birth": "19900101",
                    "is_corporate": True,
                    "tax_category": 3,
                },
            ],
        }

    #########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: issuer_address
    def test_error_1(self, client, db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, "test_batch_id"), headers={}
        )

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
                }
            ],
        }

    # <Error_2>
    # Batch not found
    def test_error_2(self, client, db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, "test_batch_id"),
            headers={
                "issuer-address": _issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "batch not found",
        }
