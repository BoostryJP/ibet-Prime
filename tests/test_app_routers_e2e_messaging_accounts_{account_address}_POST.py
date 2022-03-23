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
    E2EMessagingAccountRsaKey,
    AccountRsaStatus
)


class TestAppRoutersE2EMessagingAccountsAccountAddressPOST:
    # target API endpoint
    base_url = "/e2e_messaging_accounts/{account_address}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # RSA key is None
    def test_normal_1(self, client, db):
        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000000"
        _account.auto_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        # request target api
        req_param = {}
        resp = client.post(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "auto_generate_interval": None,
            "rsa_generation": None,
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.UNSET.value,
            "is_deleted": False,
        }
        _account = db.query(E2EMessagingAccount).first()
        assert _account.auto_generate_interval is None
        assert _account.rsa_generation is None

    # <Normal_2>
    # RSA key is not None
    def test_normal_2(self, client, db):
        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = "0x1234567890123456789012345678900000000000"
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
        req_param = {
            "auto_generate_interval": 1,
            "rsa_generation": 2,
        }
        resp = client.post(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "auto_generate_interval": 1,
            "rsa_generation": 2,
            "rsa_public_key": "rsa_public_key_1_3",
            "rsa_status": AccountRsaStatus.SET.value,
            "is_deleted": False,
        }
        _account = db.query(E2EMessagingAccount).first()
        assert _account.auto_generate_interval == 1
        assert _account.rsa_generation == 2

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Parameter Error
    # no body
    def test_error_1_1(self, client, db):
        resp = client.post(self.base_url.format(account_address="0x1234567890123456789012345678900000000000"))

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_1_2>
    # Parameter Error
    # min
    def test_error_1_2(self, client, db):
        req_param = {
            "auto_generate_interval": 0,
            "rsa_generation": 0,
        }
        resp = client.post(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
            json=req_param
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
                    "loc": ["body", "auto_generate_interval"],
                    "ctx": {"limit_value": 1},
                    "msg": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                },
                {
                    "loc": ["body", "rsa_generation"],
                    "ctx": {"limit_value": 1},
                    "msg": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                },
            ]
        }

    # <Error_1_3>
    # Parameter Error
    # max
    def test_error_1_3(self, client, db):
        req_param = {
            "auto_generate_interval": 10_001,
            "rsa_generation": 101,
        }
        resp = client.post(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
            json=req_param
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
                    "loc": ["body", "auto_generate_interval"],
                    "ctx": {"limit_value": 10_000},
                    "msg": "ensure this value is less than or equal to 10000",
                    "type": "value_error.number.not_le"
                },
                {
                    "loc": ["body", "rsa_generation"],
                    "ctx": {"limit_value": 100},
                    "msg": "ensure this value is less than or equal to 100",
                    "type": "value_error.number.not_le"
                },
            ]
        }

    # <Error_2>
    # no data
    def test_error_2(self, client, db):
        req_param = {}
        resp = client.post(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
            json=req_param
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1, "title": "NotFound"
            },
            "detail": "e2e messaging account is not exists"
        }
