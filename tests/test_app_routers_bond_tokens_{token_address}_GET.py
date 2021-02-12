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

from app.model.blockchain import IbetStraightBondContract


class TestAppRoutersBondBondTokenGET:
    # target API endpoint
    base_apiurl = "/bond/tokens/"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal Case 1>
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_1(self, mock_get, client):
        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = "issuer_address_test1"
        mock_token.token_address = "token_address_test1"
        mock_token.name = "testtoken1"
        mock_token.symbol = "test1"
        mock_token.total_supply = 10000
        mock_token.image_url = [
            "http://hoge1.test/test1.png",
            "http://hoge2.test/test1.png",
            "http://hoge3.test/test1.png",
        ]
        mock_token.contact_information = "contactInformation_test1"
        mock_token.privacy_policy = "privacyPolicy_test1"
        mock_token.tradable_exchange_contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"
        mock_token.status = True
        mock_token.face_value = 200
        mock_token.redemption_date = "redemptionDate_test1"
        mock_token.redemption_value = 40
        mock_token.return_date = "returnDate_test1"
        mock_token.return_amount = "returnAmount_test1"
        mock_token.purpose = "purpose_test1"
        mock_token.interest_rate = 0.003
        mock_token.transferable = True
        mock_token.initial_offering_status = False
        mock_token.is_redeemed = False
        mock_token.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"
        mock_token.interest_payment_date = [
            "interestPaymentDate1_test1", "interestPaymentDate2_test1",
            "interestPaymentDate3_test1", "interestPaymentDate4_test1",
            "interestPaymentDate5_test1", "interestPaymentDate6_test1",
            "interestPaymentDate7_test1", "interestPaymentDate8_test1",
            "interestPaymentDate9_test1", "interestPaymentDate10_test1",
            "interestPaymentDate11_test1", "interestPaymentDate12_test1",
        ]

        mock_get.side_effect = [
            mock_token
        ]

        resp = client.get(self.base_apiurl + "token_address_test1")

        # assertion mock call arguments
        mock_get.assert_any_call(contract_address="token_address_test1")

        assumed_response = {
            "issuer_address": "issuer_address_test1",
            "token_address": "token_address_test1",
            "name": "testtoken1",
            "symbol": "test1",
            "total_supply": 10000,
            "image_url": [
                "http://hoge1.test/test1.png",
                "http://hoge2.test/test1.png",
                "http://hoge3.test/test1.png",
            ],
            "contact_information": "contactInformation_test1",
            "privacy_policy": "privacyPolicy_test1",
            "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
            "status": True,
            "face_value": 200,
            "redemption_date": "redemptionDate_test1",
            "redemption_value": 40,
            "return_date": "returnDate_test1",
            "return_amount": "returnAmount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.003,
            "transferable": True,
            "initial_offering_status": False,
            "is_redeemed": False,
            "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
            "interest_payment_date": [
                "interestPaymentDate1_test1", "interestPaymentDate2_test1",
                "interestPaymentDate3_test1", "interestPaymentDate4_test1",
                "interestPaymentDate5_test1", "interestPaymentDate6_test1",
                "interestPaymentDate7_test1", "interestPaymentDate8_test1",
                "interestPaymentDate9_test1", "interestPaymentDate10_test1",
                "interestPaymentDate11_test1", "interestPaymentDate12_test1",
            ],
        }

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################
