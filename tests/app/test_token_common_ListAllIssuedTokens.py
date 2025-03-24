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

import pytest

from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import Token, TokenType, TokenVersion


class TestListAllIssuedTokens:
    # API endpoint
    api_url = "/tokens"

    issuer_address_1 = "0x1234567890123456789012345678900000000100"
    issuer_address_2 = "0x1234567890123456789012345678900000000200"
    issuer_address_3 = "0x1234567890123456789012345678900000000300"

    token_address_1 = "0x1234567890123456789012345678900000000010"
    token_address_2 = "0x1234567890123456789012345678900000000020"
    token_address_3 = "0x1234567890123456789012345678900000000030"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(self.api_url)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0,
            },
            "tokens": [],
        }

    # <Normal_2_1>
    # TokenType = IbetStraightBond
    @pytest.mark.freeze_time("2025-01-31 12:34:56")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_2_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)
        await async_db.commit()

        # Mock
        bond_1 = IbetStraightBondContract()
        token_attr = {
            "issuer_address": self.issuer_address_1,
            "token_address": self.token_address_1,
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

        # Request target API
        resp = await async_client.get(self.api_url)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_1,
                    "token_address": self.token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": "2025-01-31T21:34:56+09:00",
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": token_attr,
                }
            ],
        }

    # <Normal_2_2>
    # TokenType = IbetShare
    @pytest.mark.freeze_time("2025-01-31 12:34:56")
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_2_2(self, mock_IbetShareContract_get, async_client, async_db):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)
        await async_db.commit()

        # Mock
        share_1 = IbetShareContract()
        token_attr = {
            "issuer_address": self.issuer_address_1,
            "token_address": self.token_address_1,
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

        # Request target API
        resp = await async_client.get(self.api_url)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_1,
                    "token_address": self.token_address_1,
                    "token_type": TokenType.IBET_SHARE,
                    "created": "2025-01-31T21:34:56+09:00",
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": token_attr,
                }
            ],
        }

    # <Normal_3>
    # Multiple records
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_3(
        self,
        mock_IbetShareContract_get,
        mock_IbetStraightBondContract_get,
        async_client,
        async_db,
    ):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address_2
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # Mock
        bond_1 = IbetStraightBondContract()
        bond_token_attr = {
            "issuer_address": self.issuer_address_1,
            "token_address": self.token_address_1,
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
        bond_1.__dict__ = bond_token_attr
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        share_1 = IbetShareContract()
        share_token_attr = {
            "issuer_address": self.issuer_address_2,
            "token_address": self.token_address_2,
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
        share_1.__dict__ = share_token_attr
        mock_IbetShareContract_get.side_effect = [share_1]

        # Request target API
        resp = await async_client.get(self.api_url)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_2,
                    "token_address": self.token_address_2,
                    "token_type": TokenType.IBET_SHARE,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": share_token_attr,
                },
                {
                    "issuer_address": self.issuer_address_1,
                    "token_address": self.token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_token_attr,
                },
            ],
        }

    # <Normal_4_1>
    # Base query filtering: issuer address
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_4_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address_2
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # Mock
        bond_1 = IbetStraightBondContract()
        bond_1_attr = {
            "issuer_address": self.issuer_address_1,
            "token_address": self.token_address_1,
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
        bond_1.__dict__ = bond_1_attr
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # Request target API
        resp = await async_client.get(
            self.api_url,
            headers={"issuer-address": self.issuer_address_1},
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_1,
                    "token_address": self.token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_1_attr,
                }
            ],
        }

    # <Normal_4_2>
    # Base query filtering: token_address_list
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_4_2(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address_2
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # Mock
        bond_2 = IbetStraightBondContract()
        bond_2_attr = {
            "issuer_address": self.issuer_address_2,
            "token_address": self.token_address_2,
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
        bond_2.__dict__ = bond_2_attr
        mock_IbetStraightBondContract_get.side_effect = [bond_2]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"token_address_list": [self.token_address_2]}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_2,
                    "token_address": self.token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_2_attr,
                }
            ],
        }

    # <Normal_5>
    # Search filtering: token_type
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_5(self, mock_IbetShareContract_get, async_client, async_db):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address_2
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # Mock
        share_1 = IbetShareContract()
        share_token_attr = {
            "issuer_address": self.issuer_address_2,
            "token_address": self.token_address_2,
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
        share_1.__dict__ = share_token_attr
        mock_IbetShareContract_get.side_effect = [share_1]

        # Request target API
        resp = await async_client.get(self.api_url, params={"token_type": "IbetShare"})

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_2,
                    "token_address": self.token_address_2,
                    "token_type": TokenType.IBET_SHARE,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": share_token_attr,
                },
            ],
        }

    # <Normal_6_1>
    # Sort: created
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_6_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address_2
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # Mock
        bond_1 = IbetStraightBondContract()
        bond_1_attr = {
            "issuer_address": self.issuer_address_1,
            "token_address": self.token_address_1,
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
        bond_1.__dict__ = bond_1_attr

        bond_2 = IbetStraightBondContract()
        bond_2_attr = {
            "issuer_address": self.issuer_address_2,
            "token_address": self.token_address_2,
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
        bond_2.__dict__ = bond_2_attr

        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"sort_item": "created", "sort_order": 0}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_1,
                    "token_address": self.token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_1_attr,
                },
                {
                    "issuer_address": self.issuer_address_2,
                    "token_address": self.token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_2_attr,
                },
            ],
        }

    # <Normal_6_2>
    # Sort: token_address
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_6_2(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address_2
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # Mock
        bond_1 = IbetStraightBondContract()
        bond_1_attr = {
            "issuer_address": self.issuer_address_1,
            "token_address": self.token_address_1,
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
        bond_1.__dict__ = bond_1_attr

        bond_2 = IbetStraightBondContract()
        bond_2_attr = {
            "issuer_address": self.issuer_address_2,
            "token_address": self.token_address_2,
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
        bond_2.__dict__ = bond_2_attr

        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_2]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"sort_item": "token_address", "sort_order": 0}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 2,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_1,
                    "token_address": self.token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_1_attr,
                },
                {
                    "issuer_address": self.issuer_address_2,
                    "token_address": self.token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_2_attr,
                },
            ],
        }

    # <Normal_7>
    # Offset/Limit
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_7(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        # Prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address_1
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address_2
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        _token = Token()
        _token.token_address = self.token_address_3
        _token.issuer_address = self.issuer_address_3
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # Mock
        bond_2 = IbetStraightBondContract()
        bond_2_attr = {
            "issuer_address": self.issuer_address_2,
            "token_address": self.token_address_2,
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
        bond_2.__dict__ = bond_2_attr

        mock_IbetStraightBondContract_get.side_effect = [bond_2]

        # Request target API
        resp = await async_client.get(self.api_url, params={"offset": 1, "limit": 1})

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 3,
                "offset": 1,
                "limit": 1,
                "total": 3,
            },
            "tokens": [
                {
                    "issuer_address": self.issuer_address_2,
                    "token_address": self.token_address_2,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "created": mock.ANY,
                    "token_status": 1,
                    "contract_version": "24_09",
                    "token_attributes": bond_2_attr,
                }
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1_1>
    # token_address_list: Invalid token address
    # -> 422: RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.api_url, params={"token_address_list": ["invalid_token_address"]}
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["query", "token_address_list", 0],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_token_address",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_1_2>
    # token_type: Invalid token address
    # -> 422: RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.api_url, params={"token_type": "invalid_token_type"}
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["query", "token_type"],
                    "msg": "Input should be 'IbetStraightBond' or 'IbetShare'",
                    "input": "invalid_token_type",
                    "ctx": {"expected": "'IbetStraightBond' or 'IbetShare'"},
                }
            ],
        }
