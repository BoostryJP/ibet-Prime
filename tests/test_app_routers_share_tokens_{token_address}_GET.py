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

from pytz import timezone

from app.model.blockchain import IbetShareContract
from app.model.db import Token, TokenType, TokenVersion
from config import TZ


class TestAppRoutersShareTokensTokenAddressGET:
    # target API endpoint
    base_apiurl = "/share/tokens/"
    local_tz = timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # not exist Additional info
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_1(self, mock_get, client, db):
        # prepare data
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.version = TokenVersion.V_22_12
        db.add(token)
        db.commit()

        _issue_time = (
            timezone("UTC")
            .localize(token.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        # request target API
        mock_token = IbetShareContract()
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
        mock_token.issue_price = 1000
        mock_token.dividends = 123.45
        mock_token.dividend_record_date = "20211231"
        mock_token.dividend_payment_date = "20211231"
        mock_token.cancellation_date = "20221231"
        mock_token.transferable = True
        mock_token.is_offering = True
        mock_token.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token.principal_value = 1000
        mock_token.transfer_approval_required = False
        mock_token.is_canceled = False
        mock_token.memo = "memo_test1"
        mock_get.side_effect = [mock_token]

        resp = client.get(self.base_apiurl + "token_address_test1")

        # assertion
        assumed_response = {
            "issuer_address": "issuer_address_test1",
            "token_address": "token_address_test1",
            "name": "testtoken1",
            "symbol": "test1",
            "total_supply": 10000,
            "contact_information": "contactInformation_test1",
            "privacy_policy": "privacyPolicy_test1",
            "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
            "status": True,
            "issue_price": 1000,
            "principal_value": 1000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "transferable": True,
            "transfer_approval_required": False,
            "is_offering": True,
            "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
            "is_canceled": False,
            "issue_datetime": _issue_time,
            "token_status": 1,
            "memo": "memo_test1",
            "contract_version": TokenVersion.V_22_12,
        }

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal_2>
    # exist Additional info
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_2(self, mock_get, client, db):
        # prepare data
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.version = TokenVersion.V_22_12
        db.add(token)
        db.commit()

        _issue_time = (
            timezone("UTC")
            .localize(token.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        # request target API
        mock_token = IbetShareContract()
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
        mock_token.issue_price = 1000
        mock_token.dividends = 123.45
        mock_token.dividend_record_date = "20211231"
        mock_token.dividend_payment_date = "20211231"
        mock_token.cancellation_date = "20221231"
        mock_token.transferable = True
        mock_token.is_offering = True
        mock_token.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token.principal_value = 1000
        mock_token.transfer_approval_required = False
        mock_token.is_canceled = False
        mock_token.memo = "memo_test1"
        mock_get.side_effect = [mock_token]

        resp = client.get(self.base_apiurl + "token_address_test1")

        # assertion
        assumed_response = {
            "issuer_address": "issuer_address_test1",
            "token_address": "token_address_test1",
            "name": "testtoken1",
            "symbol": "test1",
            "total_supply": 10000,
            "contact_information": "contactInformation_test1",
            "privacy_policy": "privacyPolicy_test1",
            "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
            "status": True,
            "issue_price": 1000,
            "principal_value": 1000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "transferable": True,
            "transfer_approval_required": False,
            "is_offering": True,
            "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
            "is_canceled": False,
            "issue_datetime": _issue_time,
            "token_status": 1,
            "memo": "memo_test1",
            "contract_version": TokenVersion.V_22_12,
        }

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # No data
    def test_error_1(self, client, db):
        resp = client.get(self.base_apiurl + "not_found_token_address")

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_2>
    # Processing token
    def test_error_2(self, client, db):
        # prepare data
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.token_status = 0
        token.version = TokenVersion.V_22_12
        db.add(token)

        db.commit()

        resp = client.get(self.base_apiurl + "token_address_test1")

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
