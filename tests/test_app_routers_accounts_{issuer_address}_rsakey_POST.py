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
from config import PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG, PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE, ZERO_ADDRESS
from app.model.db import Account, AccountRsaKeyTemporary, AccountRsaStatus
from app.model.utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersAccountsIssuerAddressRsakeyPOST:
    # target API endpoint
    base_url = "/accounts/{}/rsakey"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # RSA Create
    def test_normal_1(self, client, db):
        _user_1 = config_eth_account("user1")

        _account_before = Account()
        _account_before.issuer_address = _user_1["address"]
        _account_before.keyfile = _user_1["keyfile_json"]
        eoa_password = E2EEUtils.encrypt("password")
        _account_before.eoa_password = eoa_password
        _account_before.rsa_status = AccountRsaStatus.UNSET.value
        db.add(_account_before)
        db.commit()

        password = "password_create"
        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt(password)
        }

        resp = client.post(self.base_url.format(_user_1["address"]), json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _user_1["address"],
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.CREATING.value
        }
        _account_after = db.query(Account).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.eoa_password == eoa_password
        assert _account_after.rsa_private_key is None
        assert _account_after.rsa_public_key is None
        assert E2EEUtils.decrypt(_account_after.rsa_passphrase) == password
        assert _account_after.rsa_status == AccountRsaStatus.CREATING.value

    # <Normal_2>
    # RSA Change
    def test_normal_2(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account_before = Account()
        _account_before.issuer_address = _user_1["address"]
        _account_before.keyfile = _user_1["keyfile_json"]
        eoa_password = E2EEUtils.encrypt("password")
        _account_before.eoa_password = eoa_password
        _account_before.rsa_private_key = _user_1["rsa_private_key"]
        _account_before.rsa_public_key = _user_1["rsa_public_key"]
        rsa_passphrase = E2EEUtils.encrypt("password")
        _account_before.rsa_passphrase = rsa_passphrase
        _account_before.rsa_status = AccountRsaStatus.SET.value
        db.add(_account_before)
        db.commit()

        _temporary_before = db.query(AccountRsaKeyTemporary).all()

        password = "password_change"
        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt(password)
        }

        resp = client.post(self.base_url.format(_user_1["address"]), json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _user_1["address"],
            "rsa_public_key": _user_1["rsa_public_key"],
            "rsa_status": AccountRsaStatus.CHANGING.value
        }
        _temporary_after = db.query(AccountRsaKeyTemporary).all()
        assert len(_temporary_before) == 0
        assert len(_temporary_after) == 1
        _temporary = _temporary_after[0]
        assert _temporary.issuer_address == _user_1["address"]
        assert _temporary.rsa_private_key == _user_1["rsa_private_key"]
        assert _temporary.rsa_public_key == _user_1["rsa_public_key"]
        assert _temporary.rsa_passphrase == rsa_passphrase
        _account_after = db.query(Account).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.eoa_password == eoa_password
        assert _account_after.rsa_private_key == _user_1["rsa_private_key"]
        assert _account_after.rsa_public_key == _user_1["rsa_public_key"]
        assert E2EEUtils.decrypt(_account_after.rsa_passphrase) == password
        assert _account_after.rsa_status == AccountRsaStatus.CHANGING.value

    # <Normal_3>
    # RSA Create(default passphrase)
    def test_normal_3(self, client, db):
        _user_1 = config_eth_account("user1")

        _account_before = Account()
        _account_before.issuer_address = _user_1["address"]
        _account_before.keyfile = _user_1["keyfile_json"]
        eoa_password = E2EEUtils.encrypt("password")
        _account_before.eoa_password = eoa_password
        _account_before.rsa_status = AccountRsaStatus.UNSET.value
        db.add(_account_before)
        db.commit()

        req_param = {}

        resp = client.post(self.base_url.format(_user_1["address"]), json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _user_1["address"],
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.CREATING.value
        }
        _account_after = db.query(Account).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.eoa_password == eoa_password
        assert _account_after.rsa_private_key is None
        assert _account_after.rsa_public_key is None
        assert E2EEUtils.decrypt(_account_after.rsa_passphrase) == PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE
        assert _account_after.rsa_status == AccountRsaStatus.CREATING.value

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error: no body
    def test_error_1(self, client, db):
        resp = client.post(
            self.base_url.format(ZERO_ADDRESS)
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
                }
            ]
        }

    # <Error_2>
    # Parameter Error: rsa_passphrase
    def test_error_2(self, client, db):
        _user_1 = config_eth_account("user1")

        req_param = {
            "rsa_passphrase": "test"
        }

        resp = client.post(self.base_url.format(_user_1["address"]), json=req_param)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "rsa_passphrase is not a Base64-decoded encrypted data",
                    "type": "value_error"
                }
            ]
        }

    # <Error_3>
    # Not Exists Account
    def test_error_3(self, client, db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.SET.value
        db.add(_account)

        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt("password")
        }

        _user_2 = config_eth_account("user2")
        resp = client.post(self.base_url.format(_user_2["address"]), json=req_param)

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
    # now Generating RSA(CREATING)
    def test_error_4(self, client, db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.CREATING.value
        db.add(_account)

        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt("password")
        }

        resp = client.post(self.base_url.format(_user_1["address"]), json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "RSA key is now generating"
        }

    # <Error_5>
    # now Generating RSA(CHANGING)
    def test_error_5(self, client, db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.CHANGING.value
        db.add(_account)

        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt("password")
        }

        resp = client.post(self.base_url.format(_user_1["address"]), json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "RSA key is now generating"
        }

    # <Error_6>
    # Passphrase Policy Violation
    def test_error_6(self, client, db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.SET.value
        db.add(_account)

        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt("test")
        }

        resp = client.post(self.base_url.format(_user_1["address"]), json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG
        }