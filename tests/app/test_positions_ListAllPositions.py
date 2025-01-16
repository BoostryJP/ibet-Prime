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
from app.model.db import (
    IDXLockedPosition,
    IDXPosition,
    Token,
    TokenType,
    TokenVersion,
)


class TestListAllPositions:
    # target API endpoint
    base_url = "/positions/{account_address}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    def test_normal_1(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = (
            "0x1234567890123456789012345678900000000001"  # not target
        )
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0,
            },
            "positions": [],
        }

    # <Normal_2>
    # 1 record
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_2(self, mock_IbetStraightBondContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"
        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"
        token_address_1 = "0x1234567890123456789012345678900000000010"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address_1
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
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
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_1",
                    "token_attributes": None,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 10,
                },
            ],
        }

    # <Normal_3_1>
    # multi record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3_1(
        self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"
        account_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"
        token_address_3 = "0x1234567890123456789012345678900000000030"

        # prepare data: Token 1
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position 1
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000010"
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Locked Position 1
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        # prepare data: Token-2
        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position-2
        _position = IDXPosition()
        _position.token_address = token_address_2
        _position.account_address = account_address
        _position.balance = 20
        _position.exchange_balance = 21
        _position.exchange_commitment = 22
        _position.pending_transfer = 23
        db.add(_position)

        # prepare data: Locked Position 2
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 10
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 10
        db.add(_locked_position)

        # prepare data: Token-3
        _token = Token()
        _token.token_address = token_address_3
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position-3
        _position = IDXPosition()
        _position.token_address = token_address_3
        _position.account_address = account_address
        _position.balance = 30
        _position.exchange_balance = 31
        _position.exchange_commitment = 32
        _position.pending_transfer = 33
        db.add(_position)

        # prepare data: Locked Position 3
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_3
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 15
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_3
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 15
        db.add(_locked_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 3,
            },
            "positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_1",
                    "token_attributes": None,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 10,
                },
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_2",
                    "token_attributes": None,
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 23,
                    "locked": 20,
                },
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_3,
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": "test_share_1",
                    "token_attributes": None,
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                    "locked": 30,
                },
            ],
        }

    # <Normal_3_2>
    # multi record (Including former holder)
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3_2(
        self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"
        account_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"
        token_address_3 = "0x1234567890123456789012345678900000000030"

        # prepare data: Token 1
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position 1
        _position = IDXPosition()
        _position.token_address = token_address_1
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Token 2
        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position 2
        _position = IDXPosition()
        _position.token_address = token_address_2
        _position.account_address = account_address
        _position.balance = 0
        _position.exchange_balance = 0
        _position.exchange_commitment = 22
        _position.pending_transfer = 23
        db.add(_position)

        # prepare data: Locked Position 2
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 0
        db.add(_locked_position)

        # prepare data: Token 3
        _token = Token()
        _token.token_address = token_address_3
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position 3
        _position = IDXPosition()
        _position.token_address = token_address_3
        _position.account_address = account_address
        _position.balance = 0
        _position.exchange_balance = 0
        _position.exchange_commitment = 0
        _position.pending_transfer = 0
        db.add(_position)

        # prepare data: Locked Position 3
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_3
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
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_1",
                    "token_attributes": None,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 0,
                },
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_2",
                    "token_attributes": None,
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 22,
                    "pending_transfer": 23,
                    "locked": 0,
                },
            ],
        }

    # <Normal_4>
    # specify header
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_4(
        self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db
    ):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000010"
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000011"
        _token.issuer_address = (
            "0x1234567890123456789012345678900000000101"  # not target
        )
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000011"
        _position.account_address = account_address
        _position.balance = 20
        _position.exchange_balance = 21
        _position.exchange_commitment = 22
        _position.pending_transfer = 23
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000012"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000012"
        _position.account_address = account_address
        _position.balance = 30
        _position.exchange_balance = 31
        _position.exchange_commitment = 32
        _position.pending_transfer = 33
        db.add(_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            headers={"issuer-address": "0x1234567890123456789012345678900000000100"},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "positions": [
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000010",
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_1",
                    "token_attributes": None,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 0,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000012",
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": "test_share_1",
                    "token_attributes": None,
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                    "locked": 0,
                },
            ],
        }

    # <Normal_5_1>
    # Search Filter
    # token_type
    # IbetStraightBond
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_5_1(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000010"
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000011"
        _token.issuer_address = "0x1234567890123456789012345678900000000101"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000011"
        _position.account_address = account_address
        _position.balance = 20
        _position.exchange_balance = 21
        _position.exchange_commitment = 22
        _position.pending_transfer = 23
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000012"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000012"
        _position.account_address = account_address
        _position.balance = 30
        _position.exchange_balance = 31
        _position.exchange_commitment = 32
        _position.pending_transfer = 33
        db.add(_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={"token_type": TokenType.IBET_STRAIGHT_BOND},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 3,
            },
            "positions": [
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000010",
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_1",
                    "token_attributes": None,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 0,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000101",
                    "token_address": "0x1234567890123456789012345678900000000011",
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_2",
                    "token_attributes": None,
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 23,
                    "locked": 0,
                },
            ],
        }

    # <Normal_5_2>
    # Search Filter
    # token_type
    # IbetShare
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_5_2(self, mock_IbetShareContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000010"
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000011"
        _token.issuer_address = "0x1234567890123456789012345678900000000101"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000011"
        _position.account_address = account_address
        _position.balance = 20
        _position.exchange_balance = 21
        _position.exchange_commitment = 22
        _position.pending_transfer = 23
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000012"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000012"
        _position.account_address = account_address
        _position.balance = 30
        _position.exchange_balance = 31
        _position.exchange_commitment = 32
        _position.pending_transfer = 33
        db.add(_position)

        db.commit()

        # mock
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={"token_type": TokenType.IBET_SHARE},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 3,
            },
            "positions": [
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000012",
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": "test_share_1",
                    "token_attributes": None,
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                    "locked": 0,
                },
            ],
        }

    # <Normal_5_3>
    # Search Filter
    # including_former_position
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_5_3(
        self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db
    ):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000010"
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000011"
        _token.issuer_address = "0x1234567890123456789012345678900000000101"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000011"
        _position.account_address = account_address
        _position.balance = 0
        _position.exchange_balance = 0
        _position.exchange_commitment = 0
        _position.pending_transfer = 0
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000012"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000012"
        _position.account_address = account_address
        _position.balance = 30
        _position.exchange_balance = 20
        _position.exchange_commitment = 10
        _position.pending_transfer = 1
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000013"
        _token.issuer_address = "0x1234567890123456789012345678900000000101"
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000013"
        _position.account_address = account_address
        _position.balance = 0
        _position.exchange_balance = 0
        _position.exchange_commitment = 0
        _position.pending_transfer = 0
        db.add(_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        share_2 = IbetShareContract()
        share_2.name = "test_share_2"
        mock_IbetShareContract_get.side_effect = [share_1, share_2]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={"include_former_position": "true"},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "positions": [
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000010",
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_1",
                    "token_attributes": None,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 0,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000101",
                    "token_address": "0x1234567890123456789012345678900000000011",
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_2",
                    "token_attributes": None,
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000012",
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": "test_share_1",
                    "token_attributes": None,
                    "balance": 30,
                    "exchange_balance": 20,
                    "exchange_commitment": 10,
                    "pending_transfer": 1,
                    "locked": 0,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000101",
                    "token_address": "0x1234567890123456789012345678900000000013",
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": "test_share_2",
                    "token_attributes": None,
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "pending_transfer": 0,
                    "locked": 0,
                },
            ],
        }

    # <Normal_6>
    # Pagination
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_6(
        self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db
    ):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000010"
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000011"
        _token.issuer_address = "0x1234567890123456789012345678900000000101"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000011"
        _position.account_address = account_address
        _position.balance = 20
        _position.exchange_balance = 21
        _position.exchange_commitment = 22
        _position.pending_transfer = 23
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000012"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000012"
        _position.account_address = account_address
        _position.balance = 30
        _position.exchange_balance = 31
        _position.exchange_commitment = 32
        _position.pending_transfer = 33
        db.add(_position)

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000013"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000013"
        _position.account_address = account_address
        _position.balance = 40
        _position.exchange_balance = 41
        _position.exchange_commitment = 42
        _position.pending_transfer = 43
        db.add(_position)

        db.commit()

        # mock
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_2]
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={
                "offset": 1,
                "limit": 2,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": 1,
                "limit": 2,
                "total": 4,
            },
            "positions": [
                {
                    "issuer_address": "0x1234567890123456789012345678900000000101",
                    "token_address": "0x1234567890123456789012345678900000000011",
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "test_bond_2",
                    "token_attributes": None,
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 23,
                    "locked": 0,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000012",
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": "test_share_1",
                    "token_attributes": None,
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                    "locked": 0,
                },
            ],
        }

    # <Normal_7_1>
    # include_token_attributes: True
    # - IbetStraightBond
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_7_1(self, mock_IbetStraightBondContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"
        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"
        token_address_1 = "0x1234567890123456789012345678900000000010"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address_1
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = "0x1234567890123456789012345678900000000002"
        _locked_position.account_address = other_account_address  # not to be included
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        token_attr = {
            "issuer_address": issuer_address,
            "token_address": token_address_1,
            "name": "テスト債券-test",
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        bond_1.__dict__ = token_attr
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={"include_token_attributes": True},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": "テスト債券-test",
                    "token_attributes": token_attr,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 10,
                },
            ],
        }

    # <Normal_7_2>
    # include_token_attributes: True
    # - IbetShare
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_7_2(self, mock_IbetShareContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"
        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"
        token_address_1 = "0x1234567890123456789012345678900000000010"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address_1
        _position.account_address = account_address
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000001"  # lock address 1
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = (
            "0x1234567890123456789012345678900000000002"  # lock address 2
        )
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = "0x1234567890123456789012345678900000000002"
        _locked_position.account_address = other_account_address  # not to be included
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        share_1 = IbetShareContract()
        token_attr = {
            "issuer_address": issuer_address,
            "token_address": token_address_1,
            "name": "テスト株式-test",
            "symbol": "TEST-test",
            "total_supply": 999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": False,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "issue_price": 999997,
            "cancellation_date": "99991231",
            "memo": "memo_test",
            "principal_value": 999998,
            "is_canceled": True,
            "dividends": 9.99,
            "dividend_record_date": "99991230",
            "dividend_payment_date": "99991229",
        }
        share_1.__dict__ = token_attr
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={"include_token_attributes": True},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": "テスト株式-test",
                    "token_attributes": token_attr,
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                    "locked": 10,
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError
    # header
    def test_error_1_1(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            headers={
                "issuer-address": "test",
            },
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

    # <Error_1_2>
    # RequestValidationError
    # query(invalid value)
    def test_error_1_2(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={
                "token_type": "test",
                "offset": "test",
                "limit": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                },
                {
                    "ctx": {"expected": "'IbetStraightBond' or 'IbetShare'"},
                    "input": "test",
                    "loc": ["query", "token_type"],
                    "msg": "Input should be 'IbetStraightBond' or 'IbetShare'",
                    "type": "enum",
                },
            ],
        }
