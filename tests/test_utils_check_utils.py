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
import hashlib
from datetime import datetime
from unittest import mock

import pytest
from fastapi import Request

from app.exceptions import AuthorizationError
from app.model.db import (
    Account,
    AuthToken
)
from app.utils.check_utils import check_auth
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestCheckAuth:
    eoa_password = "password"
    auth_token = "test_auth_token"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1_1
    # Authentication by eoa_password(encrypted)
    def test_normal_1_1(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        # test function
        account, decrypted_eoa_password = check_auth(
            request=Request(scope={"type": "http"}),
            db=db,
            issuer_address=test_account["address"],
            eoa_password=E2EEUtils.encrypt(self.eoa_password)
        )

        assert account == _account
        assert decrypted_eoa_password == self.eoa_password

    # Normal_1_2
    # Authentication by eoa_password(not encrypted)
    @mock.patch("app.utils.check_utils.E2EE_REQUEST_ENABLED", False)
    def test_normal_1_2(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        # test function
        account, decrypted_eoa_password = check_auth(
            request=Request(scope={"type": "http"}),
            db=db,
            issuer_address=test_account["address"],
            eoa_password=self.eoa_password
        )

        assert account == _account
        assert decrypted_eoa_password == self.eoa_password

    # Normal_2_1
    # Authentication by auth_token
    # valid duration = 0
    def test_normal_2_1(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        _auth_token = AuthToken()
        _auth_token.issuer_address = test_account["address"]
        _auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        _auth_token.valid_duration = 0
        db.add(_auth_token)

        # test function
        account, decrypted_eoa_password = check_auth(
            request=Request(scope={"type": "http"}),
            db=db,
            issuer_address=test_account["address"],
            auth_token=self.auth_token
        )

        assert account == _account
        assert decrypted_eoa_password == self.eoa_password

    # Normal_2_2
    # Authentication by auth_token
    # valid duration != 0
    def test_normal_2_2(self, freezer, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        _auth_token = AuthToken()
        _auth_token.issuer_address = test_account["address"]
        _auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        _auth_token.usage_start = datetime(2022, 7, 15, 12, 32, 56)  # 2022-07-15 12:34:56 - 120sec
        _auth_token.valid_duration = 120
        db.add(_auth_token)

        # test function
        freezer.move_to('2022-07-15 12:34:56')
        account, decrypted_eoa_password = check_auth(
            request=Request(scope={"type": "http"}),
            db=db,
            issuer_address=test_account["address"],
            auth_token=self.auth_token
        )

        assert account == _account
        assert decrypted_eoa_password == self.eoa_password

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # issuer does not exist
    def test_error_1(self, db):
        test_account = config_eth_account("user1")

        # test function
        with pytest.raises(AuthorizationError):
            check_auth(
                request=Request(scope={"type": "http"}),
                db=db,
                issuer_address=test_account["address"],
                eoa_password=E2EEUtils.encrypt(self.eoa_password)
            )

    # Error_2
    # eoa_password is None and auth_token is None
    def test_error_2(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        # test function
        with pytest.raises(AuthorizationError):
            check_auth(
                request=Request(scope={"type": "http"}),
                db=db,
                issuer_address=test_account["address"]
            )

    # Error_3_1
    # eoa_password is mismatched (encrypted)
    def test_error_3_1(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        # test function
        with pytest.raises(AuthorizationError):
            check_auth(
                request=Request(scope={"type": "http"}),
                db=db,
                issuer_address=test_account["address"],
                eoa_password=E2EEUtils.encrypt("incorrect_password")  # incorrect password
            )

    # Error_3_2
    # eoa_password is mismatched (not encrypted)
    @mock.patch("app.utils.check_utils.E2EE_REQUEST_ENABLED", False)
    def test_error_3_2(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        # test function
        with pytest.raises(AuthorizationError):
            check_auth(
                request=Request(scope={"type": "http"}),
                db=db,
                issuer_address=test_account["address"],
                eoa_password="incorrect_password"  # incorrect password
            )

    # Error_4_1
    # auth_token does not exist
    def test_error_4_1(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        # test function
        with pytest.raises(AuthorizationError):
            check_auth(
                request=Request(scope={"type": "http"}),
                db=db,
                issuer_address=test_account["address"],
                auth_token=self.eoa_password
            )

    # Error_4_2
    # auth_token is mismatched
    def test_error_4_2(self, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        _auth_token = AuthToken()
        _auth_token.issuer_address = test_account["address"]
        _auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        _auth_token.valid_duration = 0
        db.add(_auth_token)

        # test function
        with pytest.raises(AuthorizationError):
            check_auth(
                request=Request(scope={"type": "http"}),
                db=db,
                issuer_address=test_account["address"],
                auth_token="incorrect_token"  # incorrect token
            )

    # Error_4_3
    # auth_token has been expired
    def test_error_4_3(self, freezer, db):
        test_account = config_eth_account("user1")

        # prepare data
        _account = Account()
        _account.issuer_address = test_account["address"]
        _account.keyfile = test_account["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt(self.eoa_password)
        db.add(_account)

        _auth_token = AuthToken()
        _auth_token.issuer_address = test_account["address"]
        _auth_token.auth_token = hashlib.sha256(self.auth_token.encode()).hexdigest()
        _auth_token.usage_start = datetime(2022, 7, 15, 12, 32, 55)  # 2022-07-15 12:34:56 - 121sec
        _auth_token.valid_duration = 120
        db.add(_auth_token)

        # test function
        freezer.move_to('2022-07-15 12:34:56')
        with pytest.raises(AuthorizationError):
            check_auth(
                request=Request(scope={"type": "http"}),
                db=db,
                issuer_address=test_account["address"],
                auth_token=self.auth_token
            )
