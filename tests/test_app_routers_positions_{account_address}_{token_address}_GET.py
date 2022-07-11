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
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address, token_address=token_address),
            headers={"issuer-address": issuer_address}
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
        }

    # <Normal_1_2>
    # specify header
    # share token
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_1_2(self, mock_IbetShareContract_get, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
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

        # mock
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        mock_IbetShareContract_get.side_effect = [share_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address, token_address=token_address),
            headers={"issuer-address": issuer_address}
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

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address, token_address=token_address),
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
        }

    # <Normal_3_1>
    # No Position (no record)
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
        db.add(_token)

        # prepare data: Position
        _position = IDXPosition()
        _position.token_address = token_address
        _position.account_address = "0x1234567890123456789012345678900000000001"  # not target
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
            self.base_url.format(account_address=account_address, token_address=token_address),
            headers={"issuer-address": issuer_address}
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
        }

    # <Normal_3_2>
    # No Position (record exists but have no balance)
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

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address, token_address=token_address),
            headers={"issuer-address": issuer_address}
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
            self.base_url.format(account_address=account_address, token_address=token_address),
            headers={"issuer-address": "test"}
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

    # <Error_2_1>
    # NotFound: Token
    # not set header
    def test_error_2_1(self, client, db):
        account_address = "0x1234567890123456789012345678900000000000"
        token_address = "0x1234567890123456789012345678900000000010"

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address, token_address=token_address),
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
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
        _token.issuer_address = "0x1234567890123456789012345678900000000101"  # not target
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
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

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address, token_address=token_address),
            headers={"issuer-address": issuer_address}
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
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

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address, token_address=token_address),
            headers={"issuer-address": issuer_address}
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "this token is temporarily unavailable"
        }
