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
from config import PERSONAL_INFO_PASSPHRASE_PATTERN_MSG
from app.model.db import Account, AccountRsaKeyTemporary
from app.model.utils import SecureValueUtils
from tests.account_config import config_eth_account


class TestAppRoutersAccountsRsakeyPOST:
    # target API endpoint
    apiurl = "/accounts/rsakey"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account_before = Account()
        _account_before.issuer_address = _user_1["address"]
        _account_before.keyfile = _user_1["keyfile_json"]
        _account_before.rsa_private_key = _user_1["rsa_private_key"]
        _account_before.rsa_public_key = _user_1["rsa_public_key"]
        rsa_encrypt_passphrase = SecureValueUtils.encrypt("password")
        _account_before.rsa_passphrase = rsa_encrypt_passphrase
        db.add(_account_before)
        db.commit()

        _temporary_before = db.query(AccountRsaKeyTemporary).all()

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"],
            "passphrase": SecureValueUtils.encrypt("password")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _user_1["address"],
            "rsa_public_key": _user_2["rsa_public_key"]
        }

        _temporary_after = db.query(AccountRsaKeyTemporary).all()
        _temporary = _temporary_after[0]
        assert _temporary.issuer_address == _user_1["address"]
        assert _temporary.rsa_private_key == _user_1["rsa_private_key"]
        assert _temporary.rsa_public_key == _user_1["rsa_public_key"]
        assert _temporary.rsa_passphrase == rsa_encrypt_passphrase
        _account_after = db.query(Account).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.rsa_private_key == _user_2["rsa_private_key"]
        assert _account_after.rsa_public_key == _user_2["rsa_public_key"]
        assert _account_after.rsa_passphrase is not None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):

        resp = client.post(
            self.apiurl
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
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_2>
    # Parameter Error: issuer-address
    def test_error_2(self, client, db):
        _user_2 = config_eth_account("user2")

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"],
            "passphrase": SecureValueUtils.encrypt("password")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": "0x0"})

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }]
        }

    # <Error_3>
    # Not Exists Account
    def test_error_3(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"],
            "passphrase": SecureValueUtils.encrypt("password")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_2["address"]})

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "issuer is not exists"
        }

    # <Error_4>
    # Now Changing Account
    def test_error_4(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"],
            "passphrase": SecureValueUtils.encrypt("password")
        }

        _temporary = AccountRsaKeyTemporary()
        _temporary.issuer_address = _user_1["address"]
        _temporary.rsa_private_key = _user_1["rsa_private_key"]
        _temporary.rsa_public_key = _user_1["rsa_public_key"]
        db.add(_temporary)

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "issuer information is now changing"
        }

    # <Error_5>
    # Invalid Private Key
    def test_error_5(self, client, db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_private_key": "test",
            "passphrase": SecureValueUtils.encrypt("password")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "RSA Private Key is invalid, or passphrase is invalid"
        }

    # <Error_6>
    # Incorrect Passphrase
    def test_error_6(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"],
            "passphrase": SecureValueUtils.encrypt("hogehoge")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "RSA Private Key is invalid, or passphrase is invalid"
        }

    # <Error_7>
    # Sending Public Key
    def test_error_7(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_public_key"],
            "passphrase": SecureValueUtils.encrypt("password")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "RSA Private Key is invalid"
        }

    # <Error_8>
    # RSA Key Length Invalid
    def test_error_8(self, client, db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        rsa_private_key = "-----BEGIN RSA PRIVATE KEY-----\n" \
                          "Proc-Type: 4,ENCRYPTED\n" \
                          "DEK-Info: DES-EDE3-CBC,3163E6CFD0428406\n" \
                          "\n" \
                          "6cF8OBUM3Y1g4+4T3mx1/cNePVRLpGVKGl1jPUuffS66Ey83Bwq1VVkw4VPfIomN\n" \
                          "VqZ8PApC4CHyrALe8zPmtE4ZE6vMbvyVsZhzsBCow+D76LVjGTNCXutkDMFp4dRw\n" \
                          "2kje+2ImKjzDL0tFEDFV+vWDfUD62B/+482NfPDkM21meDGvVuJAYkLFAw7IRbE9\n" \
                          "uPHBJIX1fC9y3jbm4DTpS670EtStaAlshEL47V7ncclxQiiKR5HsyLOC+oo45KY3\n" \
                          "NN9lc5wYhZYek97twq6HwNQkRHZXMlEzZvgxwVTeC3fpz4Qu9FZTi2VgMRfMO7kM\n" \
                          "L1fges5FzUAUaUzzHk2QefVq0b5erQCk0KiqExtAChy33+cJrswXek5JdLMhuGu5\n" \
                          "/ECLx6Y+/rOaaMJ/RLRKIEovjfh1gRgRsHDMmG6IGVuidya9gFMiCKP30fo8Wh7j\n" \
                          "wAf9akbn1Facoxvy2ptvompaQX3MLi/3uW3M/hnD1dkgpsIsIH47txrvgFHfxnSk\n" \
                          "7vrKe/YXJ9h3puyjh3r5bcOmU7y4VtFaYGOO6MF5SwT3Df6uRYpH9TQTKcZQklQJ\n" \
                          "IZD4dozg7IdMG6Gs6Gn5z6PLzaEg2mZkoM+BpfHMj9u/Ju7yj3kvTlNfcoMbnwff\n" \
                          "qOzCyF4D0Q23EpMLguHrAXeZp8qkXO+w54kQ7WeMSZV+p7l0Wg/u9MgrP9FH6DPC\n" \
                          "YRfcn3f6407gF5eHx7FjLnFI+56ZAbv10K7yEc/hhFz4bLUrxqXL0+OZYpAiOUcb\n" \
                          "ZnIqZEM8/De2a7kH+zg6heaAfRSAaWKJHC+4xHG1hTc1LboOX+x6jQ==\n" \
                          "-----END RSA PRIVATE KEY-----"
        req_param = {
            "rsa_private_key": rsa_private_key,
            "passphrase": SecureValueUtils.encrypt("password")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "RSA Key length(bits) is invalid"
        }

    # <Error_9>
    # Invalid Passphrase
    def test_error_9(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"],
            "passphrase": "test"  # Not Base64-encoded
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["body", "passphrase"],
                "msg": "passphrase is not a Base64-decoded encrypted data",
                "type": "value_error"
            }]
        }

    # <Error_10>
    # Passphrase Policy Violation
    def test_error_10(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = SecureValueUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"],
            "passphrase": SecureValueUtils.encrypt("test")
        }

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": _user_1["address"]})

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": PERSONAL_INFO_PASSPHRASE_PATTERN_MSG
        }
