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
from unittest.mock import call

from app.model.blockchain import IbetStraightBondContract
from app.model.db import Token, TokenType


class TestAppRoutersBondBondTokensGET:
    # target API endpoint
    apiurl = "/bond/tokens"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal Case 1>
    # parameter unset address, 0 Record
    def test_normal_1(self, client, db):
        resp = client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal Case 2>
    # parameter unset address, 1 Record
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_2(self, mock_get, client, db):
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        db.add(token)

        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = token.issuer_address
        mock_token.token_address = token.token_address
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

        resp = client.get(self.apiurl)

        # assertion mock call arguments
        mock_get.assert_any_call(contract_address=token.token_address)

        assumed_response = [
            {
                "issuer_address": token.issuer_address,
                "token_address": token.token_address,
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

    # <Normal Case 3>
    # parameter unset address, Multi Record
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_3(self, mock_get, client, db):
        # 1st Data
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = "issuer_address_test1"
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        db.add(token_1)

        mock_token_1 = IbetStraightBondContract()
        mock_token_1.issuer_address = token_1.issuer_address
        mock_token_1.token_address = token_1.token_address
        mock_token_1.name = "testtoken1"
        mock_token_1.symbol = "test1"
        mock_token_1.total_supply = 10000
        mock_token_1.image_url = [
            "http://hoge1.test/test1.png",
            "http://hoge2.test/test1.png",
            "http://hoge3.test/test1.png",
        ]
        mock_token_1.contact_information = "contactInformation_test1"
        mock_token_1.privacy_policy = "privacyPolicy_test1"
        mock_token_1.tradable_exchange_contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"
        mock_token_1.status = True
        mock_token_1.face_value = 200
        mock_token_1.redemption_date = "redemptionDate_test1"
        mock_token_1.redemption_value = 40
        mock_token_1.return_date = "returnDate_test1"
        mock_token_1.return_amount = "returnAmount_test1"
        mock_token_1.purpose = "purpose_test1"
        mock_token_1.interest_rate = 0.003
        mock_token_1.transferable = True
        mock_token_1.initial_offering_status = False
        mock_token_1.is_redeemed = False
        mock_token_1.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"
        mock_token_1.interest_payment_date = [
            "interestPaymentDate1_test1", "interestPaymentDate2_test1",
            "interestPaymentDate3_test1", "interestPaymentDate4_test1",
            "interestPaymentDate5_test1", "interestPaymentDate6_test1",
            "interestPaymentDate7_test1", "interestPaymentDate8_test1",
            "interestPaymentDate9_test1", "interestPaymentDate10_test1",
            "interestPaymentDate11_test1", "interestPaymentDate12_test1",
        ]

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = "issuer_address_test2"
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        db.add(token_2)

        mock_token_2 = IbetStraightBondContract()
        mock_token_2.issuer_address = token_2.issuer_address
        mock_token_2.token_address = token_2.token_address
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 50000
        mock_token_2.image_url = [
            "http://hoge1.test/test2.png",
            "http://hoge2.test/test2.png",
            "http://hoge3.test/test2.png",
        ]
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = "0x1234567890AbcdfE1234567890abcdfE12345680"
        mock_token_2.status = True
        mock_token_2.face_value = 600
        mock_token_2.redemption_date = "redemptionDate_test2"
        mock_token_2.redemption_value = 80
        mock_token_2.return_date = "returnDate_test2"
        mock_token_2.return_amount = "returnAmount_test2"
        mock_token_2.purpose = "purpose_test2"
        mock_token_2.interest_rate = 0.007
        mock_token_2.transferable = False
        mock_token_2.initial_offering_status = False
        mock_token_2.is_redeemed = False
        mock_token_2.personal_info_contract_address = "0x1234567890abcdFE1234567890ABcdfE12345681"
        mock_token_2.interest_payment_date = [
            "interestPaymentDate1_test2", "interestPaymentDate2_test2",
            "interestPaymentDate3_test2", "interestPaymentDate4_test2",
            "interestPaymentDate5_test2", "interestPaymentDate6_test2",
            "interestPaymentDate7_test2", "interestPaymentDate8_test2",
            "interestPaymentDate9_test2", "interestPaymentDate10_test2",
            "interestPaymentDate11_test2", "interestPaymentDate12_test2",
        ]

        mock_get.side_effect = [
            mock_token_1, mock_token_2
        ]

        resp = client.get(self.apiurl)

        # assertion mock call arguments
        mock_get.assert_has_calls(
            [call(contract_address=token_1.token_address), call(contract_address=token_2.token_address)])

        assumed_response = [
            {
                "issuer_address": token_1.issuer_address,
                "token_address": token_1.token_address,
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
                "issuer_address": token_2.issuer_address,
                "token_address": token_2.token_address,
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

    # <Normal Case 4>
    # parameter set address, 0 Record
    def test_normal_4(self, client, db):
        # No Target Data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        db.add(token)

        resp = client.get(self.apiurl, headers={"issuer-address": "test"})

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal Case 5>
    # parameter set address, 1 Record
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_5(self, mock_get, client, db):
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = "issuer_address_test1"
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        db.add(token_1)

        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = token_1.issuer_address
        mock_token.token_address = token_1.token_address
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

        # No Target Data
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.tx_hash = "tx_hash_test1"
        token_2.issuer_address = "issuer_address_test2"
        token_2.token_address = "token_address_test1"
        token_2.abi = "abi_test1"
        db.add(token_2)

        resp = client.get(self.apiurl, headers={"issuer-address": "issuer_address_test1"})

        # assertion mock call arguments
        mock_get.assert_any_call(contract_address=token_1.token_address)

        assumed_response = [
            {
                "issuer_address": token_1.issuer_address,
                "token_address": token_1.token_address,
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

    # <Normal Case 6>
    # parameter set address, Multi Record
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    def test_normal_6(self, mock_get, client, db):
        # 1st Data
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = "issuer_address_common"
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        db.add(token_1)

        mock_token_1 = IbetStraightBondContract()
        mock_token_1.issuer_address = token_1.issuer_address
        mock_token_1.token_address = token_1.token_address
        mock_token_1.name = "testtoken1"
        mock_token_1.symbol = "test1"
        mock_token_1.total_supply = 10000
        mock_token_1.image_url = [
            "http://hoge1.test/test1.png",
            "http://hoge2.test/test1.png",
            "http://hoge3.test/test1.png",
        ]
        mock_token_1.contact_information = "contactInformation_test1"
        mock_token_1.privacy_policy = "privacyPolicy_test1"
        mock_token_1.tradable_exchange_contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"
        mock_token_1.status = True
        mock_token_1.face_value = 200
        mock_token_1.redemption_date = "redemptionDate_test1"
        mock_token_1.redemption_value = 40
        mock_token_1.return_date = "returnDate_test1"
        mock_token_1.return_amount = "returnAmount_test1"
        mock_token_1.purpose = "purpose_test1"
        mock_token_1.interest_rate = 0.003
        mock_token_1.transferable = True
        mock_token_1.initial_offering_status = False
        mock_token_1.is_redeemed = False
        mock_token_1.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"
        mock_token_1.interest_payment_date = [
            "interestPaymentDate1_test1", "interestPaymentDate2_test1",
            "interestPaymentDate3_test1", "interestPaymentDate4_test1",
            "interestPaymentDate5_test1", "interestPaymentDate6_test1",
            "interestPaymentDate7_test1", "interestPaymentDate8_test1",
            "interestPaymentDate9_test1", "interestPaymentDate10_test1",
            "interestPaymentDate11_test1", "interestPaymentDate12_test1",
        ]

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = "issuer_address_common"
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        db.add(token_2)

        mock_token_2 = IbetStraightBondContract()
        mock_token_2.issuer_address = token_2.issuer_address
        mock_token_2.token_address = token_2.token_address
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 50000
        mock_token_2.image_url = [
            "http://hoge1.test/test2.png",
            "http://hoge2.test/test2.png",
            "http://hoge3.test/test2.png",
        ]
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = "0x1234567890AbcdfE1234567890abcdfE12345680"
        mock_token_2.status = True
        mock_token_2.face_value = 600
        mock_token_2.redemption_date = "redemptionDate_test2"
        mock_token_2.redemption_value = 80
        mock_token_2.return_date = "returnDate_test2"
        mock_token_2.return_amount = "returnAmount_test2"
        mock_token_2.purpose = "purpose_test2"
        mock_token_2.interest_rate = 0.007
        mock_token_2.transferable = False
        mock_token_2.initial_offering_status = False
        mock_token_2.is_redeemed = False
        mock_token_2.personal_info_contract_address = "0x1234567890abcdFE1234567890ABcdfE12345681"
        mock_token_2.interest_payment_date = [
            "interestPaymentDate1_test2", "interestPaymentDate2_test2",
            "interestPaymentDate3_test2", "interestPaymentDate4_test2",
            "interestPaymentDate5_test2", "interestPaymentDate6_test2",
            "interestPaymentDate7_test2", "interestPaymentDate8_test2",
            "interestPaymentDate9_test2", "interestPaymentDate10_test2",
            "interestPaymentDate11_test2", "interestPaymentDate12_test2",
        ]

        mock_get.side_effect = [
            mock_token_1, mock_token_2
        ]

        # No Target Data
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.tx_hash = "tx_hash_test1"
        token_3.issuer_address = "issuer_address_test2"
        token_3.token_address = "token_address_test1"
        token_3.abi = "abi_test1"
        db.add(token_3)

        resp = client.get(self.apiurl, headers={"issuer-address": "issuer_address_common"})

        # assertion mock call arguments
        mock_get.assert_has_calls(
            [call(contract_address=token_1.token_address), call(contract_address=token_2.token_address)])

        assumed_response = [
            {
                "issuer_address": "issuer_address_common",
                "token_address": token_1.token_address,
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
                "issuer_address": "issuer_address_common",
                "token_address": token_2.token_address,
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
    # Error Case
    ###########################################################################