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

from app.model.db import (
    Token,
    TokenType,
    IDXPersonalInfo,
    Ledger,
    LedgerDetailsData,
    LedgerTemplate,
    LedgerDetailsTemplate,
LedgerDetailsDataType
)
from app.model.blockchain import IbetStraightBondContract
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressHistoryLedgerIdGET:
    # target API endpoint
    base_url = "/ledger/{token_address}/history/{ledger_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Not Most Recent
    def test_normal_1(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "headers": {
                "hoge": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
            },
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": {
                        "s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                    "data": [
                        {
                            "account_address": "0x001",
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02"
                        }
                    ],
                    "footers": {
                        "f-s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "f-s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                },
            ],
            "footers": {
                "f-hoge": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "f-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
            }
        }
        _ledger_1.country_code = "JPN"
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 0,
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "headers": {
                "hoge": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
            },
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": {
                        "s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                    "data": [
                        {
                            "account_address": "0x001",
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02"
                        }
                    ],
                    "footers": {
                        "f-s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "f-s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                },
            ],
            "footers": {
                "f-hoge": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "f-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
            }
        }

    # <Normal_2>
    # Most Recent
    def test_normal_2(self, client, db):
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
        db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "created": "2022/12/01",
            "token_name": "テスト原簿",
            "headers": {
                "hoge": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
            },
            "details": [
                {
                    "token_detail_type": "権利_test_1",  # NOTE: Not Exists Ledger Details Template(be erased from response)
                    "headers": {
                        "s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                    "data": [
                        {
                            "account_address": "0x001",
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02"
                        }
                    ],
                    "footers": {
                        "f-s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "f-s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                },
                {
                    "token_detail_type": "権利_test_2",  # NOTE: Recent from blockchain
                    "headers": {
                        "s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02"
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03"
                        }
                    ],
                    "footers": {
                        "f-s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "f-s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                },
                {
                    "token_detail_type": "権利_test_3",  # NOTE: Recent from database
                    "headers": {
                        "s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                    "data": [
                        {
                            "account_address": "0x001",
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02"
                        }
                    ],
                    "footers": {
                        "f-s-hoge": {
                            "key": "test",
                            "value": "test2"
                        },
                        "f-s-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                    },
                },
            ],
            "footers": {
                "f-hoge": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "f-fuga": "bbbbbbbbbbbbbbbbbbbbbbbbb",
            }
        }
        _ledger_1.country_code = "JPN"
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        # Note: account_address_1 only
        _idx_personal_info_1 = IDXPersonalInfo()
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": "name_db_1",
            "address": "address_db_1"
        }
        db.add(_idx_personal_info_1)

        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.token_name = "テスト原簿_update"
        _template.country_code = "JPN"
        _template.headers = {
            "hoge": "aaaa",
            "fuga": "bbbb",
        }
        _template.footers = {
            "f-hoge": "aaaa",
            "f-fuga": "bbbb",
        }
        db.add(_template)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_2"
        _details_1.headers = {
            "test1": "a",
            "test2": "b"
        }
        _details_1.footers = {
            "f-test1": "a",
            "f-test2": "b"
        }
        _details_1.data_type = LedgerDetailsDataType.IBET_FIN
        _details_1.data_source =token_address
        db.add(_details_1)

        _details_2 = LedgerDetailsTemplate()
        _details_2.token_address = token_address
        _details_2.token_detail_type = "権利_test_3"
        _details_2.headers = {
            "test1-1": "a",
            "test2-1": "b"
        }
        _details_2.footers = {
            "f-test1-1": "a",
            "f-test2-1": "b"
        }
        _details_2.data_type = LedgerDetailsDataType.DB
        _details_2.data_source = "data_id_2"
        db.add(_details_2)

        _details_2_data_1 = LedgerDetailsData()
        _details_2_data_1.token_address = token_address
        _details_2_data_1.data_id = "data_id_2"
        _details_2_data_1.account_address = "account_address_test_1"
        _details_2_data_1.name = "name_test_1"
        _details_2_data_1.address = "address_test_1"
        _details_2_data_1.amount = 10
        _details_2_data_1.price = 20
        _details_2_data_1.balance = 200
        _details_2_data_1.acquisition_date = "2020/01/01"
        db.add(_details_2_data_1)

        _details_2_data_2 = LedgerDetailsData()
        _details_2_data_2.token_address = token_address
        _details_2_data_2.data_id = "data_id_2"
        _details_2_data_2.account_address = "account_address_test_2"
        _details_2_data_2.name = "name_test_2"
        _details_2_data_2.address = "address_test_2"
        _details_2_data_2.amount = 20
        _details_2_data_2.price = 30
        _details_2_data_2.balance = 600
        _details_2_data_2.acquisition_date = "2020/01/02"
        db.add(_details_2_data_2)

        # NOTE: Add response
        _details_3 = LedgerDetailsTemplate()
        _details_3.token_address = token_address
        _details_3.token_detail_type = "権利_test_4"
        _details_3.headers = {
            "test1-2": "a",
            "test2-2": "b"
        }
        _details_3.footers = {
            "f-test1-2": "a",
            "f-test2-2": "b"
        }
        _details_3.data_type = LedgerDetailsDataType.IBET_FIN
        _details_3.data_source =token_address
        db.add(_details_3)

        # NOTE: Add response
        _details_4 = LedgerDetailsTemplate()
        _details_4.token_address = token_address
        _details_4.token_detail_type = "権利_test_5"
        _details_4.headers = {
            "test1-3": "a",
            "test2-3": "b"
        }
        _details_4.footers = {
            "f-test1-3": "a",
            "f-test2-3": "b"
        }
        _details_4.data_type = LedgerDetailsDataType.DB
        _details_4.data_source = "data_id_4"
        db.add(_details_4)

        _details_4_data_1 = LedgerDetailsData()
        _details_4_data_1.token_address = token_address
        _details_4_data_1.data_id = "data_id_4"
        _details_4_data_1.account_address = "account_address_test_3"
        _details_4_data_1.name = "name_test_3"
        _details_4_data_1.address = "address_test_3"
        _details_4_data_1.amount = 10
        _details_4_data_1.price = 20
        _details_4_data_1.balance = 200
        _details_4_data_1.acquisition_date = "2020/01/01"
        db.add(_details_4_data_1)

        _details_4_data_2 = LedgerDetailsData()
        _details_4_data_2.token_address = token_address
        _details_4_data_2.data_id = "data_id_4"
        _details_4_data_2.account_address = "account_address_test_4"
        _details_4_data_2.name = "name_test_4"
        _details_4_data_2.address = "address_test_4"
        _details_4_data_2.amount = 20
        _details_4_data_2.price = 30
        _details_4_data_2.balance = 600
        _details_4_data_2.acquisition_date = "2020/01/02"
        db.add(_details_4_data_2)

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token_get_mock = mock.patch("app.model.blockchain.IbetStraightBondContract.get", return_value=token)
        personal_get_info_mock = mock.patch("app.model.blockchain.PersonalInfoContract.get_info")

        # request target API
        with token_get_mock as token_get_mock_patch, personal_get_info_mock as personal_get_info_mock_patch:
            # Note: account_address_2 only
            personal_get_info_mock_patch.side_effect = [{
                "name": "name_contract_2",
                "address": "address_contract_2",
            }]
            resp = client.get(
                self.base_url.format(token_address=token_address, ledger_id=1),
                params={
                    "latest_flg": 1,
                },
                headers={
                    "issuer-address": issuer_address,
                }
            )

            # assertion
            token_get_mock_patch.assert_any_call(token_address)
            personal_get_info_mock_patch.assert_has_calls([
                call(account_address_2, default_value="")
            ])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "created": "2022/12/01",
            "token_name": "テスト原簿_update",
            "headers": {
                "hoge": "aaaa",
                "fuga": "bbbb",
            },
            "details": [
                {
                    "token_detail_type": "権利_test_2",
                    "headers": {
                        "test1": "a",
                        "test2": "b"
                    },
                    "data": [
                        {
                            "account_address": account_address_1,
                            "name": "name_db_1",
                            "address": "address_db_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 30,
                            "acquisition_date": "2022/12/02"
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_contract_2",
                            "address": "address_contract_2",
                            "amount": 100,
                            "price": 200,
                            "balance": 300,
                            "acquisition_date": "2022/12/03"
                        }
                    ],
                    "footers": {
                        "f-test1": "a",
                        "f-test2": "b"
                    },
                },
                {
                    "token_detail_type": "権利_test_3",
                    "headers": {
                        "test1-1": "a",
                        "test2-1": "b"
                    },
                    "data": [
                        {
                            "account_address": "account_address_test_1",
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": "account_address_test_2",
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        }
                    ],
                    "footers": {
                        "f-test1-1": "a",
                        "f-test2-1": "b"
                    },
                },
                {
                    "token_detail_type": "権利_test_4",
                    "headers": {
                        "test1-2": "a",
                        "test2-2": "b"
                    },
                    "data": [],
                    "footers": {
                        "f-test1-2": "a",
                        "f-test2-2": "b"
                    },
                },
                {
                    "token_detail_type": "権利_test_5",
                    "headers": {
                        "test1-3": "a",
                        "test2-3": "b"
                    },
                    "data": [
                        {
                            "account_address": "account_address_test_3",
                            "name": "name_test_3",
                            "address": "address_test_3",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                        },
                        {
                            "account_address": "account_address_test_4",
                            "name": "name_test_4",
                            "address": "address_test_4",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                        },
                    ],
                    "footers": {
                        "f-test1-3": "a",
                        "f-test2-3": "b"
                    },
                },
            ],
            "footers": {
                "f-hoge": "aaaa",
                "f-fuga": "bbbb",
            },
        }
    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["query", "latest_flg"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_2>
    # Parameter Error(issuer-address)
    def test_error_2(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": "test",
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_3>
    # Parameter Error(latest_flg less)
    def test_error_3(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": -1,
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "ctx": {
                        "limit_value": 0
                    },
                    "loc": ["query", "latest_flg"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                }
            ]
        }

    # <Error_4>
    # Parameter Error(latest_flg greater)
    def test_error_4(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 2,
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "ctx": {
                        "limit_value": 1
                    },
                    "loc": ["query", "latest_flg"],
                    "msg": "ensure this value is less than or equal to 1",
                    "type": "value_error.number.not_le"
                }
            ]
        }

    # <Error_5>
    # Token Not Found
    def test_error_5(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "token does not exist"
        }

    # <Error_6>
    # Ledger Not Found
    def test_error_6(self, client, db):
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
        db.add(_token)

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "ledger does not exist"
        }

    # <Error_7>
    # Ledger Template Not Found
    def test_error_7(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {}
        _ledger_1.country_code = "JPN"
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "ledger template does not exist"
        }