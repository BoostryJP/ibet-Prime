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
from pytz import timezone

from app.model.blockchain import IbetShareContract
from app.model.db import Token, TokenType, TokenVersion
from config import TZ
from tests.account_config import config_eth_account


class TestListAllShareTokens:
    # target API endpoint
    apiurl = "/share/tokens"
    local_tz = timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # parameter unset address, 0 Record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        resp = await async_client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal_2>
    # parameter unset address, 1 Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_2(self, mock_get, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = issuer_address_1
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.version = TokenVersion.V_24_09
        async_db.add(token)
        await async_db.commit()

        _issue_datetime = (
            timezone("UTC")
            .localize(token.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        # request target API
        mock_token = IbetShareContract()
        mock_token.issuer_address = issuer_address_1
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
        mock_token.require_personal_info_registered = True
        mock_token.principal_value = 1000
        mock_token.transfer_approval_required = False
        mock_token.is_canceled = False
        mock_token.memo = "memo_test1"
        mock_get.side_effect = [mock_token]

        resp = await async_client.get(self.apiurl)

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "require_personal_info_registered": True,
                "is_canceled": False,
                "issue_datetime": _issue_datetime,
                "token_status": 1,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_24_09,
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 3>
    # parameter unset address, Multi Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_3(self, mock_get, async_client, async_db):
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
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)
        await async_db.commit()

        _issue_datetime_1 = (
            timezone("UTC")
            .localize(token_1.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_1 = IbetShareContract()
        mock_token_1.issuer_address = issuer_address_1
        mock_token_1.token_address = "token_address_test1"
        mock_token_1.name = "testtoken1"
        mock_token_1.symbol = "test1"
        mock_token_1.total_supply = 10000
        mock_token_1.contact_information = "contactInformation_test1"
        mock_token_1.privacy_policy = "privacyPolicy_test1"
        mock_token_1.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token_1.status = True
        mock_token_1.issue_price = 1000
        mock_token_1.dividends = 123.45
        mock_token_1.dividend_record_date = "20211231"
        mock_token_1.dividend_payment_date = "20211231"
        mock_token_1.cancellation_date = "20221231"
        mock_token_1.transferable = True
        mock_token_1.is_offering = True
        mock_token_1.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token_1.require_personal_info_registered = True
        mock_token_1.principal_value = 1000
        mock_token_1.transfer_approval_required = False
        mock_token_1.is_canceled = False
        mock_token_1.memo = "memo_test1"

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = issuer_address_2
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)
        await async_db.commit()

        _issue_datetime_2 = (
            timezone("UTC")
            .localize(token_2.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_2 = IbetShareContract()
        mock_token_2.issuer_address = issuer_address_2
        mock_token_2.token_address = "token_address_test2"
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 10000
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token_2.status = True
        mock_token_2.issue_price = 1000
        mock_token_2.dividends = 123.45
        mock_token_2.dividend_record_date = "20211231"
        mock_token_2.dividend_payment_date = "20211231"
        mock_token_2.cancellation_date = "20221231"
        mock_token_2.transferable = True
        mock_token_2.is_offering = True
        mock_token_2.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token_2.require_personal_info_registered = False
        mock_token_2.principal_value = 1000
        mock_token_2.transfer_approval_required = False
        mock_token_2.is_canceled = False
        mock_token_2.memo = "memo_test2"

        mock_get.side_effect = [mock_token_1, mock_token_2]

        resp = await async_client.get(self.apiurl)

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "require_personal_info_registered": True,
                "is_canceled": False,
                "issue_datetime": _issue_datetime_1,
                "token_status": 1,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_24_09,
            },
            {
                "issuer_address": issuer_address_2,
                "token_address": "token_address_test2",
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 10000,
                "contact_information": "contactInformation_test2",
                "privacy_policy": "privacyPolicy_test2",
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
                "require_personal_info_registered": False,
                "is_canceled": False,
                "issue_datetime": _issue_datetime_2,
                "token_status": 0,
                "memo": "memo_test2",
                "contract_version": TokenVersion.V_24_09,
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
        # No Target Data
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = "tx_hash_test1"
        token.issuer_address = "issuer_address_test1"
        token.token_address = "token_address_test1"
        token.abi = "abi_test1"
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        resp = await async_client.get(
            self.apiurl, headers={"issuer-address": issuer_address_1}
        )

        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal Case 5>
    # parameter set address, 1 Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_5(self, mock_get, async_client, async_db):
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
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)
        await async_db.commit()
        _issue_datetime = (
            timezone("UTC")
            .localize(token_1.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token = IbetShareContract()
        mock_token.issuer_address = issuer_address_1
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
        mock_token.require_personal_info_registered = True
        mock_token.principal_value = 1000
        mock_token.transfer_approval_required = False
        mock_token.is_canceled = False
        mock_token.memo = "memo_test1"
        mock_get.side_effect = [mock_token]

        # No Target Data
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash_test1"
        token_2.issuer_address = issuer_address_2
        token_2.token_address = "token_address_test1"
        token_2.abi = "abi_test1"
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)

        resp = await async_client.get(
            self.apiurl, headers={"issuer-address": issuer_address_1}
        )

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "require_personal_info_registered": True,
                "is_canceled": False,
                "issue_datetime": _issue_datetime,
                "token_status": 1,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_24_09,
            }
        ]

        assert resp.status_code == 200
        assert resp.json() == assumed_response

    # <Normal Case 6>
    # parameter set address, Multi Record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_6(self, mock_get, async_client, async_db):
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
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)
        await async_db.commit()

        _issue_datetime_1 = (
            timezone("UTC")
            .localize(token_1.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_1 = IbetShareContract()
        mock_token_1.issuer_address = issuer_address_1
        mock_token_1.token_address = "token_address_test1"
        mock_token_1.name = "testtoken1"
        mock_token_1.symbol = "test1"
        mock_token_1.total_supply = 10000
        mock_token_1.contact_information = "contactInformation_test1"
        mock_token_1.privacy_policy = "privacyPolicy_test1"
        mock_token_1.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token_1.status = True
        mock_token_1.issue_price = 1000
        mock_token_1.dividends = 123.45
        mock_token_1.dividend_record_date = "20211231"
        mock_token_1.dividend_payment_date = "20211231"
        mock_token_1.cancellation_date = "20221231"
        mock_token_1.transferable = True
        mock_token_1.is_offering = True
        mock_token_1.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token_1.require_personal_info_registered = True
        mock_token_1.principal_value = 1000
        mock_token_1.transfer_approval_required = False
        mock_token_1.is_canceled = False
        mock_token_1.memo = "memo_test1"

        # 2nd Data
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash_test2"
        token_2.issuer_address = issuer_address_1
        token_2.token_address = "token_address_test2"
        token_2.abi = "abi_test2"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)
        await async_db.commit()

        _issue_datetime_2 = (
            timezone("UTC")
            .localize(token_2.created)
            .astimezone(self.local_tz)
            .isoformat()
        )

        mock_token_2 = IbetShareContract()
        mock_token_2.issuer_address = issuer_address_1
        mock_token_2.token_address = "token_address_test2"
        mock_token_2.name = "testtoken2"
        mock_token_2.symbol = "test2"
        mock_token_2.total_supply = 10000
        mock_token_2.contact_information = "contactInformation_test2"
        mock_token_2.privacy_policy = "privacyPolicy_test2"
        mock_token_2.tradable_exchange_contract_address = (
            "0x1234567890abCdFe1234567890ABCdFE12345678"
        )
        mock_token_2.status = True
        mock_token_2.issue_price = 1000
        mock_token_2.dividends = 123.45
        mock_token_2.dividend_record_date = "20211231"
        mock_token_2.dividend_payment_date = "20211231"
        mock_token_2.cancellation_date = "20221231"
        mock_token_2.transferable = True
        mock_token_2.is_offering = True
        mock_token_2.personal_info_contract_address = (
            "0x1234567890aBcDFE1234567890abcDFE12345679"
        )
        mock_token_2.require_personal_info_registered = True
        mock_token_2.principal_value = 1000
        mock_token_2.transfer_approval_required = False
        mock_token_2.is_canceled = False
        mock_token_2.memo = "memo_test2"

        mock_get.side_effect = [mock_token_1, mock_token_2]

        # No Target Data
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.tx_hash = "tx_hash_test1"
        token_3.issuer_address = issuer_address_2
        token_3.token_address = "token_address_test1"
        token_3.abi = "abi_test1"
        token_3.version = TokenVersion.V_24_09
        async_db.add(token_3)

        resp = await async_client.get(
            self.apiurl, headers={"issuer-address": issuer_address_1}
        )

        assumed_response = [
            {
                "issuer_address": issuer_address_1,
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
                "require_personal_info_registered": True,
                "is_canceled": False,
                "issue_datetime": _issue_datetime_1,
                "token_status": 1,
                "memo": "memo_test1",
                "contract_version": TokenVersion.V_24_09,
            },
            {
                "issuer_address": issuer_address_1,
                "token_address": "token_address_test2",
                "name": "testtoken2",
                "symbol": "test2",
                "total_supply": 10000,
                "principal_value": 1000,
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
                "transfer_approval_required": False,
                "is_offering": True,
                "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
                "require_personal_info_registered": True,
                "is_canceled": False,
                "issue_datetime": _issue_datetime_2,
                "token_status": 0,
                "memo": "memo_test2",
                "contract_version": TokenVersion.V_24_09,
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
