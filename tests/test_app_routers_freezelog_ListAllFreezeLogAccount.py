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
from app.model.db import FreezeLogAccount


class TestListAllFreezeLogAccount:
    # Target API endpoint
    test_url = "/freeze_log/accounts"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Data does not exist
    def test_normal_1(self, client, db):
        # Request target api
        resp = client.get(self.test_url)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal_2>
    # Data exist
    def test_normal_2(self, client, db):
        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = "0x1234567890123456789012345678900000000000"
        log_account.keyfile = "test_keyfile_0"
        log_account.eoa_password = "test_password_0"
        db.add(log_account)

        log_account = FreezeLogAccount()
        log_account.account_address = "0x1234567890123456789012345678900000000001"
        log_account.keyfile = "test_keyfile_1"
        log_account.eoa_password = "test_password_1"
        db.add(log_account)

        db.commit()

        # Request target api
        resp = client.get(self.test_url)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "account_address": "0x1234567890123456789012345678900000000000",
                "is_deleted": False,
            },
            {
                "account_address": "0x1234567890123456789012345678900000000001",
                "is_deleted": False,
            },
        ]
