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

    # <Normal_1_1>
    # Set issue-address in the header
    def test_normal_1_1(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
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
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        # request target AsPI
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
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }

    # <Normal_1_2>
    # Do not set issue-address in the header
    def test_normal_1_2(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
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
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        # request target AsPI
        resp = client.get(
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
            "headers": [
                {
                    "key": "aaa",
                    "value": "aaa",
                },
                {
                    "hoge": "aaaa",
                    "fuga": "bbbb",
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }

    # <Normal_2_1>
    # latest_flg = 1 (Get the latest personal info)
    #  address_1 has personal info in the DB
    #  address_2 has no personal info in the DB
    def test_normal_2_1(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
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
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        _idx_personal_info_1 = IDXPersonalInfo()  # Note: account_address_1 has personal information in DB
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": "name_db_1",
            "address": "address_db_1"
        }
        db.add(_idx_personal_info_1)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {
                "test1": "a",
                "test2": "b"
            }
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {
                "f-test1": "a",
                "f-test2": "b"
            }
        ]
        _details_1.data_type = LedgerDetailsDataType.IBET_FIN.value
        _details_1.data_source = token_address
        db.add(_details_1)

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token_get_mock = mock.patch("app.model.blockchain.IbetStraightBondContract.get", return_value=token)
        personal_get_info_mock = mock.patch("app.model.blockchain.PersonalInfoContract.get_info")

        # request target API
        with token_get_mock as token_get_mock_patch, personal_get_info_mock as personal_get_info_mock_patch:
            # Note:
            # account_address_2 has no personal information in the DB
            # and gets information from the contract
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
                call(account_address=account_address_2, default_value=None)
            ])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
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
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }

    # <Normal_2_2>
    # latest_flg = 1 (Get the latest personal info)
    #  address_1 has partial personal info in the DB
    #  address_2 has no personal info in the DB
    def test_normal_2_2(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
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
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        _idx_personal_info_1 = IDXPersonalInfo()  # Note: account_address_1 has partial personal information in DB
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": None,
            "address": None
        }
        db.add(_idx_personal_info_1)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {
                "test1": "a",
                "test2": "b"
            }
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "aaa",
            },
            {
                "f-test1": "a",
                "f-test2": "b"
            }
        ]
        _details_1.data_type = LedgerDetailsDataType.IBET_FIN.value
        _details_1.data_source = token_address
        db.add(_details_1)

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token.issuer_address = issuer_address
        token_get_mock = mock.patch("app.model.blockchain.IbetStraightBondContract.get", return_value=token)
        personal_get_info_mock = mock.patch("app.model.blockchain.PersonalInfoContract.get_info")

        # request target API
        with token_get_mock as token_get_mock_patch, personal_get_info_mock as personal_get_info_mock_patch:
            # Note:
            # account_address_2 has no personal information in the DB
            # and gets information from the contract
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
                call(account_address=account_address_2, default_value=None)
            ])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
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
                }
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1": "a",
                            "test2": "b"
                        }
                    ],
                    "data": [
                        {
                            "account_address": account_address_1,
                            # Value stored with None should be converted to empty string.
                            "name": "",
                            "address": "",
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
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1": "a",
                            "f-test2": "b"
                        }
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "test1-1": "a",
                            "test2-1": "b"
                        }
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
                        }
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "aaa",
                        },
                        {
                            "f-test1-1": "a",
                            "f-test2-1": "b"
                        }
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
                }
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error(issuer-address)
    def test_error_1(self, client, db):
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

    # <Error_2>
    # Parameter Error(latest_flg less)
    def test_error_2(self, client, db):
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

    # <Error_3>
    # Parameter Error(latest_flg greater)
    def test_error_3(self, client, db):
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

    # <Error_4_1>
    # Token Not Found
    # set issuer-address
    def test_error_4_1(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = "0x1234567890123456789012345678901234567899"  # not target
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 2
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
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token does not exist"
        }

    # <Error_4_2>
    # Token Not Found
    # unset issuer-address
    def test_error_4_2(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address, ledger_id=1),
            params={
                "latest_flg": 1,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token does not exist"
        }

    # <Error_5>
    # Processing Token
    def test_error_5(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 0
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
            "detail": "wait for a while as the token is being processed"
        }

    # <Error_6>
    # Ledger Not Found
    def test_error_6(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
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
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "ledger does not exist"
        }

