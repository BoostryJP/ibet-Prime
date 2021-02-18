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
from app.model.db import Account, AccountRsaKeyTemporary
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
        db.add(_account_before)
        db.commit()

        _temporary_before = db.query(AccountRsaKeyTemporary).all()

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"]
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
        _account_after = db.query(Account).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.rsa_private_key == _user_2["rsa_private_key"]
        assert _account_after.rsa_public_key == _user_2["rsa_public_key"]


    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Not Exists Account
    def test_error_1(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"]
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

    # <Error_2>
    # Now Changing Account
    def test_error_2(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_private_key"]
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

    # <Error_3>
    # Invalid Private Key
    def test_error_3(self, client, db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        db.add(_account)

        req_param = {
            "rsa_private_key": "test"
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

    # <Error_4>
    # Sending Public Key
    def test_error_4(self, client, db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        db.add(_account)

        req_param = {
            "rsa_private_key": _user_2["rsa_public_key"]
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
