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

from app.model.blockchain import IbetStraightBondContract
from app.model.db import Token, TokenType, TokenVersion
from config import TZ


class TestRetrieveBondToken:
    # target API endpoint
    base_apiurl = "/bond/tokens/"
    local_tz = pytz.timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # not exist Additional info
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_1(self, mock_get, async_client, async_db):
        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
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

        # request target API
        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = "issuer_address_test1"
        mock_token.token_address = "token_address_test1"
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

        mock_get.side_effect = [mock_token]

        resp = await async_client.get(self.base_apiurl + "token_address_test1")

        # assertion
        assumed_response = {
            "issuer_address": "issuer_address_test1",
            "token_address": "token_address_test1",
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

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal_2>
    # exist Additional info
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_2(self, mock_get, async_client, async_db):
        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
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

        # request target API
        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = "issuer_address_test1"
        mock_token.token_address = "token_address_test1"
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

        mock_get.side_effect = [mock_token]

        resp = await async_client.get(self.base_apiurl + "token_address_test1")

        # assertion
        assumed_response = {
            "issuer_address": "issuer_address_test1",
            "token_address": "token_address_test1",
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

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # No data
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        resp = await async_client.get(self.base_apiurl + "not_found_token_address")

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_2>
    # Processing Token
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.token_status = 0
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        resp = await async_client.get(self.base_apiurl + "token_address_test1")

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
