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
    BatchForceUnlock,
    BatchForceUnlockUpload,
    Token,
    TokenType,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressForceUnlockBatchBatchIdGET:
    # target API endpoint
    base_url = "/share/tokens/{}/force_unlock/batch/{}"

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",
        "0e778f46-864e-4ec0-b566-21bd31cf63ff",
    ]

    account_list = [
        {
            "account_address": config_eth_account("user1")["address"],
            "lock_address": config_eth_account("user2")["address"],
            "recipient_address": config_eth_account("user3")["address"],
            "value": 1,
        },
        {
            "account_address": config_eth_account("user2")["address"],
            "lock_address": config_eth_account("user3")["address"],
            "recipient_address": config_eth_account("user4")["address"],
            "value": 2,
        },
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # Single Record
    def test_normal_1(self, client, db):
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
        db.add(token)

        batch_upload = BatchForceUnlockUpload()
        batch_upload.batch_id = self.upload_id_list[0]
        batch_upload.issuer_address = issuer_address
        batch_upload.token_type = TokenType.IBET_SHARE.value
        batch_upload.token_address = test_token_address
        batch_upload.status = 1
        db.add(batch_upload)

        batch_record = BatchForceUnlock()
        batch_record.batch_id = self.upload_id_list[0]
        batch_record.token_address = test_token_address
        batch_record.token_type = TokenType.IBET_SHARE.value
        batch_record.account_address = self.account_list[0]["account_address"]
        batch_record.lock_address = self.account_list[0]["lock_address"]
        batch_record.recipient_address = self.account_list[0]["recipient_address"]
        batch_record.value = self.account_list[0]["value"]
        batch_record.status = 1
        db.add(batch_record)

        # request target API
        resp = client.get(
            self.base_url.format(test_token_address, self.upload_id_list[0]),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "status": 1,
            "results": [
                {
                    "id": 1,
                    "account_address": self.account_list[0]["account_address"],
                    "lock_address": self.account_list[0]["lock_address"],
                    "recipient_address": self.account_list[0]["recipient_address"],
                    "value": self.account_list[0]["value"],
                    "status": 1,
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
        db.add(token)

        batch_upload = BatchForceUnlockUpload()
        batch_upload.batch_id = self.upload_id_list[0]
        batch_upload.issuer_address = issuer_address
        batch_upload.token_type = TokenType.IBET_SHARE.value
        batch_upload.token_address = test_token_address
        batch_upload.status = 1
        db.add(batch_upload)

        batch_record = BatchForceUnlock()
        batch_record.batch_id = self.upload_id_list[0]
        batch_record.token_address = test_token_address
        batch_record.token_type = TokenType.IBET_SHARE.value
        batch_record.account_address = self.account_list[0]["account_address"]
        batch_record.lock_address = self.account_list[0]["lock_address"]
        batch_record.recipient_address = self.account_list[0]["recipient_address"]
        batch_record.value = self.account_list[0]["value"]
        batch_record.status = 1
        db.add(batch_record)

        batch_record = BatchForceUnlock()
        batch_record.batch_id = self.upload_id_list[0]
        batch_record.token_address = test_token_address
        batch_record.token_type = TokenType.IBET_SHARE.value
        batch_record.account_address = self.account_list[1]["account_address"]
        batch_record.lock_address = self.account_list[1]["lock_address"]
        batch_record.recipient_address = self.account_list[1]["recipient_address"]
        batch_record.value = self.account_list[1]["value"]
        batch_record.status = 1
        db.add(batch_record)

        # request target API
        resp = client.get(
            self.base_url.format(test_token_address, self.upload_id_list[0]),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "status": 1,
            "results": [
                {
                    "id": 1,
                    "account_address": self.account_list[0]["account_address"],
                    "lock_address": self.account_list[0]["lock_address"],
                    "recipient_address": self.account_list[0]["recipient_address"],
                    "value": self.account_list[0]["value"],
                    "status": 1,
                },
                {
                    "id": 2,
                    "account_address": self.account_list[1]["account_address"],
                    "lock_address": self.account_list[1]["lock_address"],
                    "recipient_address": self.account_list[1]["recipient_address"],
                    "value": self.account_list[1]["value"],
                    "status": 1,
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
        db.add(token)

        batch_upload = BatchForceUnlockUpload()
        batch_upload.batch_id = self.upload_id_list[1]
        batch_upload.issuer_address = issuer_address
        batch_upload.token_type = TokenType.IBET_SHARE.value
        batch_upload.token_address = test_token_address
        batch_upload.status = 1
        db.add(batch_upload)

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
