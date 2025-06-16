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
import pytz
from web3.datastructures import AttributeDict

from app.model.blockchain import IbetStraightBondContract
from app.model.db import Token, TokenType, TokenVersion
from config import TZ
from tests.account_config import config_eth_account


class TestListAllBondTokens:
    # target API endpoint
    apiurl = "/bond/tokens"
    local_tz = pytz.timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal Case 1>
    # parameter unset address, 0 Record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        resp = await async_client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal Case 2>
    # parameter unset address, 1 Record
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_2(self, mock_get, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = issuer_address_1
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.version = TokenVersion.V_25_06
        async_db.add(token)
        await async_db.commit()
        _issue_datetime = (
            pytz.timezone("UTC")
            .localize(token.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = token.issuer_address
        mock_token.token_address = token.token_address
        mock_token.name = "testtoken1"
        mock_token.symbol = "test1"
        mock_token.total_supply = 10000
        mock_token.contact_information = "contactInformation_test1"
        mock_token.privacy_policy = "privacyPolicy_test1"
        mock_token.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token.status = True
        mock_token.face_value = 200
        mock_token.face_value_currency = "JPY"
        mock_token.redemption_date = "redemptionDate_test1"
        mock_token.redemption_value = 40
        mock_token.redemption_value_currency = "JPY"
        mock_token.return_date = "returnDate_test1"
        mock_token.return_amount = "returnAmount_test1"
        mock_token.purpose = "purpose_test1"
        mock_token.interest_rate = 0.003
        mock_token.base_fx_rate = 123.456789
        mock_token.transferable = True
        mock_token.is_offering = False
        mock_token.is_redeemed = False
        mock_token.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token.require_personal_info_registered = True
        mock_token.interest_payment_date = [
            "interestPaymentDate1_test1",
            "interestPaymentDate2_test1",
            "interestPaymentDate3_test1",
            "interestPaymentDate4_test1",
            "interestPaymentDate5_test1",
            "interestPaymentDate6_test1",
            "interestPaymentDate7_test1",
            "interestPaymentDate8_test1",
            "interestPaymentDate9_test1",
            "interestPaymentDate10_test1",
            "interestPaymentDate11_test1",
            "interestPaymentDate12_test1",
        ]
        mock_token.interest_payment_currency = "JPY"
        mock_token.transfer_approval_required = True
        mock_token.memo = "memo_test1"

        mock_get.side_effect = [AttributeDict(mock_token.__dict__)]

        resp = await async_client.get(self.apiurl)

        assumed_response = [
            {
                "issuer_address": token.issuer_address,
                "token_address": token.token_address,
                "name": "testtoken1",
                "symbol": "test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "redemptionDate_test1",
                "redemption_value": 40,
                "redemption_value_currency": "JPY",
                "return_date": "returnDate_test1",
                "return_amount": "returnAmount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.003,
                "interest_payment_date": [
                    "interestPaymentDate1_test1",
                    "interestPaymentDate2_test1",
                    "interestPaymentDate3_test1",
                    "interestPaymentDate4_test1",
                    "interestPaymentDate5_test1",
                    "interestPaymentDate6_test1",
                    "interestPaymentDate7_test1",
                    "interestPaymentDate8_test1",
                    "interestPaymentDate9_test1",
                    "interestPaymentDate10_test1",
                    "interestPaymentDate11_test1",
                    "interestPaymentDate12_test1",
                ],
                "interest_payment_currency": "JPY",
                "base_fx_rate": 123.456789,
                "transferable": True,
                "is_redeemed": False,
                "status": True,
                "is_offering": False,
                "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "require_personal_info_registered": True,
                "contact_information": "contactInformation_test1",
                "privacy_policy": "privacyPolicy_test1",
                "issue_datetime": _issue_datetime,
                "token_status": 1,
                "transfer_approval_required": True,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_25_06,
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 3>
    # parameter unset address, Multi Record
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_3(self, mock_get, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        # 1st Data
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)
        await async_db.commit()
        _issue_datetime_1 = (
            pytz.timezone("UTC")
            .localize(token_1.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_1 = IbetStraightBondContract()
        mock_token_1.issuer_address = token_1.issuer_address
        mock_token_1.token_address = token_1.token_address
        mock_token_1.name = "testtoken1"
        mock_token_1.symbol = "test1"
        mock_token_1.total_supply = 10000
        mock_token_1.contact_information = "contactInformation_test1"
        mock_token_1.privacy_policy = "privacyPolicy_test1"
        mock_token_1.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token_1.status = True
        mock_token_1.face_value = 200
        mock_token_1.face_value_currency = "JPY"
        mock_token_1.redemption_date = "redemptionDate_test1"
        mock_token_1.redemption_value = 40
        mock_token_1.redemption_value_currency = "JPY"
        mock_token_1.return_date = "returnDate_test1"
        mock_token_1.return_amount = "returnAmount_test1"
        mock_token_1.purpose = "purpose_test1"
        mock_token_1.interest_rate = 0.003
        mock_token_1.transferable = True
        mock_token_1.is_offering = False
        mock_token_1.is_redeemed = False
        mock_token_1.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token_1.require_personal_info_registered = True
        mock_token_1.interest_payment_date = [
            "interestPaymentDate1_test1",
            "interestPaymentDate2_test1",
            "interestPaymentDate3_test1",
            "interestPaymentDate4_test1",
            "interestPaymentDate5_test1",
            "interestPaymentDate6_test1",
            "interestPaymentDate7_test1",
            "interestPaymentDate8_test1",
            "interestPaymentDate9_test1",
            "interestPaymentDate10_test1",
            "interestPaymentDate11_test1",
            "interestPaymentDate12_test1",
        ]
        mock_token_1.interest_payment_currency = "JPY"
        mock_token_1.base_fx_rate = 123.456789
        mock_token_1.transfer_approval_required = True
        mock_token_1.memo = "memo_test1"

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = issuer_address_2
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)
        await async_db.commit()
        _issue_datetime_2 = (
            pytz.timezone("UTC")
            .localize(token_2.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_2 = IbetStraightBondContract()
        mock_token_2.issuer_address = token_2.issuer_address
        mock_token_2.token_address = token_2.token_address
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 50000
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = (
            "0x1234567890AbcdfE1234567890abcdfE12345680"
        )
        mock_token_2.status = True
        mock_token_2.face_value = 600
        mock_token_2.face_value_currency = "JPY"
        mock_token_2.redemption_date = "redemptionDate_test2"
        mock_token_2.redemption_value = 80
        mock_token_2.redemption_value_currency = "JPY"
        mock_token_2.return_date = "returnDate_test2"
        mock_token_2.return_amount = "returnAmount_test2"
        mock_token_2.purpose = "purpose_test2"
        mock_token_2.interest_rate = 0.007
        mock_token_2.transferable = False
        mock_token_2.is_offering = False
        mock_token_2.is_redeemed = False
        mock_token_2.personal_info_contract_address = (
            "0x1234567890abcdFE1234567890ABcdfE12345681"
        )
        mock_token_2.require_personal_info_registered = False
        mock_token_2.interest_payment_date = [
            "interestPaymentDate1_test2",
            "interestPaymentDate2_test2",
            "interestPaymentDate3_test2",
            "interestPaymentDate4_test2",
            "interestPaymentDate5_test2",
            "interestPaymentDate6_test2",
            "interestPaymentDate7_test2",
            "interestPaymentDate8_test2",
            "interestPaymentDate9_test2",
            "interestPaymentDate10_test2",
            "interestPaymentDate11_test2",
            "interestPaymentDate12_test2",
        ]
        mock_token_2.interest_payment_currency = "JPY"
        mock_token_2.base_fx_rate = 123.456789
        mock_token_2.transfer_approval_required = False
        mock_token_2.memo = "memo_test2"

        mock_get.side_effect = [
            AttributeDict(mock_token_1.__dict__),
            AttributeDict(mock_token_2.__dict__),
        ]

        resp = await async_client.get(self.apiurl)

        assumed_response = [
            {
                "issuer_address": token_1.issuer_address,
                "token_address": token_1.token_address,
                "name": "testtoken1",
                "symbol": "test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "redemptionDate_test1",
                "redemption_value": 40,
                "redemption_value_currency": "JPY",
                "return_date": "returnDate_test1",
                "return_amount": "returnAmount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.003,
                "interest_payment_date": [
                    "interestPaymentDate1_test1",
                    "interestPaymentDate2_test1",
                    "interestPaymentDate3_test1",
                    "interestPaymentDate4_test1",
                    "interestPaymentDate5_test1",
                    "interestPaymentDate6_test1",
                    "interestPaymentDate7_test1",
                    "interestPaymentDate8_test1",
                    "interestPaymentDate9_test1",
                    "interestPaymentDate10_test1",
                    "interestPaymentDate11_test1",
                    "interestPaymentDate12_test1",
                ],
                "interest_payment_currency": "JPY",
                "base_fx_rate": 123.456789,
                "transferable": True,
                "is_redeemed": False,
                "status": True,
                "is_offering": False,
                "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "require_personal_info_registered": True,
                "contact_information": "contactInformation_test1",
                "privacy_policy": "privacyPolicy_test1",
                "issue_datetime": _issue_datetime_1,
                "token_status": 1,
                "transfer_approval_required": True,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_25_06,
            },
            {
                "issuer_address": token_2.issuer_address,
                "token_address": token_2.token_address,
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 50000,
                "face_value": 600,
                "face_value_currency": "JPY",
                "redemption_date": "redemptionDate_test2",
                "redemption_value": 80,
                "redemption_value_currency": "JPY",
                "return_date": "returnDate_test2",
                "return_amount": "returnAmount_test2",
                "purpose": "purpose_test2",
                "interest_rate": 0.007,
                "interest_payment_date": [
                    "interestPaymentDate1_test2",
                    "interestPaymentDate2_test2",
                    "interestPaymentDate3_test2",
                    "interestPaymentDate4_test2",
                    "interestPaymentDate5_test2",
                    "interestPaymentDate6_test2",
                    "interestPaymentDate7_test2",
                    "interestPaymentDate8_test2",
                    "interestPaymentDate9_test2",
                    "interestPaymentDate10_test2",
                    "interestPaymentDate11_test2",
                    "interestPaymentDate12_test2",
                ],
                "interest_payment_currency": "JPY",
                "base_fx_rate": 123.456789,
                "transferable": False,
                "is_redeemed": False,
                "status": True,
                "is_offering": False,
                "tradable_exchange_contract_address": "0x1234567890AbcdfE1234567890abcdfE12345680",
                "personal_info_contract_address": "0x1234567890abcdFE1234567890ABcdfE12345681",
                "require_personal_info_registered": False,
                "contact_information": "contactInformation_test2",
                "privacy_policy": "privacyPolicy_test2",
                "issue_datetime": _issue_datetime_2,
                "token_status": 0,
                "transfer_approval_required": False,
                "memo": "memo_test2",
                "contract_version": TokenVersion.V_25_06,
            },
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 4>
    # parameter set address, 0 Record
    @pytest.mark.asyncio
    async def test_normal_4(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        # No Target Data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = issuer_address_1
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        resp = await async_client.get(
            self.apiurl, headers={"issuer-address": issuer_address_2}
        )

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal Case 5>
    # parameter set address, 1 Record
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_5(self, mock_get, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)
        await async_db.commit()
        _issue_datetime = (
            pytz.timezone("UTC")
            .localize(token_1.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = token_1.issuer_address
        mock_token.token_address = token_1.token_address
        mock_token.name = "testtoken1"
        mock_token.symbol = "test1"
        mock_token.total_supply = 10000
        mock_token.contact_information = "contactInformation_test1"
        mock_token.privacy_policy = "privacyPolicy_test1"
        mock_token.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token.status = True
        mock_token.face_value = 200
        mock_token.face_value_currency = "JPY"
        mock_token.redemption_date = "redemptionDate_test1"
        mock_token.redemption_value = 40
        mock_token.redemption_value_currency = "JPY"
        mock_token.return_date = "returnDate_test1"
        mock_token.return_amount = "returnAmount_test1"
        mock_token.purpose = "purpose_test1"
        mock_token.interest_rate = 0.003
        mock_token.base_fx_rate = 123.456789
        mock_token.transferable = True
        mock_token.is_offering = False
        mock_token.is_redeemed = False
        mock_token.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token.require_personal_info_registered = True
        mock_token.interest_payment_date = [
            "interestPaymentDate1_test1",
            "interestPaymentDate2_test1",
            "interestPaymentDate3_test1",
            "interestPaymentDate4_test1",
            "interestPaymentDate5_test1",
            "interestPaymentDate6_test1",
            "interestPaymentDate7_test1",
            "interestPaymentDate8_test1",
            "interestPaymentDate9_test1",
            "interestPaymentDate10_test1",
            "interestPaymentDate11_test1",
            "interestPaymentDate12_test1",
        ]
        mock_token.interest_payment_currency = "JPY"
        mock_token.transfer_approval_required = True
        mock_token.memo = "memo_test1"

        mock_get.side_effect = [AttributeDict(mock_token.__dict__)]

        # No Target Data
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.tx_hash = "tx_hash_test1"
        token_2.issuer_address = issuer_address_2
        token_2.token_address = "token_address_test1"
        token_2.abi = "abi_test1"
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)

        resp = await async_client.get(
            self.apiurl, headers={"issuer-address": issuer_address_1}
        )

        assumed_response = [
            {
                "issuer_address": token_1.issuer_address,
                "token_address": token_1.token_address,
                "name": "testtoken1",
                "symbol": "test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "redemptionDate_test1",
                "redemption_value": 40,
                "redemption_value_currency": "JPY",
                "return_date": "returnDate_test1",
                "return_amount": "returnAmount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.003,
                "interest_payment_date": [
                    "interestPaymentDate1_test1",
                    "interestPaymentDate2_test1",
                    "interestPaymentDate3_test1",
                    "interestPaymentDate4_test1",
                    "interestPaymentDate5_test1",
                    "interestPaymentDate6_test1",
                    "interestPaymentDate7_test1",
                    "interestPaymentDate8_test1",
                    "interestPaymentDate9_test1",
                    "interestPaymentDate10_test1",
                    "interestPaymentDate11_test1",
                    "interestPaymentDate12_test1",
                ],
                "interest_payment_currency": "JPY",
                "base_fx_rate": 123.456789,
                "transferable": True,
                "is_redeemed": False,
                "status": True,
                "is_offering": False,
                "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "require_personal_info_registered": True,
                "contact_information": "contactInformation_test1",
                "privacy_policy": "privacyPolicy_test1",
                "issue_datetime": _issue_datetime,
                "token_status": 1,
                "transfer_approval_required": True,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_25_06,
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 6>
    # parameter set address, Multi Record
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_6(self, mock_get, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        # 1st Data
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)
        await async_db.commit()
        _issue_datetime_1 = (
            pytz.timezone("UTC")
            .localize(token_1.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_1 = IbetStraightBondContract()
        mock_token_1.issuer_address = token_1.issuer_address
        mock_token_1.token_address = token_1.token_address
        mock_token_1.name = "testtoken1"
        mock_token_1.symbol = "test1"
        mock_token_1.total_supply = 10000
        mock_token_1.contact_information = "contactInformation_test1"
        mock_token_1.privacy_policy = "privacyPolicy_test1"
        mock_token_1.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token_1.status = True
        mock_token_1.face_value = 200
        mock_token_1.face_value_currency = "JPY"
        mock_token_1.redemption_date = "redemptionDate_test1"
        mock_token_1.redemption_value = 40
        mock_token_1.redemption_value_currency = "JPY"
        mock_token_1.return_date = "returnDate_test1"
        mock_token_1.return_amount = "returnAmount_test1"
        mock_token_1.purpose = "purpose_test1"
        mock_token_1.interest_rate = 0.003
        mock_token_1.transferable = True
        mock_token_1.is_offering = False
        mock_token_1.is_redeemed = False
        mock_token_1.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token_1.require_personal_info_registered = True
        mock_token_1.interest_payment_date = [
            "interestPaymentDate1_test1",
            "interestPaymentDate2_test1",
            "interestPaymentDate3_test1",
            "interestPaymentDate4_test1",
            "interestPaymentDate5_test1",
            "interestPaymentDate6_test1",
            "interestPaymentDate7_test1",
            "interestPaymentDate8_test1",
            "interestPaymentDate9_test1",
            "interestPaymentDate10_test1",
            "interestPaymentDate11_test1",
            "interestPaymentDate12_test1",
        ]
        mock_token_1.interest_payment_currency = "JPY"
        mock_token_1.base_fx_rate = 123.456789
        mock_token_1.transfer_approval_required = True
        mock_token_1.memo = "memo_test1"

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = issuer_address_1
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)
        await async_db.commit()
        _issue_datetime_2 = (
            pytz.timezone("UTC")
            .localize(token_2.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_2 = IbetStraightBondContract()
        mock_token_2.issuer_address = token_2.issuer_address
        mock_token_2.token_address = token_2.token_address
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 50000
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = (
            "0x1234567890AbcdfE1234567890abcdfE12345680"
        )
        mock_token_2.status = True
        mock_token_2.face_value = 600
        mock_token_2.face_value_currency = "JPY"
        mock_token_2.redemption_date = "redemptionDate_test2"
        mock_token_2.redemption_value = 80
        mock_token_2.redemption_value_currency = "JPY"
        mock_token_2.return_date = "returnDate_test2"
        mock_token_2.return_amount = "returnAmount_test2"
        mock_token_2.purpose = "purpose_test2"
        mock_token_2.interest_rate = 0.007
        mock_token_2.transferable = False
        mock_token_2.is_offering = False
        mock_token_2.is_redeemed = False
        mock_token_2.personal_info_contract_address = (
            "0x1234567890abcdFE1234567890ABcdfE12345681"
        )
        mock_token_2.require_personal_info_registered = True
        mock_token_2.interest_payment_date = [
            "interestPaymentDate1_test2",
            "interestPaymentDate2_test2",
            "interestPaymentDate3_test2",
            "interestPaymentDate4_test2",
            "interestPaymentDate5_test2",
            "interestPaymentDate6_test2",
            "interestPaymentDate7_test2",
            "interestPaymentDate8_test2",
            "interestPaymentDate9_test2",
            "interestPaymentDate10_test2",
            "interestPaymentDate11_test2",
            "interestPaymentDate12_test2",
        ]
        mock_token_2.interest_payment_currency = "JPY"
        mock_token_2.base_fx_rate = 123.456789
        mock_token_2.transfer_approval_required = False
        mock_token_2.memo = "memo_test2"

        mock_get.side_effect = [
            AttributeDict(mock_token_1.__dict__),
            AttributeDict(mock_token_2.__dict__),
        ]

        # No Target Data
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.tx_hash = "tx_hash_test1"
        token_3.issuer_address = issuer_address_2
        token_3.token_address = "token_address_test1"
        token_3.abi = "abi_test1"
        token_3.version = TokenVersion.V_25_06
        async_db.add(token_3)

        resp = await async_client.get(
            self.apiurl, headers={"issuer-address": issuer_address_1}
        )

        assumed_response = [
            {
                "issuer_address": token_1.issuer_address,
                "token_address": token_1.token_address,
                "name": "testtoken1",
                "symbol": "test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "redemptionDate_test1",
                "redemption_value": 40,
                "redemption_value_currency": "JPY",
                "return_date": "returnDate_test1",
                "return_amount": "returnAmount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.003,
                "interest_payment_date": [
                    "interestPaymentDate1_test1",
                    "interestPaymentDate2_test1",
                    "interestPaymentDate3_test1",
                    "interestPaymentDate4_test1",
                    "interestPaymentDate5_test1",
                    "interestPaymentDate6_test1",
                    "interestPaymentDate7_test1",
                    "interestPaymentDate8_test1",
                    "interestPaymentDate9_test1",
                    "interestPaymentDate10_test1",
                    "interestPaymentDate11_test1",
                    "interestPaymentDate12_test1",
                ],
                "interest_payment_currency": "JPY",
                "base_fx_rate": 123.456789,
                "transferable": True,
                "is_redeemed": False,
                "status": True,
                "is_offering": False,
                "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "require_personal_info_registered": True,
                "contact_information": "contactInformation_test1",
                "privacy_policy": "privacyPolicy_test1",
                "issue_datetime": _issue_datetime_1,
                "token_status": 1,
                "transfer_approval_required": True,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_25_06,
            },
            {
                "issuer_address": token_2.issuer_address,
                "token_address": token_2.token_address,
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 50000,
                "face_value": 600,
                "face_value_currency": "JPY",
                "redemption_date": "redemptionDate_test2",
                "redemption_value": 80,
                "redemption_value_currency": "JPY",
                "return_date": "returnDate_test2",
                "return_amount": "returnAmount_test2",
                "purpose": "purpose_test2",
                "interest_rate": 0.007,
                "interest_payment_date": [
                    "interestPaymentDate1_test2",
                    "interestPaymentDate2_test2",
                    "interestPaymentDate3_test2",
                    "interestPaymentDate4_test2",
                    "interestPaymentDate5_test2",
                    "interestPaymentDate6_test2",
                    "interestPaymentDate7_test2",
                    "interestPaymentDate8_test2",
                    "interestPaymentDate9_test2",
                    "interestPaymentDate10_test2",
                    "interestPaymentDate11_test2",
                    "interestPaymentDate12_test2",
                ],
                "interest_payment_currency": "JPY",
                "base_fx_rate": 123.456789,
                "transferable": False,
                "is_redeemed": False,
                "status": True,
                "is_offering": False,
                "tradable_exchange_contract_address": "0x1234567890AbcdfE1234567890abcdfE12345680",
                "personal_info_contract_address": "0x1234567890abcdFE1234567890ABcdfE12345681",
                "require_personal_info_registered": True,
                "contact_information": "contactInformation_test2",
                "privacy_policy": "privacyPolicy_test2",
                "issue_datetime": _issue_datetime_2,
                "token_status": 0,
                "transfer_approval_required": False,
                "memo": "memo_test2",
                "contract_version": TokenVersion.V_25_06,
            },
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # parameter error
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        resp = await async_client.get(
            self.apiurl, headers={"issuer-address": "issuer_address"}
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "issuer_address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }
