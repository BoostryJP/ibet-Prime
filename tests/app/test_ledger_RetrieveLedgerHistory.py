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

from datetime import datetime
from unittest import mock
from unittest.mock import call

import pytest

from app.model.blockchain import IbetStraightBondContract
from app.model.db import (
    IDXPersonalInfo,
    Ledger,
    LedgerDataType,
    LedgerDetailsTemplate,
    PersonalInfoDataSource,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import config_eth_account


class TestRetrieveLedgerHistory:
    # target API endpoint
    base_url = "/ledger/{token_address}/history/{ledger_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Set issue-address in the header
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": None,
                            "address": None,
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": True,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 0,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": None,
                            "address": None,
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": True,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_1_2>
    # Do not set issue-address in the header
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 0,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_2>
    # latest_flg = 0 (Get the latest personal info)
    # - ledger detail contains None value in "name" and "value": some_personal_info_not_registered = True
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": None,
                            "address": None,
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": True,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"test1": "a", "test2": "b"},
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"f-test1": "a", "f-test2": "b"},
        ]
        _details_1.data_type = LedgerDataType.IBET_FIN.value
        _details_1.data_source = token_address
        async_db.add(_details_1)

        await async_db.commit()

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 0,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": None,
                            "address": None,
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": True,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_3_1>
    # latest_flg = 1 (Get the latest personal info)
    #   - address_1 has personal info in the DB
    #   - address_2 has no personal info in the DB
    # token.require_personal_info_registered = True
    @pytest.mark.asyncio
    async def test_normal_3_1(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        _idx_personal_info_1 = (
            IDXPersonalInfo()
        )  # Note: account_address_1 has personal information in DB
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": "name_db_1",
            "address": "address_db_1",
        }
        _idx_personal_info_1.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_idx_personal_info_1)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"test1": "a", "test2": "b"},
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"f-test1": "a", "f-test2": "b"},
        ]
        _details_1.data_type = LedgerDataType.IBET_FIN.value
        _details_1.data_source = token_address
        async_db.add(_details_1)

        await async_db.commit()

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token.require_personal_info_registered = True
        token_get_mock = mock.patch(
            "app.model.blockchain.IbetStraightBondContract.get", return_value=token
        )
        personal_get_info_mock = mock.patch(
            "app.model.blockchain.PersonalInfoContract.get_info"
        )

        # request target API
        with (
            token_get_mock,
            personal_get_info_mock as personal_get_info_mock_patch,
        ):
            # Note:
            # account_address_2 has no personal information in the DB
            # and gets information from the contract
            personal_get_info_mock_patch.side_effect = [
                {
                    "name": "name_contract_2",
                    "address": "address_contract_2",
                }
            ]

            resp = await async_client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 1,
                },
                headers={
                    "issuer-address": issuer_address,
                },
            )
            # assertion
            personal_get_info_mock_patch.assert_has_calls(
                [call(account_address=account_address_2, default_value=None)]
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_db_1",
                            "address": "address_db_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_contract_2",
                            "address": "address_contract_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_3_2>
    # latest_flg = 1 (Get the latest personal info)
    #   - address_1 has partial personal info in the DB
    #   - address_2 has no personal info in the DB
    # token.require_personal_info_registered = True
    @pytest.mark.asyncio
    async def test_normal_3_2(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        _idx_personal_info_1 = (
            IDXPersonalInfo()
        )  # Note: account_address_1 has partial personal information in DB
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {"name": "name_test_1", "address": None}
        _idx_personal_info_1.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_idx_personal_info_1)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"test1": "a", "test2": "b"},
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"f-test1": "a", "f-test2": "b"},
        ]
        _details_1.data_type = LedgerDataType.IBET_FIN.value
        _details_1.data_source = token_address
        async_db.add(_details_1)

        await async_db.commit()

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token.require_personal_info_registered = True
        token_get_mock = mock.patch(
            "app.model.blockchain.IbetStraightBondContract.get", return_value=token
        )
        personal_get_info_mock = mock.patch(
            "app.model.blockchain.PersonalInfoContract.get_info"
        )

        # request target API
        with (
            token_get_mock,
            personal_get_info_mock as personal_get_info_mock_patch,
        ):
            # Note:
            # account_address_2 has no personal information in the DB
            # and gets information from the contract
            personal_get_info_mock_patch.side_effect = [
                {
                    "name": "name_contract_2",
                    "address": "address_contract_2",
                }
            ]

            resp = await async_client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 1,
                },
                headers={
                    "issuer-address": issuer_address,
                },
            )
            # assertion
            personal_get_info_mock_patch.assert_has_calls(
                [call(account_address=account_address_2, default_value=None)]
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": None,
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_contract_2",
                            "address": "address_contract_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_3_3>
    # latest_flg = 1 (Get the latest personal info)
    # token.require_personal_info_registered = False
    # Personal information has not been indexed yet
    @pytest.mark.asyncio
    async def test_normal_3_3(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,  # Personal information is set (normally not possible)
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"test1": "a", "test2": "b"},
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"f-test1": "a", "f-test2": "b"},
        ]
        _details_1.data_type = LedgerDataType.IBET_FIN.value
        _details_1.data_source = token_address
        async_db.add(_details_1)

        await async_db.commit()

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token.require_personal_info_registered = False
        token_get_mock = mock.patch(
            "app.model.blockchain.IbetStraightBondContract.get", return_value=token
        )

        # request target API
        with token_get_mock:
            resp = await async_client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 1,
                },
                headers={
                    "issuer-address": issuer_address,
                },
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": None,  # not null -> null
                            "address": None,  # not null -> null
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": True,  # False -> True
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_3_4>
    # latest_flg = 1 (Get the latest personal info)
    #   - address_1 is issuer's address
    @pytest.mark.asyncio
    async def test_normal_3_4(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": issuer_address,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,  # Personal information is set (normally not possible)
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"test1": "a", "test2": "b"},
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"f-test1": "a", "f-test2": "b"},
        ]
        _details_1.data_type = LedgerDataType.IBET_FIN.value
        _details_1.data_source = token_address
        async_db.add(_details_1)

        await async_db.commit()

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token.require_personal_info_registered = False
        token_get_mock = mock.patch(
            "app.model.blockchain.IbetStraightBondContract.get", return_value=token
        )

        # request target API
        with token_get_mock:
            resp = await async_client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 1,
                },
                headers={
                    "issuer-address": issuer_address,
                },
            )

        # assertion
        assert resp.status_code == 200
        assert (
            resp.json()
            == {
                "created": "2022/12/01",
                "token_name": "テスト原簿",
                "currency": "JPY",
                "headers": [
                    {
                        "key": "aaa",
                        "value": "aaa",
                    },
                    {
                        "hoge": "aaaa",
                        "fuga": "bbbb",
                    },
                ],
                "details": [
                    {
                        "token_detail_type": "権利_test_1",
                        "headers": [
                            {
                                "key": "aaa",
                                "value": "aaa",
                            },
                            {"test1": "a", "test2": "b"},
                        ],
                        "data": [
                            {
                                "account_address": issuer_address,
                                "name": None,
                                "address": None,
                                "amount": 10,
                                "price": 20,
                                "balance": 30,
                                "acquisition_date": "2022/12/02",
                            },
                        ],
                        "footers": [
                            {
                                "key": "aaa",
                                "value": "aaa",
                            },
                            {"f-test1": "a", "f-test2": "b"},
                        ],
                        "some_personal_info_not_registered": False,  # Issuer cannot have any personal info
                    },
                ],
                "footers": [
                    {
                        "key": "aaa",
                        "value": "aaa",
                    },
                    {
                        "f-hoge": "aaaa",
                        "f-fuga": "bbbb",
                    },
                ],
            }
        )

    # <Normal_3_5>
    # latest_flg = 1 (Get the latest personal info)
    #   - address_1 has personal info in the DB but the values are null
    #   - address_2 has personal info in the DB
    @pytest.mark.asyncio
    async def test_normal_3_5(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        _idx_personal_info_1 = IDXPersonalInfo()  # Note: account_address_1 has personal information in DB but the values are null
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": None,
            "address": None,
        }
        _idx_personal_info_1.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_idx_personal_info_1)

        _idx_personal_info_2 = (
            IDXPersonalInfo()
        )  # Note: account_address_2 has personal information in DB
        _idx_personal_info_2.account_address = account_address_2
        _idx_personal_info_2.issuer_address = issuer_address
        _idx_personal_info_2.personal_info = {
            "name": "name_db_2",
            "address": "address_db_2",
        }
        _idx_personal_info_2.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_idx_personal_info_2)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"test1": "a", "test2": "b"},
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {"f-test1": "a", "f-test2": "b"},
        ]
        _details_1.data_type = LedgerDataType.IBET_FIN
        _details_1.data_source = token_address
        async_db.add(_details_1)

        await async_db.commit()

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token.require_personal_info_registered = True
        token_get_mock = mock.patch(
            "app.model.blockchain.IbetStraightBondContract.get", return_value=token
        )
        personal_get_info_mock = mock.patch(
            "app.model.blockchain.PersonalInfoContract.get_info"
        )

        # request target API
        with (
            token_get_mock,
            personal_get_info_mock as personal_get_info_mock_patch,
        ):
            # Note:
            # account_address_1 has no personal information in the DB
            # and gets information from the contract
            personal_get_info_mock_patch.side_effect = [
                {
                    "name": "name_contract_1",
                    "address": "address_contract_1",
                },
                {
                    "name": "name_contract_2",
                    "address": "address_contract_2",
                },
            ]

            resp = await async_client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 1,
                },
                headers={
                    "issuer-address": issuer_address,
                },
            )
            # assertion
            personal_get_info_mock_patch.assert_has_calls(
                [call(account_address=account_address_1, default_value=None)]
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_contract_1",
                            "address": "address_contract_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_db_2",
                            "address": "address_db_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_4>
    # Test `currency` backward compatibility
    @pytest.mark.asyncio
    async def test_normal_4(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 0,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_5_1>
    # `some_personal_info_not_registered` is not set in ledger data
    # Test backward compatibility for specifications earlier than v24.6
    # latest_flg != 1
    @pytest.mark.asyncio
    async def test_normal_5_1(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_23_12
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 0,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    # <Normal_5_2>
    # `some_personal_info_not_registered` is not set in ledger data
    # Test backward compatibility for specifications earlier than v24.6
    # latest_flg == 1
    @pytest.mark.asyncio
    async def test_normal_5_2(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_23_12
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        _idx_personal_info_1 = (
            IDXPersonalInfo()
        )  # Note: account_address_1 has personal information in DB
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": "name_db_1",
            "address": "address_db_1",
        }
        _idx_personal_info_1.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_idx_personal_info_1)

        await async_db.commit()

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token.require_personal_info_registered = False
        token_get_mock = mock.patch(
            "app.model.blockchain.IbetStraightBondContract.get", return_value=token
        )

        # request target API
        with token_get_mock:
            resp = await async_client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 1,
                },
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "currency": "JPY",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1-1": "a", "test2-1": "b"},
                    ],
                    "data": [
                        {
                            "account_address": None,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": None,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1-1": "a", "f-test2-1": "b"},
                    ],
                    "some_personal_info_not_registered": False,
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error(issuer-address)
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2>
    # Parameter Error(latest_flg less)
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": -1,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "latest_flg"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                }
            ],
        }

    # <Error_3>
    # Parameter Error(latest_flg greater)
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 2,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"le": 1},
                    "input": "2",
                    "loc": ["query", "latest_flg"],
                    "msg": "Input should be less than or equal to 1",
                    "type": "less_than_equal",
                }
            ],
        }

    # <Error_4_1>
    # Token Not Found
    # set issuer-address
    @pytest.mark.asyncio
    async def test_error_4_1(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = (
            "0x1234567890123456789012345678901234567899"  # not target
        )
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 2
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token does not exist",
        }

    # <Error_4_2>
    # Token Not Found
    # unset issuer-address
    @pytest.mark.asyncio
    async def test_error_4_2(self, async_client, async_db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token does not exist",
        }

    # <Error_5>
    # Processing Token
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # <Error_6>
    # Ledger Not Found
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "ledger does not exist",
        }

    # <Error_7>
    # Response data includes over 64-bit range int
    @pytest.mark.asyncio
    async def test_error_7(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"test1": "a", "test2": "b"},
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 2,
                            "price": 2**63,
                            "balance": 2**64,  # Over 64-bit int range
                            "acquisition_date": "2022/12/02",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 100 * 200,
                            "acquisition_date": "2022/12/03",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {"f-test1": "a", "f-test2": "b"},
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "f-hoge": "aaaa",
                    "f-fuga": "bbbb",
                },
            ],
        }
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_ledger_1)

        await async_db.commit()

        # request target API
        with mock.patch("app.utils.fastapi_utils.RESPONSE_VALIDATION_MODE", False):
            resp = await async_client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 0,
                },
                headers={
                    "issuer-address": issuer_address,
                },
            )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 5, "title": "Integer64bitLimitExceededError"},
            "detail": "Response data includes integer which exceeds 64-bit range",
        }
