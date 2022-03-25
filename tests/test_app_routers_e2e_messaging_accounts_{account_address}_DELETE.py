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
from datetime import datetime

from app.model.db import (
    E2EMessagingAccount,
    E2EMessagingAccountRsaKey
)


class TestAppRoutersE2EMessagingAccountsAccountAddressPOST:
    # target API endpoint
    base_url = "/e2e_messaging/accounts/{account_address}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # RSA key is None
    def test_normal_1(self, client, db):
        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000000"
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000000"
        _rsa_key.rsa_public_key = "rsa_public_key_1_1"
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000000"
        _rsa_key.rsa_public_key = "rsa_public_key_1_2"
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = "0x1234567890123456789012345678900000000000"
        _rsa_key.rsa_public_key = "rsa_public_key_1_3"
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        # request target api
        resp = client.delete(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "rsa_key_generate_interval": 1,
            "rsa_generation": 2,
            "rsa_public_key": None,
            "is_deleted": True,
        }
        _account = db.query(E2EMessagingAccount).first()
        assert _account.is_deleted is True
        _rsa_key_list = db.query(E2EMessagingAccountRsaKey).all()
        assert len(_rsa_key_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # no data
    def test_error_1(self, client, db):
        resp = client.delete(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1, "title": "NotFound"
            },
            "detail": "e2e messaging account is not exists"
        }
