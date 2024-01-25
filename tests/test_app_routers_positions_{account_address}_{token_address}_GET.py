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
from unittest import mock

from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import IDXLockedPosition, IDXPosition, Token, TokenType, TokenVersion


class TestAppRoutersPositionsAccountAddressTokenAddressGET:
    # target API endpoint
    base_url = "/positions/{account_address}/{token_address}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # specify header
    # bond token
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_1_1(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = "0x1234567890123456789012345678900000000002"
        _locked_position.account_address = other_account_address  # not to be included
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": issuer_address,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_name": "test_bond_1",
            "balance": 10,
            "exchange_balance": 11,
            "exchange_commitment": 12,
            "pending_transfer": 13,
            "locked": 10,
        }

    # <Normal_1_2>
    # specify header
    # share token
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_1_2(self, mock_IbetShareContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = "0x1234567890123456789012345678900000000002"
        _locked_position.account_address = other_account_address  # not to be included
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": issuer_address,
            "token_address": token_address,
            "token_type": TokenType.IBET_SHARE.value,
            "token_name": "test_share_1",
            "balance": 10,
            "exchange_balance": 11,
            "exchange_commitment": 12,
            "pending_transfer": 13,
            "locked": 10,
        }

    # <Normal_2>
    # not specify header
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_2(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 0
        _position.exchange_balance = 0
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": issuer_address,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_name": "test_bond_1",
            "balance": 0,
            "exchange_balance": 0,
            "exchange_commitment": 12,
            "pending_transfer": 13,
            "locked": 0,
        }

    # <Normal_3_1>
    # position is None, locked position is not None
    # - Data sets that do not normally occur -> locked amount = 0
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3_1(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5  # not zero
        db.add(_locked_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": issuer_address,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_name": "test_bond_1",
            "balance": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
            "pending_transfer": 0,
            "locked": 0,
        }

    # <Normal_3_2>
    # position is not None (but zero), locked position is not None
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3_2(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 0
        _position.exchange_balance = 0
        _position.exchange_commitment = 0
        _position.pending_transfer = 0
        db.add(_position)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": issuer_address,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_name": "test_bond_1",
            "balance": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
            "pending_transfer": 0,
            "locked": 5,
        }

    # <Normal_3_3>
    # position is not None, locked position is None
    # -> locked amount = 0
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3_3(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 5
        _position.exchange_balance = 10
        _position.exchange_commitment = 15
        _position.pending_transfer = 20
        db.add(_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": issuer_address,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_name": "test_bond_1",
            "balance": 5,
            "exchange_balance": 10,
            "exchange_commitment": 15,
            "pending_transfer": 20,
            "locked": 0,
        }

    # <Normal_3_4>
    # position is not None, locked position is not None (but zero)
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3_4(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 5
        _position.exchange_balance = 10
        _position.exchange_commitment = 15
        _position.pending_transfer = 20
        db.add(_position)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 0
        db.add(_locked_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": issuer_address,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_name": "test_bond_1",
            "balance": 5,
            "exchange_balance": 10,
            "exchange_commitment": 15,
            "pending_transfer": 20,
            "locked": 0,
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # header
    def test_error_1(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": "test"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2_1>
    # NotFound: Token
    # not set header
    def test_error_2_1(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_2_2>
    # NotFound: Token
    # set header
    def test_error_2_2(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = (
            "0x1234567890123456789012345678900000000101"  # not target
        )
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_3>
    # InvalidParameterError
    def test_error_3(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.token_status = 0
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(
                account_address=account_address, token_address=token_address
            ),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
