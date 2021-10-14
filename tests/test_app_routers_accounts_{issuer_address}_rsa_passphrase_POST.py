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
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA

from config import PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG
from app.model.db import (
    Account,
    AccountRsaStatus
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersAccountsIssuerAddressRSAPassphrasePOST:
    # target API endpoint
    base_url = "/accounts/{}/rsa_passphrase"

    valid_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"
    invalid_password = "password🚀"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        _account = config_eth_account("user1")
        _issuer_address = _account["address"]
        _old_rsa_private_key = _account["rsa_private_key"]
        _rsa_public_key = _account["rsa_public_key"]
        _old_password = "password"
        _new_password = self.valid_password

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.rsa_private_key = _old_rsa_private_key
        account.rsa_public_key = _rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(_old_password)
        account.rsa_status = AccountRsaStatus.SET.value
        db.add(account)

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt(_old_password),
            "rsa_passphrase": E2EEUtils.encrypt(_new_password),
        }
        resp = client.post(
            self.base_url.format(_issuer_address),
            json=req_param
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None
        _account = db.query(Account).first()
        _account_rsa_private_key = _account.rsa_private_key
        _account_rsa_passphrase = E2EEUtils.decrypt(_account.rsa_passphrase)
        assert _account_rsa_private_key != _old_rsa_private_key
        assert _account_rsa_passphrase == _new_password

        # decrypt test
        test_data = "test_data1234"
        pub_rsa_key = RSA.importKey(_rsa_public_key)
        pub_cipher = PKCS1_OAEP.new(pub_rsa_key)
        encrypt_data = pub_cipher.encrypt(test_data.encode("utf-8"))
        pri_rsa_key = RSA.importKey(_account_rsa_private_key, passphrase=_account_rsa_passphrase)
        pri_cipher = PKCS1_OAEP.new(pri_rsa_key)
        decrypt_data = pri_cipher.decrypt(encrypt_data).decode()
        assert decrypt_data == test_data

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # parameter error(required body)
    def test_error_1(self, client, db):
        _account = config_eth_account("user1")
        _issuer_address = _account["address"]

        # request target API
        resp = client.post(
            self.base_url.format(_issuer_address)
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
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_2>
    # parameter error(required field)
    def test_error_2(self, client, db):
        _account = config_eth_account("user1")
        _issuer_address = _account["address"]

        # request target API
        req_param = {
            "dummy": "dummy",
        }
        resp = client.post(
            self.base_url.format(_issuer_address),
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
                    "loc": ["body", "old_rsa_passphrase"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_3>
    # parameter error(not decrypt)
    def test_error_3(self, client, db):
        _account = config_eth_account("user1")
        _issuer_address = _account["address"]
        _old_password = "password"
        _new_password = self.valid_password

        # request target API
        req_param = {
            "old_rsa_passphrase": _old_password,
            "rsa_passphrase": _new_password,
        }
        resp = client.post(
            self.base_url.format(_issuer_address),
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
                    "loc": ["body", "old_rsa_passphrase"],
                    "msg": "old_rsa_passphrase is not a Base64-encoded encrypted data",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "rsa_passphrase is not a Base64-encoded encrypted data",
                    "type": "value_error"
                },
            ]
        }

    # <Error_4>
    # No data
    def test_error_4(self, client, db):
        _old_password = "password"
        _new_password = self.valid_password

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt(_old_password),
            "rsa_passphrase": E2EEUtils.encrypt(_new_password),
        }
        resp = client.post(
            self.base_url.format("non_existent_issuer_address"),
            json=req_param
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1, "title": "NotFound"
            },
            "detail": "issuer is not exists"
        }

    # <Error_5>
    # old password mismatch
    def test_error_5(self, client, db):
        _account = config_eth_account("user1")
        _issuer_address = _account["address"]
        _old_rsa_private_key = _account["rsa_private_key"]
        _rsa_public_key = _account["rsa_public_key"]
        _old_password = "password"
        _new_password = self.valid_password

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.rsa_private_key = _old_rsa_private_key
        account.rsa_public_key = _rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(_old_password)
        account.rsa_status = AccountRsaStatus.SET.value
        db.add(account)

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt("passwordtest"),
            "rsa_passphrase": E2EEUtils.encrypt(_new_password),
        }
        resp = client.post(
            self.base_url.format(_issuer_address),
            json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1, "title": "InvalidParameterError"
            },
            "detail": "old passphrase mismatch"
        }

    # <Error_6>
    # password policy
    def test_error_6(self, client, db):
        _account = config_eth_account("user1")
        _issuer_address = _account["address"]
        _old_rsa_private_key = _account["rsa_private_key"]
        _rsa_public_key = _account["rsa_public_key"]
        _old_password = "password"
        _new_password = self.invalid_password

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.rsa_private_key = _old_rsa_private_key
        account.rsa_public_key = _rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(_old_password)
        account.rsa_status = AccountRsaStatus.SET.value
        db.add(account)

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt(_old_password),
            "rsa_passphrase": E2EEUtils.encrypt(_new_password),
        }
        resp = client.post(
            self.base_url.format(_issuer_address),
            json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1, "title": "InvalidParameterError"
            },
            "detail": PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG
        }
