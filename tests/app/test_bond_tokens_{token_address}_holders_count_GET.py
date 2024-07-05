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

from app.model.db import (
    Account,
    IDXLockedPosition,
    IDXPosition,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import config_eth_account


class TestAppRoutersBondTokensTokenAddressHoldersCountGET:
    # target API endpoint
    base_url = "/bond/tokens/{}/holders/count"

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
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {"count": 0}

    # <Normal_1_2>
    # position is not None
    # locked_position is None
    def test_normal_1_2(self, client, db):
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
        token.version = TokenVersion.V_24_09
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        db.add(idx_position_1)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {"count": 1}

    # <Normal_1_3>
    # position is not None
    # locked_position is not None
    def test_normal_1_3(self, client, db):
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
        token.version = TokenVersion.V_24_09
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        db.add(idx_position_1)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        db.add(idx_locked_position)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        db.add(idx_locked_position)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {"count": 1}

    # <Normal_1_4>
    # position is not None (but zero)
    # locked_position is not None (but zero)
    def test_normal_1_4(self, client, db):
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
        token.version = TokenVersion.V_24_09
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 0
        idx_position_1.exchange_balance = 0
        idx_position_1.exchange_commitment = 0
        idx_position_1.pending_transfer = 0
        db.add(idx_position_1)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 0
        db.add(idx_locked_position)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {"count": 0}

    # <Normal_2>
    # Multiple records
    def test_normal_2(self, client, db):
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
        token.version = TokenVersion.V_24_09
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.exchange_balance = 11
        idx_position_1.exchange_commitment = 12
        idx_position_1.pending_transfer = 5
        db.add(idx_position_1)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_1
        idx_locked_position.value = 5
        db.add(idx_locked_position)

        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.exchange_balance = 21
        idx_position_2.exchange_commitment = 22
        idx_position_2.pending_transfer = 10
        db.add(idx_position_2)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_2
        idx_locked_position.value = 5
        db.add(idx_locked_position)

        idx_position_3 = IDXPosition()
        idx_position_3.token_address = _token_address
        idx_position_3.account_address = _account_address_3
        idx_position_3.balance = 99
        idx_position_3.exchange_balance = 99
        idx_position_3.exchange_commitment = 99
        idx_position_3.pending_transfer = 99
        db.add(idx_position_3)

        idx_locked_position = IDXLockedPosition()
        idx_locked_position.token_address = _token_address
        idx_locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        idx_locked_position.account_address = _account_address_3
        idx_locked_position.value = 5
        db.add(idx_locked_position)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {"count": 3}

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # issuer-address is not a valid address
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
    # InvalidParameterError
    # issuer does not exist
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
    # NotFound
    # token not found
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
    # InvalidParameterError
    # this token is temporarily unavailable
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
        token.version = TokenVersion.V_24_09
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
