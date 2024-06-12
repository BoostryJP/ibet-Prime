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

import time
from datetime import UTC, datetime

from app.model.db import E2EMessagingAccount, E2EMessagingAccountRsaKey


class TestAppRoutersE2EMessagingAccountsGET:
    # target API endpoint
    base_url = "/e2e_messaging/accounts"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    def test_normal_1(self, client, db):
        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal_2>
    # 1 record
    def test_normal_2(self, client, db):
        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000000"
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000000"
        _rsa_key.rsa_public_key = "rsa_public_key_1_1"
        _rsa_key.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_rsa_key)
        time.sleep(1)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "account_address": "0x1234567890123456789012345678900000000000",
                "rsa_key_generate_interval": 1,
                "rsa_generation": 2,
                "rsa_public_key": "rsa_public_key_1_1",
                "is_deleted": False,
            },
        ]

    # <Normal_3>
    # multi record
    def test_normal_3(self, client, db):
        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000000"
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000000"
        _rsa_key.rsa_public_key = "rsa_public_key_1_1"
        _rsa_key.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_rsa_key)
        time.sleep(1)

        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000001"
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        _account.is_deleted = True
        db.add(_account)

        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000002"
        _account.rsa_key_generate_interval = 3
        _account.rsa_generation = 4
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000002"
        _rsa_key.rsa_public_key = "rsa_public_key_2_1"
        _rsa_key.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_rsa_key)
        time.sleep(1)

        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000003"
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000003"
        _rsa_key.rsa_public_key = "rsa_public_key_3_1"
        _rsa_key.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_rsa_key)
        time.sleep(1)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000003"
        _rsa_key.rsa_public_key = "rsa_public_key_3_2"
        _rsa_key.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_rsa_key)
        time.sleep(1)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000003"
        _rsa_key.rsa_public_key = "rsa_public_key_3_3"
        _rsa_key.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_rsa_key)
        time.sleep(1)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "account_address": "0x1234567890123456789012345678900000000000",
                "rsa_key_generate_interval": 0,
                "rsa_generation": 0,
                "rsa_public_key": "rsa_public_key_1_1",
                "is_deleted": False,
            },
            {
                "account_address": "0x1234567890123456789012345678900000000001",
                "rsa_key_generate_interval": 1,
                "rsa_generation": 2,
                "rsa_public_key": None,
                "is_deleted": True,
            },
            {
                "account_address": "0x1234567890123456789012345678900000000002",
                "rsa_key_generate_interval": 3,
                "rsa_generation": 4,
                "rsa_public_key": "rsa_public_key_2_1",
                "is_deleted": False,
            },
            {
                "account_address": "0x1234567890123456789012345678900000000003",
                "rsa_key_generate_interval": 0,
                "rsa_generation": 0,
                "rsa_public_key": "rsa_public_key_3_3",
                "is_deleted": False,
            },
        ]

    ###########################################################################
    # Error Case
    ###########################################################################
