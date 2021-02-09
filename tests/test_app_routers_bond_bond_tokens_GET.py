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
from app.model.db import Token, TokenType

from tests.account_config import eth_account
from tests.contract_module import issue_bond_token


class TestAppRoutersBondBondTokensGET:
    # テスト対象API
    apiurl = "/bond/tokens"

    ###########################################################################
    # 正常系
    ###########################################################################

    # ＜正常系1＞
    # アドレス指定なし、0件
    def test_normal_1(self, client, db):

        resp = client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json() == []

    # ＜正常系2＞
    # アドレス指定なし、1件
    def test_normal_2(self, client, db):
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

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token["tx_hash"]
        token.issuer_address = issuer["account_address"]
        token.token_address = bond_token["address"]
        token.abi = bond_token["abi"]
        db.add(token)

        resp = client.get(self.apiurl)

        assumed_response = [
            {
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
            },
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # ＜正常系3＞
    # アドレス指定なし、複数件
    def test_normal_3(self, client, db):
        issuer = eth_account["issuer"]

        # 1件目
        bond_token_1 = issue_bond_token(issuer, {
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

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_1["tx_hash"]
        token.issuer_address = issuer["account_address"]
        token.token_address = bond_token_1["address"]
        token.abi = bond_token_1["abi"]
        db.add(token)

        # 2件目
        bond_token_2 = issue_bond_token(issuer, {
            "name": "testtoken2",
            "symbol": "test2",
            "totalSupply": 50000,
            "faceValue": 600,
            "redemptionDate": "redemptionDate_test2",
            "redemptionValue": 80,
            "returnDate": "returnDate_test2",
            "returnAmount": "returnAmount_test2",
            "purpose": "purpose_test2",
            "tradableExchange": "0x1234567890AbcdfE1234567890abcdfE12345680",
            "personalInfoAddress": "0x1234567890abcdFE1234567890ABcdfE12345681",
            "contactInformation": "contactInformation_test2",
            "privacyPolicy": "privacyPolicy_test2",
            "imageURL": [
                "http://hoge1.test/test2.png",
                "http://hoge2.test/test2.png",
                "http://hoge3.test/test2.png",
            ],
            "memo": "memo_test2",
            "interestRate": 70,
            "interestPaymentDate1": "interestPaymentDate1_test2",
            "interestPaymentDate2": "interestPaymentDate2_test2",
            "interestPaymentDate3": "interestPaymentDate3_test2",
            "interestPaymentDate4": "interestPaymentDate4_test2",
            "interestPaymentDate5": "interestPaymentDate5_test2",
            "interestPaymentDate6": "interestPaymentDate6_test2",
            "interestPaymentDate7": "interestPaymentDate7_test2",
            "interestPaymentDate8": "interestPaymentDate8_test2",
            "interestPaymentDate9": "interestPaymentDate9_test2",
            "interestPaymentDate10": "interestPaymentDate10_test2",
            "interestPaymentDate11": "interestPaymentDate11_test2",
            "interestPaymentDate12": "interestPaymentDate12_test2",
            "transferable": False
        })

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_2["tx_hash"]
        token.issuer_address = issuer["account_address"]
        token.token_address = bond_token_2["address"]
        token.abi = bond_token_2["abi"]
        db.add(token)

        resp = client.get(self.apiurl)

        assumed_response =[
            {
                "issuer_address": issuer["account_address"],
                "token_address": bond_token_1["address"],
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
            },
            {
                "issuer_address": issuer["account_address"],
                "token_address": bond_token_2["address"],
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 50000,
                "image_url": [
                    "http://hoge1.test/test2.png",
                    "http://hoge2.test/test2.png",
                    "http://hoge3.test/test2.png",
                ],
                "contact_information": "contactInformation_test2",
                "privacy_policy": "privacyPolicy_test2",
                "tradable_exchange_contract_address": "0x1234567890AbcdfE1234567890abcdfE12345680",
                "status": True,
                "face_value": 600,
                "redemption_date": "redemptionDate_test2",
                "redemption_value": 80,
                "return_date": "returnDate_test2",
                "return_amount": "returnAmount_test2",
                "purpose": "purpose_test2",
                "interest_rate": 0.007,
                "transferable": False,
                "initial_offering_status": False,
                "is_redeemed": False,
                "personal_info_contract_address": "0x1234567890abcdFE1234567890ABcdfE12345681",
                "interest_payment_date": [
                    "interestPaymentDate1_test2", "interestPaymentDate2_test2",
                    "interestPaymentDate3_test2", "interestPaymentDate4_test2",
                    "interestPaymentDate5_test2", "interestPaymentDate6_test2",
                    "interestPaymentDate7_test2", "interestPaymentDate8_test2",
                    "interestPaymentDate9_test2", "interestPaymentDate10_test2",
                    "interestPaymentDate11_test2", "interestPaymentDate12_test2",
                ],
            },
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # ＜正常系4＞
    # アドレス指定あり、0件
    def test_normal_4(self, client, db):

        # 対象外データ
        issuer_2 = eth_account["issuer2"]
        bond_token_2 = issue_bond_token(issuer_2, {
            "name": "testtoken1",
            "symbol": "test1",
            "totalSupply": 10000,
            "faceValue": 200,
            "redemptionDate": "redemptionDate_test1",
            "redemptionValue": 40,
            "returnDate": "returnDate_test1",
            "returnAmount": "returnAmount_test1",
            "purpose": "purpose_test1",
        })

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_2["tx_hash"]
        token.issuer_address = issuer_2["account_address"]
        token.token_address = bond_token_2["address"]
        token.abi = bond_token_2["abi"]
        db.add(token)

        resp = client.get(self.apiurl, headers={"issuer-address": "test"})

        assert resp.status_code == 200
        assert resp.json() == []

    # ＜正常系5＞
    # アドレス指定あり、1件
    def test_normal_5(self, client, db):
        issuer_1 = eth_account["issuer"]
        bond_token_1 = issue_bond_token(issuer_1, {
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

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_1["tx_hash"]
        token.issuer_address = issuer_1["account_address"]
        token.token_address = bond_token_1["address"]
        token.abi = bond_token_1["abi"]
        db.add(token)

        # 対象外データ
        issuer_2 = eth_account["issuer2"]
        bond_token_2 = issue_bond_token(issuer_2, {
            "name": "testtoken1",
            "symbol": "test1",
            "totalSupply": 10000,
            "faceValue": 200,
            "redemptionDate": "redemptionDate_test1",
            "redemptionValue": 40,
            "returnDate": "returnDate_test1",
            "returnAmount": "returnAmount_test1",
            "purpose": "purpose_test1",
        })

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_2["tx_hash"]
        token.issuer_address = issuer_2["account_address"]
        token.token_address = bond_token_2["address"]
        token.abi = bond_token_2["abi"]
        db.add(token)

        resp = client.get(self.apiurl, headers={"issuer-address": issuer_1["account_address"]})

        assumed_response =[
            {
                "issuer_address": issuer_1["account_address"],
                "token_address": bond_token_1["address"],
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
            },
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # ＜正常系6＞
    # アドレス指定あり、複数件
    def test_normal_6(self, client, db):
        issuer_1 = eth_account["issuer"]

        # 1件目
        bond_token_1 = issue_bond_token(issuer_1, {
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

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_1["tx_hash"]
        token.issuer_address = issuer_1["account_address"]
        token.token_address = bond_token_1["address"]
        token.abi = bond_token_1["abi"]
        db.add(token)

        # 2件目
        bond_token_2 = issue_bond_token(issuer_1, {
            "name": "testtoken2",
            "symbol": "test2",
            "totalSupply": 50000,
            "faceValue": 600,
            "redemptionDate": "redemptionDate_test2",
            "redemptionValue": 80,
            "returnDate": "returnDate_test2",
            "returnAmount": "returnAmount_test2",
            "purpose": "purpose_test2",
            "tradableExchange": "0x1234567890AbcdfE1234567890abcdfE12345680",
            "personalInfoAddress": "0x1234567890abcdFE1234567890ABcdfE12345681",
            "contactInformation": "contactInformation_test2",
            "privacyPolicy": "privacyPolicy_test2",
            "imageURL": [
                "http://hoge1.test/test2.png",
                "http://hoge2.test/test2.png",
                "http://hoge3.test/test2.png",
            ],
            "memo": "memo_test2",
            "interestRate": 70,
            "interestPaymentDate1": "interestPaymentDate1_test2",
            "interestPaymentDate2": "interestPaymentDate2_test2",
            "interestPaymentDate3": "interestPaymentDate3_test2",
            "interestPaymentDate4": "interestPaymentDate4_test2",
            "interestPaymentDate5": "interestPaymentDate5_test2",
            "interestPaymentDate6": "interestPaymentDate6_test2",
            "interestPaymentDate7": "interestPaymentDate7_test2",
            "interestPaymentDate8": "interestPaymentDate8_test2",
            "interestPaymentDate9": "interestPaymentDate9_test2",
            "interestPaymentDate10": "interestPaymentDate10_test2",
            "interestPaymentDate11": "interestPaymentDate11_test2",
            "interestPaymentDate12": "interestPaymentDate12_test2",
            "transferable": False
        })

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_2["tx_hash"]
        token.issuer_address = issuer_1["account_address"]
        token.token_address = bond_token_2["address"]
        token.abi = bond_token_2["abi"]
        db.add(token)

        # 対象外データ
        issuer_2 = eth_account["issuer2"]
        bond_token_3 = issue_bond_token(issuer_2, {
            "name": "testtoken1",
            "symbol": "test1",
            "totalSupply": 10000,
            "faceValue": 200,
            "redemptionDate": "redemptionDate_test1",
            "redemptionValue": 40,
            "returnDate": "returnDate_test1",
            "returnAmount": "returnAmount_test1",
            "purpose": "purpose_test1",
        })

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = bond_token_3["tx_hash"]
        token.issuer_address = issuer_2["account_address"]
        token.token_address = bond_token_3["address"]
        token.abi = bond_token_3["abi"]
        db.add(token)

        resp = client.get(self.apiurl, headers={"issuer-address": issuer_1["account_address"]})

        assumed_response =[
            {
                "issuer_address": issuer_1["account_address"],
                "token_address": bond_token_1["address"],
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
            },
            {
                "issuer_address": issuer_1["account_address"],
                "token_address": bond_token_2["address"],
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 50000,
                "image_url": [
                    "http://hoge1.test/test2.png",
                    "http://hoge2.test/test2.png",
                    "http://hoge3.test/test2.png",
                ],
                "contact_information": "contactInformation_test2",
                "privacy_policy": "privacyPolicy_test2",
                "tradable_exchange_contract_address": "0x1234567890AbcdfE1234567890abcdfE12345680",
                "status": True,
                "face_value": 600,
                "redemption_date": "redemptionDate_test2",
                "redemption_value": 80,
                "return_date": "returnDate_test2",
                "return_amount": "returnAmount_test2",
                "purpose": "purpose_test2",
                "interest_rate": 0.007,
                "transferable": False,
                "initial_offering_status": False,
                "is_redeemed": False,
                "personal_info_contract_address": "0x1234567890abcdFE1234567890ABcdfE12345681",
                "interest_payment_date": [
                    "interestPaymentDate1_test2", "interestPaymentDate2_test2",
                    "interestPaymentDate3_test2", "interestPaymentDate4_test2",
                    "interestPaymentDate5_test2", "interestPaymentDate6_test2",
                    "interestPaymentDate7_test2", "interestPaymentDate8_test2",
                    "interestPaymentDate9_test2", "interestPaymentDate10_test2",
                    "interestPaymentDate11_test2", "interestPaymentDate12_test2",
                ],
            },
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    ###########################################################################
    # エラー系
    ###########################################################################
