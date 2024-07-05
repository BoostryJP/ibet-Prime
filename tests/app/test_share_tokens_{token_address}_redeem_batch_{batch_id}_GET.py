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
    BatchIssueRedeem,
    BatchIssueRedeemProcessingCategory,
    BatchIssueRedeemUpload,
    IDXPersonalInfo,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressRedeemBatchBatchIdGET:
    # target API endpoint
    base_url = "/share/tokens/{}/redeem/batch/{}"

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",
        "0e778f46-864e-4ec0-b566-21bd31cf63ff",
    ]

    account_list = [
        {"address": config_eth_account("user1")["address"], "amount": 1},
        {"address": config_eth_account("user2")["address"], "amount": 2},
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1_1
    # Single Record(No personal information)
    def test_normal_1_1(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = test_token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        batch_upload = BatchIssueRedeemUpload()
        batch_upload.upload_id = self.upload_id_list[0]
        batch_upload.issuer_address = issuer_address
        batch_upload.token_type = TokenType.IBET_SHARE.value
        batch_upload.token_address = test_token_address
        batch_upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
        batch_upload.processed = True
        db.add(batch_upload)

        batch_record = BatchIssueRedeem()
        batch_record.upload_id = self.upload_id_list[0]
        batch_record.account_address = self.account_list[0]["address"]
        batch_record.amount = self.account_list[0]["amount"]
        batch_record.status = 1
        db.add(batch_record)

        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = self.account_list[0]["address"]
        idx_personal_info_1.issuer_address = "other_issuer_address"
        idx_personal_info_1._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(idx_personal_info_1)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(test_token_address, self.upload_id_list[0]),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "processed": True,
            "results": [
                {
                    "account_address": self.account_list[0]["address"],
                    "amount": self.account_list[0]["amount"],
                    "status": 1,
                    "personal_information": {
                        "key_manager": None,
                        "address": None,
                        "birth": None,
                        "email": None,
                        "is_corporate": None,
                        "name": None,
                        "postal_code": None,
                        "tax_category": None,
                    },
                }
            ],
        }

    # Normal_1_2
    # Single Record(With personal information)
    def test_normal_1_2(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = test_token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        batch_upload = BatchIssueRedeemUpload()
        batch_upload.upload_id = self.upload_id_list[0]
        batch_upload.issuer_address = issuer_address
        batch_upload.token_type = TokenType.IBET_SHARE.value
        batch_upload.token_address = test_token_address
        batch_upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
        batch_upload.processed = True
        db.add(batch_upload)

        batch_record = BatchIssueRedeem()
        batch_record.upload_id = self.upload_id_list[0]
        batch_record.account_address = self.account_list[0]["address"]
        batch_record.amount = self.account_list[0]["amount"]
        batch_record.status = 1
        db.add(batch_record)

        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = self.account_list[0]["address"]
        idx_personal_info_1.issuer_address = issuer_address
        idx_personal_info_1._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(idx_personal_info_1)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(test_token_address, self.upload_id_list[0]),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "processed": True,
            "results": [
                {
                    "account_address": self.account_list[0]["address"],
                    "amount": self.account_list[0]["amount"],
                    "status": 1,
                    "personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                }
            ],
        }

    # Normal_2
    # Multiple Records
    def test_normal_2(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = test_token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        batch_upload = BatchIssueRedeemUpload()
        batch_upload.upload_id = self.upload_id_list[0]
        batch_upload.issuer_address = issuer_address
        batch_upload.token_type = TokenType.IBET_SHARE.value
        batch_upload.token_address = test_token_address
        batch_upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
        batch_upload.processed = True
        db.add(batch_upload)

        batch_record = BatchIssueRedeem()
        batch_record.upload_id = self.upload_id_list[0]
        batch_record.account_address = self.account_list[0]["address"]
        batch_record.amount = self.account_list[0]["amount"]
        batch_record.status = 1
        db.add(batch_record)

        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = self.account_list[0]["address"]
        idx_personal_info_1.issuer_address = issuer_address
        idx_personal_info_1._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(idx_personal_info_1)

        batch_record = BatchIssueRedeem()
        batch_record.upload_id = self.upload_id_list[0]
        batch_record.account_address = self.account_list[1]["address"]
        batch_record.amount = self.account_list[1]["amount"]
        batch_record.status = 1
        db.add(batch_record)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(test_token_address, self.upload_id_list[0]),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "processed": True,
            "results": [
                {
                    "account_address": self.account_list[0]["address"],
                    "amount": self.account_list[0]["amount"],
                    "status": 1,
                    "personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                },
                {
                    "account_address": self.account_list[1]["address"],
                    "amount": self.account_list[1]["amount"],
                    "status": 1,
                    "personal_information": {
                        "key_manager": None,
                        "address": None,
                        "birth": None,
                        "email": None,
                        "is_corporate": None,
                        "name": None,
                        "postal_code": None,
                        "tax_category": None,
                    },
                },
            ],
        }

    #########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # NotFound
    def test_error_1(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = test_token_address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        batch_upload = BatchIssueRedeemUpload()
        batch_upload.upload_id = self.upload_id_list[1]
        batch_upload.issuer_address = issuer_address
        batch_upload.token_type = TokenType.IBET_SHARE.value
        batch_upload.token_address = test_token_address
        batch_upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
        batch_upload.processed = True
        db.add(batch_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(test_token_address, self.upload_id_list[0]),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "batch not found",
        }
