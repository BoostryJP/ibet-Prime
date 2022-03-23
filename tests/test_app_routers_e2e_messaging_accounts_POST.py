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
import base64
from unittest import mock
from unittest.mock import ANY

from config import EOA_PASSWORD_PATTERN_MSG
from app.model.db import (
    E2EMessagingAccount,
    AccountRsaStatus
)
from app.utils.e2ee_utils import E2EEUtils


class TestAppRoutersE2EMessagingAccountsPOST:
    # target API endpoint
    base_url = "/e2e_messaging_accounts"

    valid_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"
    invalid_password = "password🚀"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        _accounts_before = db.query(E2EMessagingAccount).all()

        password = self.valid_password
        req_param = {
            "eoa_password": E2EEUtils.encrypt(password)
        }

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": ANY,
            "auto_generate_interval": None,
            "rsa_generation": None,
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.UNSET.value,
            "is_deleted": False,
        }

        _accounts_after = db.query(E2EMessagingAccount).all()

        assert 0 == len(_accounts_before)
        assert 1 == len(_accounts_after)
        _account = _accounts_after[0]
        assert _account.account_address == resp.json()["account_address"]
        assert _account.keyfile is not None
        assert E2EEUtils.decrypt(_account.eoa_password) == password
        assert _account.auto_generate_interval is None
        assert _account.rsa_generation is None
        assert _account.is_deleted is False

    # <Normal_2>
    # use AWS KMS
    @mock.patch("app.routers.e2e_messaging_account.AWS_KMS_GENERATE_RANDOM_ENABLED", True)
    @mock.patch("boto3.client")
    def test_normal_2(self, boto3_mock, client, db):
        _accounts_before = db.query(E2EMessagingAccount).all()

        password = self.valid_password
        req_param = {
            "eoa_password": E2EEUtils.encrypt(password),
            "auto_generate_interval": 1,
            "rsa_generation": 2,
        }

        # mock
        class KMSClientMock:
            def generate_random(self, NumberOfBytes):
                assert NumberOfBytes == 32
                return {
                    "Plaintext": b"12345678901234567890123456789012"
                }

        boto3_mock.side_effect = [
            KMSClientMock()
        ]

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": ANY,
            "auto_generate_interval": 1,
            "rsa_generation": 2,
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.UNSET.value,
            "is_deleted": False,
        }

        _accounts_after = db.query(E2EMessagingAccount).all()

        assert 0 == len(_accounts_before)
        assert 1 == len(_accounts_after)
        _account = _accounts_after[0]
        assert _account.account_address == resp.json()["account_address"]
        assert _account.keyfile is not None
        assert E2EEUtils.decrypt(_account.eoa_password) == password
        assert _account.auto_generate_interval == 1
        assert _account.rsa_generation == 2
        assert _account.is_deleted is False

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Parameter Error
    # no body
    def test_error_1_1(self, client, db):
        resp = client.post(self.base_url)

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
    # not encrypted, min
    def test_error_1_2(self, client, db):
        req_param = {
            "eoa_password": base64.encodebytes("password".encode("utf-8")).decode(),
            "auto_generate_interval": 0,
            "rsa_generation": 0,
        }

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "eoa_password"],
                    "msg": "eoa_password is not a Base64-encoded encrypted data",
                    "type": "value_error"
                },
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
        password = self.valid_password
        req_param = {
            "eoa_password": E2EEUtils.encrypt(password),
            "auto_generate_interval": 10_001,
            "rsa_generation": 101,
        }

        resp = client.post(self.base_url, json=req_param)

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
    # Invalid Password
    def test_error_2(self, client, db):
        req_param = {
            "eoa_password": E2EEUtils.encrypt(self.invalid_password)
        }

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": EOA_PASSWORD_PATTERN_MSG
        }
