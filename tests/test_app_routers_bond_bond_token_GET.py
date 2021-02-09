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
from tests.account_config import eth_account
from tests.contract_module import issue_bond_token


class TestAppRoutersBondBondTokenGET:
    # テスト対象API
    base_apiurl = "/bond/token/"

    ###########################################################################
    # 正常系
    ###########################################################################

    # ＜正常系1＞
    def test_normal_1(self, client, db):
        issuer = eth_account["issuer"]
        bond_token = issue_bond_token(issuer, {
            "name": "testtoken1",
            "symbol": "test1",
            "totalSupply": 10000,
            "faceValue": 200,
            "redemptionDate": "redemptionDate_test1",
            "redemptionValue": 40,
            "returnDate": "returnDate_test1",
            "returnAmount": "returnAmount_test1",
            "purpose": "purpose_test1",
            "tradableExchange": "0x1234567890abCdFe1234567890ABCdFE12345678",
            "personalInfoAddress": "0x1234567890aBcDFE1234567890abcDFE12345679",
            "contactInformation": "contactInformation_test1",
            "privacyPolicy": "privacyPolicy_test1",
            "imageURL": [
                "http://hoge1.test/test1.png",
                "http://hoge2.test/test1.png",
                "http://hoge3.test/test1.png",
            ],
            "memo": "memo_test1",
            "interestRate": 30,
            "interestPaymentDate1": "interestPaymentDate1_test1",
            "interestPaymentDate2": "interestPaymentDate2_test1",
            "interestPaymentDate3": "interestPaymentDate3_test1",
            "interestPaymentDate4": "interestPaymentDate4_test1",
            "interestPaymentDate5": "interestPaymentDate5_test1",
            "interestPaymentDate6": "interestPaymentDate6_test1",
            "interestPaymentDate7": "interestPaymentDate7_test1",
            "interestPaymentDate8": "interestPaymentDate8_test1",
            "interestPaymentDate9": "interestPaymentDate9_test1",
            "interestPaymentDate10": "interestPaymentDate10_test1",
            "interestPaymentDate11": "interestPaymentDate11_test1",
            "interestPaymentDate12": "interestPaymentDate12_test1",
            "transferable": True
        })

        resp = client.get(self.base_apiurl + bond_token["address"])

        assumed_response = {
            "issuer_address": issuer["account_address"],
            "token_address": bond_token["address"],
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
    # エラー系
    ###########################################################################
