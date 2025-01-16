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
from app.model.db import IDXLockedPosition, Token, TokenType, TokenVersion


class TestAppRoutersLockedPositions:
    # target API endpoint
    base_url = "/positions/{account_address}/lock"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
            "locked_positions": [],
        }

    # Normal_2_1
    # Bond
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_2_1(self, mock_IbetStraightBondContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = lock_address_2
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = other_account_address  # not to be included
        _locked_position.value = 5
        db.add(_locked_position)

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
            "locked_positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "lock_address": lock_address_1,
                    "locked": 5,
                },
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_2",
                    "lock_address": lock_address_2,
                    "locked": 5,
                },
            ],
        }

    # Normal_2_2
    # Share
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_2_2(self, mock_IbetShareContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = lock_address_2
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = other_account_address  # not to be included
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        share_1 = IbetShareContract()
        share_1.name = "test_share_1"
        share_2 = IbetShareContract()
        share_2.name = "test_share_2"
        mock_IbetShareContract_get.side_effect = [share_1, share_2]

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
            "locked_positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_name": "test_share_1",
                    "lock_address": lock_address_1,
                    "locked": 5,
                },
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_2,
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_name": "test_share_2",
                    "lock_address": lock_address_2,
                    "locked": 5,
                },
            ],
        }

    # Normal_3_1
    # Records not subject to extraction
    # Locked position is not None but its value is zero
    def test_normal_3_1(self, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"
        account_address = "0x1234567890123456789012345678900000000000"
        lock_address_1 = "0x1234567890123456789012345678900000000001"
        token_address_1 = "0x1234567890123456789012345678900000000010"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = account_address
        _locked_position.value = 0
        db.add(_locked_position)

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
            "locked_positions": [],
        }

    # Normal_3_2
    # Records not subject to extraction
    # token_status == 2
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3_2(self, mock_IbetStraightBondContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.token_status = 2
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = lock_address_2
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_2]

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
            "locked_positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_2",
                    "lock_address": lock_address_2,
                    "locked": 5,
                },
            ],
        }

    # Normal_4
    # issuer_address is not None
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_4(self, mock_IbetStraightBondContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"
        other_issuer_address = "0x1234567890123456789012345678900000000200"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = other_issuer_address  # other issuer
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = lock_address_2
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = "test_bond_1"
        bond_2 = IbetStraightBondContract()
        bond_2.name = "test_bond_2"
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = client.get(
            self.base_url.format(account_address=account_address),
            headers={"issuer-address": issuer_address},
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
            "locked_positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "lock_address": lock_address_1,
                    "locked": 5,
                },
            ],
        }

    # Normal_5
    # Search filter: token type
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_5(self, mock_IbetStraightBondContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_2
        _locked_position.lock_address = lock_address_2
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
            self.base_url.format(account_address=account_address),
            params={"token_type": TokenType.IBET_STRAIGHT_BOND.value},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "locked_positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "lock_address": lock_address_2,
                    "locked": 5,
                },
            ],
        }

    # Normal_6
    # Pagination
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_6(self, mock_IbetStraightBondContract_get, client, db):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"
        lock_address_3 = "0x1234567890123456789012345678900000000003"

        token_address_1 = "0x1234567890123456789012345678900000000010"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Locked Position
        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_1
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_2
        _locked_position.account_address = account_address
        _locked_position.value = 5
        db.add(_locked_position)

        _locked_position = IDXLockedPosition()
        _locked_position.token_address = token_address_1
        _locked_position.lock_address = lock_address_3
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
            self.base_url.format(account_address=account_address),
            params={"offset": 1, "limit": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 3,
                "offset": 1,
                "limit": 1,
                "total": 3,
            },
            "locked_positions": [
                {
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "token_name": "test_bond_1",
                    "lock_address": lock_address_2,
                    "locked": 5,
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1_1
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

    # Error_1_2
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
