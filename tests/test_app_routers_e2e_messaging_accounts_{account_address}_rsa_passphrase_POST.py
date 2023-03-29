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

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA

from app.model.db import E2EMessagingAccount, E2EMessagingAccountRsaKey
from app.utils.e2ee_utils import E2EEUtils
from config import E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG
from tests.account_config import config_eth_account


class TestAppRoutersE2EMessagingAccountsAccountAddressRsakeyPOST:
    # target API endpoint
    base_url = "/e2e_messaging/accounts/{account_address}/rsa_passphrase"

    rsa_private_key = """-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: DES-EDE3-CBC,7A0E9E7404771106

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
-----END RSA PRIVATE KEY-----"""
    rsa_public_key = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvOlb0wLo/vw/FwFys8IX
/DE4pMNLGA/mJoZ6jz0DdQG4JqGnIitzdaPreZK9H75Cfs5yfNJmP7kJixqSNjyz
WFyZ+0Jf+hwaZ6CxIyTp4zm7A0OLdqzsFIdXXHWFF10g3iwd2KkvKeuocD5c/TT8
tuI2MzhLPwCUn/umBlVPswsRucAC67U5gig5KdeKkR6JdfwVO7OpeMX3gJT6A/Ns
YE/ce4vvF/aH7mNmirnCpkfeqEk5ANpw6bdpEGwYXAdxdD3DhIabMxUvrRZp5LEh
E7pl6K6sCvVKAPl5HPtZ5/AL/Kj7iLU88qY+TYE9bSTtWqhGabSlON7bo132EkZn
Y8BnCy4c8ni00hRkxQ8ZdH468DjzaXOtiNlBLGV7BXiMf7zIE3YJD7Xd22g/XKMs
FsL7F45sgez6SBxiVQrk5WuFtLLD08+3ZAYKqaxFmesw1Niqg6mBB1E+ipYOeBlD
xtUxBqY1kHdua48rjTwEBJz6M+X6YUzIaDS/j/GcFehSyBthj099whK629i1OY3A
PhrKAc+Fywn8tNTkjicPHdzDYzUL2STwAzhrbSfIIc2HlZJSks0Fqs+tQ4Iugep6
fdDfFGjZcF3BwH6NA0frWvUW5AhhkJyJZ8IJ4C0UqakBrRLn2rvThvdCPNPWJ/tx
EK7Y4zFFnfKP3WIA3atUbbcCAwEAAQ==
-----END PUBLIC KEY-----"""

    # <Normal_1>
    def test_normal_1(self, client, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_passphrase = "password"
        new_passphrase = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = "rsa_private_key_1_1"
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt("password_1")
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = "rsa_private_key_1_2"
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt("password_2")
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = self.rsa_private_key
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt(old_passphrase)
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt(old_passphrase),
            "rsa_passphrase": E2EEUtils.encrypt(new_passphrase),
        }
        resp = client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None
        _rsa_key_list = (
            db.query(E2EMessagingAccountRsaKey)
            .order_by(E2EMessagingAccountRsaKey.block_timestamp)
            .all()
        )
        assert len(_rsa_key_list) == 3
        _rsa_key = _rsa_key_list[2]
        assert _rsa_key.rsa_private_key != self.rsa_private_key
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == new_passphrase

        # test new rsa private key
        test_data = "test_data1234"
        pub_rsa_key = RSA.importKey(self.rsa_public_key)
        pub_cipher = PKCS1_OAEP.new(pub_rsa_key)
        encrypt_data = pub_cipher.encrypt(test_data.encode("utf-8"))
        pri_rsa_key = RSA.importKey(_rsa_key.rsa_private_key, passphrase=new_passphrase)
        pri_cipher = PKCS1_OAEP.new(pri_rsa_key)
        decrypt_data = pri_cipher.decrypt(encrypt_data).decode()
        assert decrypt_data == test_data

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
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
        }

    # <Error_1_2>
    # Parameter Error
    # no required field
    def test_error_1_2(self, client, db):
        req_param = {}
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
                    "loc": ["body", "old_rsa_passphrase"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }

    # <Error_1_3>
    # Parameter Error
    # not decrypt
    def test_error_1_3(self, client, db):
        old_passphrase = "password"
        new_passphrase = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"

        req_param = {
            "old_rsa_passphrase": old_passphrase,
            "rsa_passphrase": new_passphrase,
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
                    "loc": ["body", "old_rsa_passphrase"],
                    "msg": "old_rsa_passphrase is not a Base64-encoded encrypted data",
                    "type": "value_error",
                },
                {
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "rsa_passphrase is not a Base64-encoded encrypted data",
                    "type": "value_error",
                },
            ],
        }

    # <Error_2_1>
    # no data
    # e2e messaging account
    def test_error_2_1(self, client, db):
        old_passphrase = "password"
        new_passphrase = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"

        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt(old_passphrase),
            "rsa_passphrase": E2EEUtils.encrypt(new_passphrase),
        }
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

    # <Normal_2_2>
    # no data
    # rsa key
    def test_normal_2_2(self, client, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_passphrase = "password"
        new_passphrase = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt(old_passphrase),
            "rsa_passphrase": E2EEUtils.encrypt(new_passphrase),
        }
        resp = client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "e2e messaging rsa key is not exists",
        }

    # <Normal_3>
    # old password mismatch
    def test_normal_3(self, client, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_passphrase = "password"
        new_passphrase = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = self.rsa_private_key
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt(old_passphrase)
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt("passphrasetest"),
            "rsa_passphrase": E2EEUtils.encrypt(new_passphrase),
        }
        resp = client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "old passphrase mismatch",
        }

    # <Normal_4>
    # Passphrase Policy Violation
    def test_normal_4(self, client, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_passphrase = "password"
        new_passphrase = "password🚀"

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = self.rsa_private_key
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt(old_passphrase)
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)

        # request target API
        req_param = {
            "old_rsa_passphrase": E2EEUtils.encrypt(old_passphrase),
            "rsa_passphrase": E2EEUtils.encrypt(new_passphrase),
        }
        resp = client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG,
        }
