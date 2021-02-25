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
from app.model.db import Account
from app.model.schema.utils import SecureValueUtils
from app.routers.account import generate_rsa_key
from tests.account_config import config_eth_account


class TestAppRoutersAccountsPOST:
    # target API endpoint
    apiurl = "/accounts"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @mock.patch("starlette.background.BackgroundTasks.add_task")
    def test_normal_1(self, mock_add_task, client, db):
        accounts_before = db.query(Account).all()

        req_param = {
            "eoa_password": SecureValueUtils.encrypt("password")  # Not Encrypted
        }

        resp = client.post(self.apiurl, json=req_param)

        # assertion
        assert resp.status_code == 200
        assert resp.json()["issuer_address"] is not None

        accounts_after = db.query(Account).all()

        assert 0 == len(accounts_before)
        assert 1 == len(accounts_after)
        account_1 = accounts_after[0]
        assert account_1.issuer_address == resp.json()["issuer_address"]
        assert account_1.keyfile is not None
        assert account_1.rsa_private_key is None
        assert account_1.rsa_public_key is None
        assert account_1.rsa_encrypt_passphrase is None

        mock_add_task.assert_any_call(generate_rsa_key, db, account_1.issuer_address)

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
                "msg": "eoa_password is not a Base64-decoded encrypted data",
                "type": "value_error"
            }]
        }

    # <Error_2>
    # Invalid Password
    def test_error_2(self, client, db):
        req_param = {
            "eoa_password": SecureValueUtils.encrypt("test")
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

    ###########################################################################
    # Normal Case(BackGroundTask)
    ###########################################################################

    # <Normal_1>
    def test_backgroundtask_normal_1(self, db):
        config_account = config_eth_account("user1")

        account = Account()
        account.issuer_address = config_account["address"]
        account.keyfile = config_account["keyfile_json"]
        db.add(account)

        # Run BackGroundTask
        generate_rsa_key(db, config_account["address"])

        update_account = db.query(Account).first()

        assert update_account.issuer_address == config_account["address"]
        assert update_account.keyfile == config_account["keyfile_json"]
        assert update_account.rsa_private_key is not None
        assert update_account.rsa_public_key is not None
        assert update_account.rsa_encrypt_passphrase is not None

    ###########################################################################
    # Error Case(BackGroundTask)
    ###########################################################################

    # <Error_1>
    # Not Exists Address
    def test_backgroundtask_error_1(self, db):
        config_account = config_eth_account("user1")

        account = Account()
        account.issuer_address = config_account["address"]
        account.keyfile = config_account["keyfile_json"]
        db.add(account)

        # Run BackGroundTask
        generate_rsa_key(db, issuer_address="not_exists_issuer")

        update_account = db.query(Account).first()

        assert update_account.issuer_address == config_account["address"]
        assert update_account.keyfile == config_account["keyfile_json"]
        assert update_account.rsa_private_key is None
        assert update_account.rsa_public_key is None
        assert update_account.rsa_encrypt_passphrase is None
