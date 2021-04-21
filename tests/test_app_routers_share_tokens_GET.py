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
from pytz import timezone

from config import TZ
from app.model.blockchain import IbetShareContract
from app.model.db import Token, TokenType
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensGET:
    # target API endpoint
    apiurl = "/share/tokens"
    local_tz = timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # parameter unset address, 0 Record
    def test_normal_1(self, client, db):
        resp = client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal_2>
    # parameter unset address, 1 Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_2(self, mock_get, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = issuer_address_1
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        db.add(token)
        db.commit()
        _issue_datetime = self.local_tz.localize(token.created).isoformat()

        # request target API
        mock_token = IbetShareContract()
        mock_token.issuer_address = issuer_address_1
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
        mock_token.issue_price = 1000
        mock_token.dividends = 123.45
        mock_token.dividend_record_date = "20211231"
        mock_token.dividend_payment_date = "20211231"
        mock_token.cancellation_date = "20221231"
        mock_token.transferable = True
        mock_token.offering_status = True
        mock_token.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"
        mock_get.side_effect = [mock_token]

        resp = client.get(self.apiurl)

        # assertion mock call arguments
        mock_get.assert_any_call(contract_address=token.token_address)

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "issue_price": 1000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "transferable": True,
                "offering_status": True,
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "issue_datetime": _issue_datetime
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 3>
    # parameter unset address, Multi Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_3(self, mock_get, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]
        # 1st Data
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        db.add(token_1)
        db.commit()
        _issue_datetime_1 = self.local_tz.localize(token_1.created).isoformat()

        mock_token_1 = IbetShareContract()
        mock_token_1.issuer_address = issuer_address_1
        mock_token_1.token_address = "token_address_test1"
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
        mock_token_1.issue_price = 1000
        mock_token_1.dividends = 123.45
        mock_token_1.dividend_record_date = "20211231"
        mock_token_1.dividend_payment_date = "20211231"
        mock_token_1.cancellation_date = "20221231"
        mock_token_1.transferable = True
        mock_token_1.offering_status = True
        mock_token_1.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = issuer_address_2
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        db.add(token_2)
        db.commit()
        _issue_datetime_2 = self.local_tz.localize(token_2.created).isoformat()

        mock_token_2 = IbetShareContract()
        mock_token_2.issuer_address = issuer_address_2
        mock_token_2.token_address = "token_address_test2"
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 10000
        mock_token_2.image_url = [
            "http://hoge1.test/test2.png",
            "http://hoge2.test/test2.png",
            "http://hoge3.test/test2.png",
        ]
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"
        mock_token_2.status = True
        mock_token_2.issue_price = 1000
        mock_token_2.dividends = 123.45
        mock_token_2.dividend_record_date = "20211231"
        mock_token_2.dividend_payment_date = "20211231"
        mock_token_2.cancellation_date = "20221231"
        mock_token_2.transferable = True
        mock_token_2.offering_status = True
        mock_token_2.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"

        mock_get.side_effect = [
            mock_token_1, mock_token_2
        ]

        resp = client.get(self.apiurl)

        # assertion mock call arguments
        mock_get.assert_has_calls([
            call(contract_address=token_1.token_address),
            call(contract_address=token_2.token_address)
        ])

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "issue_price": 1000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "transferable": True,
                "offering_status": True,
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "issue_datetime": _issue_datetime_1
            },
            {
                "issuer_address": issuer_address_2,
                "token_address": "token_address_test2",
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 10000,
                "image_url": [
                    "http://hoge1.test/test2.png",
                    "http://hoge2.test/test2.png",
                    "http://hoge3.test/test2.png",
                ],
                "contact_information": "contactInformation_test2",
                "privacy_policy": "privacyPolicy_test2",
                "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
                "status": True,
                "issue_price": 1000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "transferable": True,
                "offering_status": True,
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "issue_datetime": _issue_datetime_2
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 4>
    # parameter set address, 0 Record
    def test_normal_4(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        # No Target Data
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        db.add(token)

        resp = client.get(self.apiurl, headers={"issuer-address": issuer_address_1})

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal Case 5>
    # parameter set address, 1 Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_5(self, mock_get, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        db.add(token_1)
        db.commit()
        _issue_datetime = self.local_tz.localize(token_1.created).isoformat()

        mock_token = IbetShareContract()
        mock_token.issuer_address = issuer_address_1
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
        mock_token.issue_price = 1000
        mock_token.dividends = 123.45
        mock_token.dividend_record_date = "20211231"
        mock_token.dividend_payment_date = "20211231"
        mock_token.cancellation_date = "20221231"
        mock_token.transferable = True
        mock_token.offering_status = True
        mock_token.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"
        mock_get.side_effect = [mock_token]

        # No Target Data
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash_test1"
        token_2.issuer_address = issuer_address_2
        token_2.token_address = "token_address_test1"
        token_2.abi = "abi_test1"
        db.add(token_2)

        resp = client.get(self.apiurl, headers={"issuer-address": issuer_address_1})

        # assertion mock call arguments
        mock_get.assert_any_call(contract_address=token_1.token_address)

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "issue_price": 1000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "transferable": True,
                "offering_status": True,
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "issue_datetime": _issue_datetime
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 6>
    # parameter set address, Multi Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_6(self, mock_get, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]
        # 1st Data
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.tx_hash = "tx_hash_test1"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = "token_address_test1"
        token_1.abi = "abi_test1"
        db.add(token_1)
        db.commit()
        _issue_datetime_1 = self.local_tz.localize(token_1.created).isoformat()

        mock_token_1 = IbetShareContract()
        mock_token_1.issuer_address = issuer_address_1
        mock_token_1.token_address = "token_address_test1"
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
        mock_token_1.issue_price = 1000
        mock_token_1.dividends = 123.45
        mock_token_1.dividend_record_date = "20211231"
        mock_token_1.dividend_payment_date = "20211231"
        mock_token_1.cancellation_date = "20221231"
        mock_token_1.transferable = True
        mock_token_1.offering_status = True
        mock_token_1.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = issuer_address_1
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        db.add(token_2)
        db.commit()
        _issue_datetime_2 = self.local_tz.localize(token_2.created).isoformat()

        mock_token_2 = IbetShareContract()
        mock_token_2.issuer_address = issuer_address_1
        mock_token_2.token_address = "token_address_test2"
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 10000
        mock_token_2.image_url = [
            "http://hoge1.test/test2.png",
            "http://hoge2.test/test2.png",
            "http://hoge3.test/test2.png",
        ]
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"
        mock_token_2.status = True
        mock_token_2.issue_price = 1000
        mock_token_2.dividends = 123.45
        mock_token_2.dividend_record_date = "20211231"
        mock_token_2.dividend_payment_date = "20211231"
        mock_token_2.cancellation_date = "20221231"
        mock_token_2.transferable = True
        mock_token_2.offering_status = True
        mock_token_2.personal_info_contract_address = "0x1234567890aBcDFE1234567890abcDFE12345679"

        mock_get.side_effect = [
            mock_token_1, mock_token_2
        ]

        # No Target Data
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.tx_hash = "tx_hash_test1"
        token_3.issuer_address = issuer_address_2
        token_3.token_address = "token_address_test1"
        token_3.abi = "abi_test1"
        db.add(token_3)

        resp = client.get(self.apiurl, headers={"issuer-address": issuer_address_1})

        # assertion mock call arguments
        mock_get.assert_has_calls([
            call(contract_address=token_1.token_address),
            call(contract_address=token_2.token_address)
        ])

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "issue_price": 1000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "transferable": True,
                "offering_status": True,
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "issue_datetime": _issue_datetime_1
            },
            {
                "issuer_address": issuer_address_1,
                "token_address": "token_address_test2",
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 10000,
                "image_url": [
                    "http://hoge1.test/test2.png",
                    "http://hoge2.test/test2.png",
                    "http://hoge3.test/test2.png",
                ],
                "contact_information": "contactInformation_test2",
                "privacy_policy": "privacyPolicy_test2",
                "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
                "status": True,
                "issue_price": 1000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "transferable": True,
                "offering_status": True,
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "issue_datetime": _issue_datetime_2
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # parameter error
    def test_error_1(self, client, db):
        resp = client.get(self.apiurl, headers={"issuer-address": "issuer_address"})

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }]
        }
