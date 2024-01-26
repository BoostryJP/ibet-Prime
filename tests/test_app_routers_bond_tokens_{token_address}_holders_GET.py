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


class TestAppRoutersBondTokensTokenAddressHoldersGET:
    # target API endpoint
    base_url = "/bond/tokens/{}/holders"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    def test_normal_1(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

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

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "total": 0, "offset": None, "limit": None},
            "holders": [],
        }

    # <Normal_2>
    # 1 record
    def test_normal_2(self, client, db):
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

        # Other locked position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = "other_token_address"
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = _account_address_1
        _locked_position.value = 5
        _locked_position.modified = datetime(2023, 10, 25, 0, 2, 0)
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

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "total": 1, "offset": None, "limit": None},
            "holders": [
                {
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
            ],
        }

    # <Normal_3_1>
    # Multi record
    def test_normal_3_1(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"
        _account_address_2 = "0x3F198534Bbe3B2a197d3B317d41392F348EAC707"
        _account_address_3 = "0x8277D905F37F8a9717F5718d0daC21495dFE74bf"

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

        # prepare data: account_address_1
        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 10, 0)
        db.add(idx_locked_position)

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

        # prepare data: account_address_2
        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.exchange_balance = 21
        idx_position_2.exchange_commitment = 22
        idx_position_2.pending_transfer = 10
        idx_position_2.modified = datetime(2023, 10, 24, 2, 0, 0)
        db.add(idx_position_2)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 10, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 20, 0)
        db.add(idx_locked_position)

        # prepare data: account_address_3
        idx_position_3 = IDXPosition()
        idx_position_3.token_address = _token_address
        idx_position_3.account_address = _account_address_3
        idx_position_3.balance = 99
        idx_position_3.exchange_balance = 99
        idx_position_3.exchange_commitment = 99
        idx_position_3.pending_transfer = 99
        idx_position_3.modified = datetime(2023, 10, 24, 3, 0, 0)
        db.add(idx_position_3)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 4, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 5, 0, 0)
        db.add(idx_locked_position)

        # Other locked position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = "other_token_address"
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = _account_address_1
        _locked_position.value = 5
        _locked_position.modified = datetime(2023, 10, 25, 0, 2, 0)
        db.add(_locked_position)

        idx_personal_info_3 = IDXPersonalInfo()
        idx_personal_info_3.account_address = _account_address_3
        idx_personal_info_3.issuer_address = _issuer_address
        idx_personal_info_3.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            # PersonalInfo is partially registered.
        }
        db.add(idx_personal_info_3)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "total": 3, "offset": None, "limit": None},
            "holders": [
                {
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
                    "modified": "2023-10-24T01:10:00",
                },
                {
                    "account_address": _account_address_2,
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
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 10,
                    "locked": 20,
                    "modified": "2023-10-24T02:20:00",
                },
                {
                    "account_address": _account_address_3,
                    "personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": "birth_test3",
                        "is_corporate": None,
                        "tax_category": None,
                    },
                    "balance": 99,
                    "exchange_balance": 99,
                    "exchange_commitment": 99,
                    "pending_transfer": 99,
                    "locked": 30,
                    "modified": "2023-10-24T05:00:00",
                },
            ],
        }

    # <Normal_3_2>
    # Multi record (Including former holder)
    # Query param: including_former_holder=None
    def test_normal_3_2(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"
        _account_address_2 = "0x3F198534Bbe3B2a197d3B317d41392F348EAC707"
        _account_address_3 = "0x8277D905F37F8a9717F5718d0daC21495dFE74bf"

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

        # prepare data: account_address_1
        # - Locked position is None
        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 0
        idx_position_1.exchange_balance = 0
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 1, 0, 0)
        db.add(idx_position_1)

        # prepare data: account_address_1
        # - The balance is partially zero.
        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.exchange_balance = 21
        idx_position_2.exchange_commitment = 0
        idx_position_2.pending_transfer = 0
        idx_position_2.modified = datetime(2023, 10, 24, 2, 0, 0)
        db.add(idx_position_2)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 0
        idx_locked_position.modified = datetime(2023, 10, 24, 3, 0, 0)
        db.add(idx_locked_position)

        # prepare data: account_address_1
        # - The balance is zero.
        idx_position_3 = IDXPosition()
        idx_position_3.token_address = _token_address
        idx_position_3.account_address = _account_address_3
        idx_position_3.balance = 0
        idx_position_3.exchange_balance = 0
        idx_position_3.exchange_commitment = 0
        idx_position_3.pending_transfer = 0
        idx_position_3.modified = datetime(2023, 10, 24, 4, 0, 0)
        db.add(idx_position_3)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 0
        idx_locked_position.modified = datetime(2023, 10, 24, 5, 0, 0)
        db.add(idx_locked_position)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        # former holder who has currently no balance is not listed
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "total": 3, "offset": None, "limit": None},
            "holders": [
                {
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
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 12,
                    "pending_transfer": 5,
                    "locked": 0,
                    "modified": "2023-10-24T01:00:00",
                },
                {
                    "account_address": _account_address_2,
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
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "modified": "2023-10-24T03:00:00",
                },
            ],
        }

    # <Normal_3_3>
    # Multi record (Including former holder)
    # Query param: including_former_holder=True
    def test_normal_3_3(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"
        _account_address_2 = "0x3F198534Bbe3B2a197d3B317d41392F348EAC707"
        _account_address_3 = "0x8277D905F37F8a9717F5718d0daC21495dFE74bf"

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
        idx_position_1.balance = 0
        idx_position_1.exchange_balance = 0
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 1, 0, 0)
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
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(idx_personal_info_1)

        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.exchange_balance = 21
        idx_position_2.exchange_commitment = 0
        idx_position_2.pending_transfer = 0
        idx_position_2.modified = datetime(2023, 10, 24, 2, 0, 0)
        db.add(idx_position_2)

        idx_position_3 = IDXPosition()
        idx_position_3.token_address = _token_address
        idx_position_3.account_address = _account_address_3
        idx_position_3.balance = 0
        idx_position_3.exchange_balance = 0
        idx_position_3.exchange_commitment = 0
        idx_position_3.pending_transfer = 0
        idx_position_3.modified = datetime(2023, 10, 24, 3, 0, 0)
        db.add(idx_position_3)

        idx_personal_info_3 = IDXPersonalInfo()
        idx_personal_info_3.account_address = _account_address_3
        idx_personal_info_3.issuer_address = _issuer_address
        idx_personal_info_3.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            # PersonalInfo is partially registered.
        }
        db.add(idx_personal_info_3)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
            params={"include_former_holder": "true"},
        )

        # assertion
        # former holder who has currently no balance is not listed
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "total": 3, "offset": None, "limit": None},
            "holders": [
                {
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
                    "exchange_commitment": 12,
                    "pending_transfer": 5,
                    "locked": 0,
                    "modified": "2023-10-24T01:00:00",
                },
                {
                    "account_address": _account_address_2,
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
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "modified": "2023-10-24T02:00:00",
                },
                {
                    "account_address": _account_address_3,
                    "personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": "birth_test3",
                        "is_corporate": None,
                        "tax_category": None,
                    },
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                    "modified": "2023-10-24T03:00:00",
                },
            ],
        }

    # <Normal_4>
    # Sort Order
    def test_normal_4(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"
        _account_address_2 = "0x3F198534Bbe3B2a197d3B317d41392F348EAC707"
        _account_address_3 = "0x8277D905F37F8a9717F5718d0daC21495dFE74bf"

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

        # prepare data: account_address_1
        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 10, 0)
        db.add(idx_locked_position)

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

        # prepare data: account_address_2
        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.exchange_balance = 21
        idx_position_2.exchange_commitment = 22
        idx_position_2.pending_transfer = 10
        idx_position_2.modified = datetime(2023, 10, 24, 2, 0, 0)
        db.add(idx_position_2)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 10, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 20, 0)
        db.add(idx_locked_position)

        # prepare data: account_address_3
        idx_position_3 = IDXPosition()
        idx_position_3.token_address = _token_address
        idx_position_3.account_address = _account_address_3
        idx_position_3.balance = 99
        idx_position_3.exchange_balance = 99
        idx_position_3.exchange_commitment = 99
        idx_position_3.pending_transfer = 99
        idx_position_3.modified = datetime(2023, 10, 24, 3, 0, 0)
        db.add(idx_position_3)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 4, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 5, 0, 0)
        db.add(idx_locked_position)

        # Other locked position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = "other_token_address"
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = _account_address_1
        _locked_position.value = 5
        _locked_position.modified = datetime(2023, 10, 25, 0, 2, 0)
        db.add(_locked_position)

        idx_personal_info_3 = IDXPersonalInfo()
        idx_personal_info_3.account_address = _account_address_3
        idx_personal_info_3.issuer_address = _issuer_address
        idx_personal_info_3.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            # PersonalInfo is partially registered.
        }
        db.add(idx_personal_info_3)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
            params={"sort_order": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "total": 3, "offset": None, "limit": None},
            "holders": [
                {
                    "account_address": _account_address_3,
                    "personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": "birth_test3",
                        "is_corporate": None,
                        "tax_category": None,
                    },
                    "balance": 99,
                    "exchange_balance": 99,
                    "exchange_commitment": 99,
                    "pending_transfer": 99,
                    "locked": 30,
                    "modified": "2023-10-24T05:00:00",
                },
                {
                    "account_address": _account_address_2,
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
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 10,
                    "locked": 20,
                    "modified": "2023-10-24T02:20:00",
                },
                {
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
                    "modified": "2023-10-24T01:10:00",
                },
            ],
        }

    # <Normal_5_1>
    # Pagination
    def test_normal_5_1(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"
        _account_address_2 = "0x3F198534Bbe3B2a197d3B317d41392F348EAC707"
        _account_address_3 = "0x8277D905F37F8a9717F5718d0daC21495dFE74bf"

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

        # prepare data: account_address_1
        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 10, 0)
        db.add(idx_locked_position)

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

        # prepare data: account_address_2
        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.exchange_balance = 21
        idx_position_2.exchange_commitment = 22
        idx_position_2.pending_transfer = 10
        idx_position_2.modified = datetime(2023, 10, 24, 2, 0, 0)
        db.add(idx_position_2)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 10, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 20, 0)
        db.add(idx_locked_position)

        # prepare data: account_address_3
        idx_position_3 = IDXPosition()
        idx_position_3.token_address = _token_address
        idx_position_3.account_address = _account_address_3
        idx_position_3.balance = 99
        idx_position_3.exchange_balance = 99
        idx_position_3.exchange_commitment = 99
        idx_position_3.pending_transfer = 99
        idx_position_3.modified = datetime(2023, 10, 24, 3, 0, 0)
        db.add(idx_position_3)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 4, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 5, 0, 0)
        db.add(idx_locked_position)

        # Other locked position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = "other_token_address"
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = _account_address_1
        _locked_position.value = 5
        _locked_position.modified = datetime(2023, 10, 25, 0, 2, 0)
        db.add(_locked_position)

        idx_personal_info_3 = IDXPersonalInfo()
        idx_personal_info_3.account_address = _account_address_3
        idx_personal_info_3.issuer_address = _issuer_address
        idx_personal_info_3.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            # PersonalInfo is partially registered.
        }
        db.add(idx_personal_info_3)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
            params={"offset": 1, "limit": 2},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "total": 3, "offset": 1, "limit": 2},
            "holders": [
                {
                    "account_address": _account_address_2,
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
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 10,
                    "locked": 20,
                    "modified": "2023-10-24T02:20:00",
                },
                {
                    "account_address": _account_address_3,
                    "personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": "birth_test3",
                        "is_corporate": None,
                        "tax_category": None,
                    },
                    "balance": 99,
                    "exchange_balance": 99,
                    "exchange_commitment": 99,
                    "pending_transfer": 99,
                    "locked": 30,
                    "modified": "2023-10-24T05:00:00",
                },
            ],
        }

    # <Normal_5_2>
    # Pagination (over offset)
    def test_normal_5_2(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"
        _account_address_2 = "0x3F198534Bbe3B2a197d3B317d41392F348EAC707"
        _account_address_3 = "0x8277D905F37F8a9717F5718d0daC21495dFE74bf"

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

        # prepare data: account_address_1
        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        idx_position_1.modified = datetime(2023, 10, 24, 0, 0, 0)
        db.add(idx_position_1)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        idx_locked_position.modified = datetime(2023, 10, 24, 1, 10, 0)
        db.add(idx_locked_position)

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

        # prepare data: account_address_2
        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.exchange_balance = 21
        idx_position_2.exchange_commitment = 22
        idx_position_2.pending_transfer = 10
        idx_position_2.modified = datetime(2023, 10, 24, 2, 0, 0)
        db.add(idx_position_2)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 10, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 10
        idx_locked_position.modified = datetime(2023, 10, 24, 2, 20, 0)
        db.add(idx_locked_position)

        # prepare data: account_address_3
        idx_position_3 = IDXPosition()
        idx_position_3.token_address = _token_address
        idx_position_3.account_address = _account_address_3
        idx_position_3.balance = 99
        idx_position_3.exchange_balance = 99
        idx_position_3.exchange_commitment = 99
        idx_position_3.pending_transfer = 99
        idx_position_3.modified = datetime(2023, 10, 24, 3, 0, 0)
        db.add(idx_position_3)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 4, 0, 0)
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 15
        idx_locked_position.modified = datetime(2023, 10, 24, 5, 0, 0)
        db.add(idx_locked_position)

        # Other locked position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = "other_token_address"
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = _account_address_1
        _locked_position.value = 5
        _locked_position.modified = datetime(2023, 10, 25, 0, 2, 0)
        db.add(_locked_position)

        idx_personal_info_3 = IDXPersonalInfo()
        idx_personal_info_3.account_address = _account_address_3
        idx_personal_info_3.issuer_address = _issuer_address
        idx_personal_info_3.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            # PersonalInfo is partially registered.
        }
        db.add(idx_personal_info_3)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
            params={"offset": 4, "limit": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "total": 3, "offset": 4, "limit": 1},
            "holders": [],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    def test_error_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address), headers={"issuer-address": "0x0"}
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

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
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

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
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

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
