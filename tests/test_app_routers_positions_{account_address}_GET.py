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

from app.model.db import (
    IDXPosition,
    Token,
    TokenType
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract
)


class TestAppRoutersPositionsAccountAddressGET:
    # target API endpoint
    base_url = "/positions/{account_address}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    def test_normal_1(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = "0x1234567890123456789012345678900000000010"
        _position.account_address = "0x1234567890123456789012345678900000000001"  # not target
        _position.balance = 10
        _position.exchange_balance = 11
        _position.exchange_commitment = 12
        _position.pending_transfer = 13
        db.add(_position)

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
            "positions": []
        }

    # <Normal_2>
    # 1 record
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_2(self, mock_IbetStraightBondContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000010",
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                },
            ]
        }

    # <Normal_3>
    # multi record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3(self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
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
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000010",
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000101",
                    "token_address": "0x1234567890123456789012345678900000000011",
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_2",
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 23,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000012",
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_name": "test_share_1",
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                },
            ]
        }

    # <Normal_4>
    # specify header
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_4(self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.issuer_address = "0x1234567890123456789012345678900000000101"  # not target
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
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
            headers={"issuer-address": "0x1234567890123456789012345678900000000100"}
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
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000012",
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_name": "test_share_1",
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                },
            ]
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
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

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={"token_type": TokenType.IBET_STRAIGHT_BOND.value}
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
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "balance": 10,
                    "exchange_balance": 11,
                    "exchange_commitment": 12,
                    "pending_transfer": 13,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000101",
                    "token_address": "0x1234567890123456789012345678900000000011",
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_2",
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 23,
                },
            ]
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
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

        # mock
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            params={"token_type": TokenType.IBET_SHARE.value}
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
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_name": "test_share_1",
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                },
            ]
        }

    # <Normal_6>
    # Pagination
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_6(self, mock_IbetStraightBondContract_get, mock_IbetShareContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
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
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
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
            }
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
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_2",
                    "balance": 20,
                    "exchange_balance": 21,
                    "exchange_commitment": 22,
                    "pending_transfer": 23,
                },
                {
                    "issuer_address": "0x1234567890123456789012345678900000000100",
                    "token_address": "0x1234567890123456789012345678900000000012",
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_name": "test_share_1",
                    "balance": 30,
                    "exchange_balance": 31,
                    "exchange_commitment": 32,
                    "pending_transfer": 33,
                },
            ]
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
            }
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
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_1_1>
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
            }
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
                    "loc": ["query", "token_type"],
                    "ctx": {"enum_values": ["IbetStraightBond", "IbetShare"]},
                    "msg": "value is not a valid enumeration member; permitted: 'IbetStraightBond', 'IbetShare'",
                    "type": "type_error.enum"
                },
                {
                    "loc": ["query", "offset"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer"
                },
                {
                    "loc": ["query", "limit"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer"
                },
            ]
        }