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
from datetime import datetime

from app.model.db import (
    Account,
    IDXLockedPosition,
    IDXPersonalInfo,
    IDXPosition,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import config_eth_account


class TestAppRoutersBondTokensTokenAddressHoldersAccountAddressGET:
    # target API endpoint
    base_url = "/bond/tokens/{}/holders/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # position is None
    # locked_position is None
    def test_normal_1_1(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        # prepare data: Token
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        # prepare data: Personal Info
        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = _account_address_1
        idx_personal_info_1.issuer_address = _issuer_address
        idx_personal_info_1.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(idx_personal_info_1)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": _account_address_1,
            "personal_information": {
                "key_manager": "key_manager_test1",
                "name": "name_test1",
                "postal_code": "postal_code_test1",
                "address": "address_test1",
                "email": "email_test1",
                "birth": "birth_test1",
                "is_corporate": False,
                "tax_category": 10,
            },
            "balance": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
            "pending_transfer": 0,
            "locked": 0,
            "modified": None,
        }

    # <Normal_1_2>
    # position is not None
    # locked_position is None
    def test_normal_1_2(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data: Account
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        # prepare data: Token
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        # prepare data: Position
        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        # prepare data: Personal Info
        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = _account_address_1
        idx_personal_info_1.issuer_address = _issuer_address
        idx_personal_info_1.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(idx_personal_info_1)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": _account_address_1,
            "personal_information": {
                "key_manager": "key_manager_test1",
                "name": "name_test1",
                "postal_code": "postal_code_test1",
                "address": "address_test1",
                "email": "email_test1",
                "birth": "birth_test1",
                "is_corporate": False,
                "tax_category": 10,
            },
            "balance": 10,
            "exchange_balance": 11,
            "exchange_commitment": 12,
            "pending_transfer": 5,
            "locked": 0,
            "modified": "2023-10-24T00:00:00",
        }

    # <Normal_1_3>
    # position is not None
    # locked_position is not None
    def test_normal_1_3(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data: Account
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        # prepare data: Token
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        # prepare data: Position
        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = _token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = _account_address_1
        _locked_position.value = 5
        _locked_position.modified = datetime(2023, 10, 24, 0, 1, 0)
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = _token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = _account_address_1
        _locked_position.value = 5
        _locked_position.modified = datetime(2023, 10, 24, 0, 2, 0)
        db.add(_locked_position)

        # prepare data: Personal Info
        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = _account_address_1
        idx_personal_info_1.issuer_address = _issuer_address
        idx_personal_info_1.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(idx_personal_info_1)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": _account_address_1,
            "personal_information": {
                "key_manager": "key_manager_test1",
                "name": "name_test1",
                "postal_code": "postal_code_test1",
                "address": "address_test1",
                "email": "email_test1",
                "birth": "birth_test1",
                "is_corporate": False,
                "tax_category": 10,
            },
            "balance": 10,
            "exchange_balance": 11,
            "exchange_commitment": 12,
            "pending_transfer": 5,
            "locked": 10,
            "modified": "2023-10-24T00:02:00",
        }

    # <Normal_2_1>
    # PersonalInfo not registry
    def test_normal_2_1(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": _account_address_1,
            "personal_information": {
                "key_manager": None,
                "name": None,
                "postal_code": None,
                "address": None,
                "email": None,
                "birth": None,
                "is_corporate": None,
                "tax_category": None,
            },
            "balance": 10,
            "exchange_balance": 11,
            "exchange_commitment": 12,
            "pending_transfer": 5,
            "locked": 0,
            "modified": "2023-10-24T00:00:00",
        }

    # <Normal_2_2>
    # PersonalInfo is partially registered
    def test_normal_2_2(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = _account_address_1
        idx_personal_info_1.issuer_address = _issuer_address
        idx_personal_info_1.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
            # PersonalInfo is partially registered.
        }
        db.add(idx_personal_info_1)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": _account_address_1,
            "personal_information": {
                "key_manager": "key_manager_test1",
                "name": "name_test1",
                "postal_code": "postal_code_test1",
                "address": "address_test1",
                "email": "email_test1",
                "birth": "birth_test1",
                "is_corporate": None,
                "tax_category": None,
            },
            "balance": 10,
            "exchange_balance": 11,
            "exchange_commitment": 12,
            "pending_transfer": 5,
            "locked": 0,
            "modified": "2023-10-24T00:00:00",
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    def test_error_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": "0x0"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "0x0",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2>
    # InvalidParameterError: issuer does not exist
    def test_error_2(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "issuer does not exist",
        }

    # <Error_3>
    # HTTPException 404: token not found
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_4>
    # InvalidParameterError: processing token
    def test_error_4(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        token.version = TokenVersion.V_23_12
        db.add(token)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, _account_address_1),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
