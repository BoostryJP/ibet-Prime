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

from config import EOA_PASSWORD_PATTERN_MSG
from app.model.db import Account, AccountRsaStatus
from app.utils.e2ee_utils import E2EEUtils


class TestAppRoutersAccountsPOST:
    # target API endpoint
    apiurl = "/accounts"

    valid_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"
    invalid_password = "password🚀"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        accounts_before = db.query(Account).all()

        password = self.valid_password
        req_param = {
            "eoa_password": E2EEUtils.encrypt(password)
        }

        resp = client.post(self.apiurl, json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json()["issuer_address"] is not None
        assert resp.json()["rsa_public_key"] == ""
        assert resp.json()["rsa_status"] == AccountRsaStatus.UNSET.value
        assert resp.json()["is_deleted"] is False

        accounts_after = db.query(Account).all()

        assert 0 == len(accounts_before)
        assert 1 == len(accounts_after)
        account_1 = accounts_after[0]
        assert account_1.issuer_address == resp.json()["issuer_address"]
        assert account_1.keyfile is not None
        assert E2EEUtils.decrypt(account_1.eoa_password) == password
        assert account_1.rsa_private_key is None
        assert account_1.rsa_public_key is None
        assert account_1.rsa_passphrase is None
        assert account_1.rsa_status == AccountRsaStatus.UNSET.value
        assert account_1.is_deleted is False

    # <Normal_2>
    # AWS KMS
    @mock.patch("app.routers.account.AWS_KMS_GENERATE_RANDOM_ENABLED", True)
    @mock.patch("boto3.client")
    def test_normal_2(self, boto3_mock, client, db):
        accounts_before = db.query(Account).all()

        password = self.valid_password
        req_param = {
            "eoa_password": E2EEUtils.encrypt(password)
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

        resp = client.post(self.apiurl, json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json()["issuer_address"] is not None
        assert resp.json()["rsa_public_key"] == ""
        assert resp.json()["rsa_status"] == AccountRsaStatus.UNSET.value
        assert resp.json()["is_deleted"] is False

        accounts_after = db.query(Account).all()

        assert 0 == len(accounts_before)
        assert 1 == len(accounts_after)
        account_1 = accounts_after[0]
        assert account_1.issuer_address == resp.json()["issuer_address"]
        assert account_1.keyfile is not None
        assert E2EEUtils.decrypt(account_1.eoa_password) == password
        assert account_1.rsa_private_key is None
        assert account_1.rsa_public_key is None
        assert account_1.rsa_passphrase is None
        assert account_1.rsa_status == AccountRsaStatus.UNSET.value
        assert account_1.is_deleted is False

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Password Policy Violation
    def test_error_1(self, client, db):
        req_param = {
            "eoa_password": base64.encodebytes("password".encode("utf-8")).decode()
        }

        resp = client.post(self.apiurl, json=req_param)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["body", "eoa_password"],
                "msg": "eoa_password is not a Base64-encoded encrypted data",
                "type": "value_error"
            }]
        }

    # <Error_2>
    # Invalid Password
    def test_error_2(self, client, db):
        req_param = {
            "eoa_password": E2EEUtils.encrypt(self.invalid_password)
        }

        resp = client.post(self.apiurl, json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": EOA_PASSWORD_PATTERN_MSG
        }
