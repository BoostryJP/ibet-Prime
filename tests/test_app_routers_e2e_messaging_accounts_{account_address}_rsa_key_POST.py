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

from sqlalchemy import select

from app.model.db import E2EMessagingAccount, E2EMessagingAccountRsaKey


class TestAppRoutersE2EMessagingAccountsAccountAddressRSAKeyPOST:
    # target API endpoint
    base_url = "/e2e_messaging/accounts/{account_address}/rsa_key"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
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

        db.commit()

        # request target api
        req_param = {
            "rsa_key_generate_interval": 1,
            "rsa_generation": 2,
        }
        resp = client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "rsa_key_generate_interval": 1,
            "rsa_generation": 2,
            "rsa_public_key": "rsa_public_key_1_3",
            "is_deleted": False,
        }
        _account = db.scalars(select(E2EMessagingAccount).limit(1)).first()
        assert _account.rsa_key_generate_interval == 1
        assert _account.rsa_generation == 2

    # <Normal_2>
    # default value
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

        db.commit()

        # request target api
        req_param = {}
        resp = client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "rsa_key_generate_interval": 24,
            "rsa_generation": 7,
            "rsa_public_key": "rsa_public_key_1_3",
            "is_deleted": False,
        }
        _account = db.scalars(select(E2EMessagingAccount).limit(1)).first()
        assert _account.rsa_key_generate_interval == 24
        assert _account.rsa_generation == 7

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Parameter Error
    # no body
    def test_error_1_1(self, client, db):
        resp = client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            )
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # <Error_1_2>
    # Parameter Error
    # min
    def test_error_1_2(self, client, db):
        req_param = {
            "rsa_key_generate_interval": -1,
            "rsa_generation": -1,
        }
        resp = client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "rsa_key_generate_interval"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "rsa_generation"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
        }

    # <Error_1_3>
    # Parameter Error
    # max
    def test_error_1_3(self, client, db):
        req_param = {
            "rsa_key_generate_interval": 10_001,
            "rsa_generation": 101,
        }
        resp = client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"le": 10000},
                    "input": 10001,
                    "loc": ["body", "rsa_key_generate_interval"],
                    "msg": "Input should be less than or equal to 10000",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"le": 100},
                    "input": 101,
                    "loc": ["body", "rsa_generation"],
                    "msg": "Input should be less than or equal to 100",
                    "type": "less_than_equal",
                },
            ],
        }

    # <Error_2>
    # no data
    def test_error_2(self, client, db):
        req_param = {}
        resp = client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "e2e messaging account is not exists",
        }
