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
    LedgerRightsDetails,
    LedgerTemplate,
    LedgerTemplateRights
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
            "原簿作成日": "2022/12/01",
            "原簿名称": "テスト原簿",
            "項目": {
                "pdf_header_1": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "pdf_footer_1": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                "aaaa": "bbbb"
            },
            "権利": [
                {
                    "権利名称": "権利_test_1",
                    "項目": {
                        "pdf_sub_1_header_1": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "pdf_sub_1_header_2": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "aaaa": "cccc"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": "account_address_test_1",
                            "氏名または名称": "name_test_1",
                            "住所": "address_test_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                }
            ]
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
            "原簿作成日": "2022/12/01",
            "原簿名称": "テスト原簿",
            "項目": {
                "pdf_header_1": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "pdf_footer_1": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                "aaaa": "bbbb"
            },
            "権利": [
                {
                    "権利名称": "権利_test_1",
                    "項目": {
                        "pdf_sub_1_header_1": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "pdf_sub_1_header_2": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "aaaa": "cccc"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": "account_address_test_1",
                            "氏名または名称": "name_test_1",
                            "住所": "address_test_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                }
            ]
        }

    # <Normal_2>
    # Most Recent(JPN)
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
            "原簿作成日": "2022/12/01",
            "原簿名称": "テスト原簿",
            "項目": {
                "pdf_header_1": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "pdf_footer_1": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                "aaaa": "bbbb"
            },
            "権利": [
                {
                    "権利名称": "権利_test_1",  # NOTE: Not Exists Ledger Rights Template(be erased from response)
                    "項目": {
                        "pdf_sub_1_header_1": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "pdf_sub_1_header_2": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "aaaa": "cccc"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": account_address_1,
                            "氏名または名称": "name_test_1",
                            "住所": "address_test_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                },
                {
                    "権利名称": "権利_test_2",  # NOTE: Recent from blockchain
                    "項目": {
                        "aaaa": "cccc"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": account_address_1,
                            "氏名または名称": "name_test_1",
                            "住所": "address_test_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                        {
                            "アカウントアドレス": account_address_2,
                            "氏名または名称": "name_test_2",
                            "住所": "address_test_2",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                },
                {
                    "権利名称": "権利_test_3",  # NOTE: Recent from database
                    "項目": {
                        "aaaa": "cccc"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": account_address_1,
                            "氏名または名称": "name_test_1",
                            "住所": "address_test_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                }
            ]
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
        _template.ledger_name = "テスト原簿_update"
        _template.country_code = "JPN"
        _template.item = {
            "hoge": "aaaa",
            "fuga": "bbbb",
        }
        db.add(_template)

        _rights_1 = LedgerTemplateRights()
        _rights_1.token_address = token_address
        _rights_1.rights_name = "権利_test_2"
        _rights_1.item = {
            "test1": "a",
            "test2": "b"
        }
        _rights_1.details_item = {
            "d-test1": "a",
            "d-test2": "b"
        }
        db.add(_rights_1)

        _rights_2 = LedgerTemplateRights()
        _rights_2.token_address = token_address
        _rights_2.rights_name = "権利_test_3"
        _rights_2.item = {
            "test1-1": "a",
            "test2-1": "b"
        }
        _rights_2.details_item = {
            "d-test1-1": "a",
            "d-test2-1": "b"
        }
        _rights_2.is_uploaded_details = True
        db.add(_rights_2)

        _rights_2_details_1 = LedgerRightsDetails()
        _rights_2_details_1.token_address = token_address
        _rights_2_details_1.rights_name = "権利_test_3"
        _rights_2_details_1.account_address = "account_address_test_1"
        _rights_2_details_1.name = "name_test_1"
        _rights_2_details_1.address = "address_test_1"
        _rights_2_details_1.amount = 10
        _rights_2_details_1.price = 20
        _rights_2_details_1.balance = 200
        _rights_2_details_1.acquisition_date = "2020/01/01"
        db.add(_rights_2_details_1)

        _rights_2_details_2 = LedgerRightsDetails()
        _rights_2_details_2.token_address = token_address
        _rights_2_details_2.rights_name = "権利_test_3"
        _rights_2_details_2.account_address = "account_address_test_2"
        _rights_2_details_2.name = "name_test_2"
        _rights_2_details_2.address = "address_test_2"
        _rights_2_details_2.amount = 20
        _rights_2_details_2.price = 30
        _rights_2_details_2.balance = 600
        _rights_2_details_2.acquisition_date = "2020/01/02"
        db.add(_rights_2_details_2)

        # NOTE: Add response
        _rights_3 = LedgerTemplateRights()
        _rights_3.token_address = token_address
        _rights_3.rights_name = "権利_test_4"
        _rights_3.item = {
            "test1-2": "a",
            "test2-2": "b"
        }
        _rights_3.details_item = {
            "d-test1-2": "a",
            "d-test2-2": "b"
        }
        db.add(_rights_3)

        # NOTE: Add response
        _rights_4 = LedgerTemplateRights()
        _rights_4.token_address = token_address
        _rights_4.rights_name = "権利_test_5"
        _rights_4.item = {
            "test1-3": "a",
            "test2-3": "b"
        }
        _rights_4.details_item = {
            "d-test1-3": "a",
            "d-test2-3": "b"
        }
        _rights_4.is_uploaded_details = True
        db.add(_rights_4)

        _rights_4_details_1 = LedgerRightsDetails()
        _rights_4_details_1.token_address = token_address
        _rights_4_details_1.rights_name = "権利_test_5"
        _rights_4_details_1.account_address = "account_address_test_3"
        _rights_4_details_1.name = "name_test_3"
        _rights_4_details_1.address = "address_test_3"
        _rights_4_details_1.amount = 10
        _rights_4_details_1.price = 20
        _rights_4_details_1.balance = 200
        _rights_4_details_1.acquisition_date = "2020/01/01"
        db.add(_rights_4_details_1)

        _rights_4_details_2 = LedgerRightsDetails()
        _rights_4_details_2.token_address = token_address
        _rights_4_details_2.rights_name = "権利_test_5"
        _rights_4_details_2.account_address = "account_address_test_4"
        _rights_4_details_2.name = "name_test_4"
        _rights_4_details_2.address = "address_test_4"
        _rights_4_details_2.amount = 20
        _rights_4_details_2.price = 30
        _rights_4_details_2.balance = 600
        _rights_4_details_2.acquisition_date = "2020/01/02"
        db.add(_rights_4_details_2)

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
            "原簿作成日": "2022/12/01",
            "原簿名称": "テスト原簿_update",
            "項目": {
                "hoge": "aaaa",
                "fuga": "bbbb",
            },
            "権利": [
                {
                    "権利名称": "権利_test_2",
                    "項目": {
                        "test1": "a",
                        "test2": "b"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": account_address_1,
                            "氏名または名称": "name_db_1",
                            "住所": "address_db_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "d-test1": "a",
                            "d-test2": "b"
                        },
                        {
                            "アカウントアドレス": account_address_2,
                            "氏名または名称": "name_contract_2",
                            "住所": "address_contract_2",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "d-test1": "a",
                            "d-test2": "b"
                        }
                    ]
                },
                {
                    "権利名称": "権利_test_3",
                    "項目": {
                        "test1-1": "a",
                        "test2-1": "b"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": "account_address_test_1",
                            "氏名または名称": "name_test_1",
                            "住所": "address_test_1",
                            "保有口数": 10,
                            "一口あたりの金額": 20,
                            "保有残高": 200,
                            "取得日": "2020/01/01",
                            "d-test1-1": "a",
                            "d-test2-1": "b"
                        },
                        {
                            "アカウントアドレス": "account_address_test_2",
                            "氏名または名称": "name_test_2",
                            "住所": "address_test_2",
                            "保有口数": 20,
                            "一口あたりの金額": 30,
                            "保有残高": 600,
                            "取得日": "2020/01/02",
                            "d-test1-1": "a",
                            "d-test2-1": "b"
                        }
                    ]
                },
                {
                    "権利名称": "権利_test_4",
                    "項目": {
                        "test1-2": "a",
                        "test2-2": "b"
                    },
                    "明細": []
                },
                {
                    "権利名称": "権利_test_5",
                    "項目": {
                        "test1-3": "a",
                        "test2-3": "b"
                    },
                    "明細": [
                        {
                            "アカウントアドレス": "account_address_test_3",
                            "氏名または名称": "name_test_3",
                            "住所": "address_test_3",
                            "保有口数": 10,
                            "一口あたりの金額": 20,
                            "保有残高": 200,
                            "取得日": "2020/01/01",
                            "d-test1-3": "a",
                            "d-test2-3": "b"
                        },
                        {
                            "アカウントアドレス": "account_address_test_4",
                            "氏名または名称": "name_test_4",
                            "住所": "address_test_4",
                            "保有口数": 20,
                            "一口あたりの金額": 30,
                            "保有残高": 600,
                            "取得日": "2020/01/02",
                            "d-test1-3": "a",
                            "d-test2-3": "b"
                        }
                    ]
                },
            ]
        }

    # <Normal_3>
    # Most Recent(not JPN)
    def test_normal_3(self, client, db):
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
            "ledger_name": "テスト原簿",
            "item": {
                "pdf_header_1": {
                    "key": "本原簿について",
                    "value": "本社債は株式会社Aが発行した無担保社債である"
                },
                "pdf_footer_1": "bbbbbbbbbbbbbbbbbbbbbbbbb",
                "aaaa": "bbbb"
            },
            "rights": [
                {
                    "rights_name": "権利_test_1",  # NOTE: Not Exists Ledger Rights Template(be erased from response)
                    "item": {
                        "pdf_sub_1_header_1": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "pdf_sub_1_header_2": {
                            "key": "本原簿の説明",
                            "value": "aaaaaaaaaaaaaaa"
                        },
                        "aaaa": "cccc"
                    },
                    "details": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 2,
                            "price": 100,
                            "balance": 200,
                            "acquisition_date": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                },
                {
                    "rights_name": "権利_test_2",  # NOTE: Recent from blockchain
                    "item": {
                        "aaaa": "cccc"
                    },
                    "details": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 2,
                            "price": 100,
                            "balance": 200,
                            "acquisition_date": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 2,
                            "price": 100,
                            "balance": 200,
                            "acquisition_date": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                },
                {
                    "rights_name": "権利_test_3",  # NOTE: Recent from database
                    "item": {
                        "aaaa": "cccc"
                    },
                    "details": [
                        {
                            "account_address": account_address_1,
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 2,
                            "price": 100,
                            "balance": 200,
                            "acquisition_date": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                }
            ]
        }
        _ledger_1.country_code = "USA"
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
        _template.ledger_name = "テスト原簿_update"
        _template.country_code = "USA"
        _template.item = {
            "hoge": "aaaa",
            "fuga": "bbbb",
        }
        db.add(_template)

        _rights_1 = LedgerTemplateRights()
        _rights_1.token_address = token_address
        _rights_1.rights_name = "権利_test_2"
        _rights_1.item = {
            "test1": "a",
            "test2": "b"
        }
        _rights_1.details_item = {
            "d-test1": "a",
            "d-test2": "b"
        }
        db.add(_rights_1)

        _rights_2 = LedgerTemplateRights()
        _rights_2.token_address = token_address
        _rights_2.rights_name = "権利_test_3"
        _rights_2.item = {
            "test1-1": "a",
            "test2-1": "b"
        }
        _rights_2.details_item = {
            "d-test1-1": "a",
            "d-test2-1": "b"
        }
        _rights_2.is_uploaded_details = True
        db.add(_rights_2)

        _rights_2_details_1 = LedgerRightsDetails()
        _rights_2_details_1.token_address = token_address
        _rights_2_details_1.rights_name = "権利_test_3"
        _rights_2_details_1.account_address = "account_address_test_1"
        _rights_2_details_1.name = "name_test_1"
        _rights_2_details_1.address = "address_test_1"
        _rights_2_details_1.amount = 10
        _rights_2_details_1.price = 20
        _rights_2_details_1.balance = 200
        _rights_2_details_1.acquisition_date = "2020/01/01"
        db.add(_rights_2_details_1)

        _rights_2_details_2 = LedgerRightsDetails()
        _rights_2_details_2.token_address = token_address
        _rights_2_details_2.rights_name = "権利_test_3"
        _rights_2_details_2.account_address = "account_address_test_2"
        _rights_2_details_2.name = "name_test_2"
        _rights_2_details_2.address = "address_test_2"
        _rights_2_details_2.amount = 20
        _rights_2_details_2.price = 30
        _rights_2_details_2.balance = 600
        _rights_2_details_2.acquisition_date = "2020/01/02"
        db.add(_rights_2_details_2)

        # NOTE: Add response
        _rights_3 = LedgerTemplateRights()
        _rights_3.token_address = token_address
        _rights_3.rights_name = "権利_test_4"
        _rights_3.item = {
            "test1-2": "a",
            "test2-2": "b"
        }
        _rights_3.details_item = {
            "d-test1-2": "a",
            "d-test2-2": "b"
        }
        db.add(_rights_3)

        # NOTE: Add response
        _rights_4 = LedgerTemplateRights()
        _rights_4.token_address = token_address
        _rights_4.rights_name = "権利_test_5"
        _rights_4.item = {
            "test1-3": "a",
            "test2-3": "b"
        }
        _rights_4.details_item = {
            "d-test1-3": "a",
            "d-test2-3": "b"
        }
        _rights_4.is_uploaded_details = True
        db.add(_rights_4)

        _rights_4_details_1 = LedgerRightsDetails()
        _rights_4_details_1.token_address = token_address
        _rights_4_details_1.rights_name = "権利_test_5"
        _rights_4_details_1.account_address = "account_address_test_3"
        _rights_4_details_1.name = "name_test_3"
        _rights_4_details_1.address = "address_test_3"
        _rights_4_details_1.amount = 10
        _rights_4_details_1.price = 20
        _rights_4_details_1.balance = 200
        _rights_4_details_1.acquisition_date = "2020/01/01"
        db.add(_rights_4_details_1)

        _rights_4_details_2 = LedgerRightsDetails()
        _rights_4_details_2.token_address = token_address
        _rights_4_details_2.rights_name = "権利_test_5"
        _rights_4_details_2.account_address = "account_address_test_4"
        _rights_4_details_2.name = "name_test_4"
        _rights_4_details_2.address = "address_test_4"
        _rights_4_details_2.amount = 20
        _rights_4_details_2.price = 30
        _rights_4_details_2.balance = 600
        _rights_4_details_2.acquisition_date = "2020/01/02"
        db.add(_rights_4_details_2)

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
            "ledger_name": "テスト原簿_update",
            "item": {
                "hoge": "aaaa",
                "fuga": "bbbb",
            },
            "rights": [
                {
                    "rights_name": "権利_test_2",
                    "item": {
                        "test1": "a",
                        "test2": "b"
                    },
                    "details": [
                        {
                            "account_address": account_address_1,
                            "name": "name_db_1",
                            "address": "address_db_1",
                            "amount": 2,
                            "price": 100,
                            "balance": 200,
                            "acquisition_date": "2022/01/01",
                            "d-test1": "a",
                            "d-test2": "b"
                        },
                        {
                            "account_address": account_address_2,
                            "name": "name_contract_2",
                            "address": "address_contract_2",
                            "amount": 2,
                            "price": 100,
                            "balance": 200,
                            "acquisition_date": "2022/01/01",
                            "d-test1": "a",
                            "d-test2": "b"
                        }
                    ]
                },
                {
                    "rights_name": "権利_test_3",
                    "item": {
                        "test1-1": "a",
                        "test2-1": "b"
                    },
                    "details": [
                        {
                            "account_address": "account_address_test_1",
                            "name": "name_test_1",
                            "address": "address_test_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                            "d-test1-1": "a",
                            "d-test2-1": "b"
                        },
                        {
                            "account_address": "account_address_test_2",
                            "name": "name_test_2",
                            "address": "address_test_2",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                            "d-test1-1": "a",
                            "d-test2-1": "b"
                        }
                    ]
                },
                {
                    "rights_name": "権利_test_4",
                    "item": {
                        "test1-2": "a",
                        "test2-2": "b"
                    },
                    "details": []
                },
                {
                    "rights_name": "権利_test_5",
                    "item": {
                        "test1-3": "a",
                        "test2-3": "b"
                    },
                    "details": [
                        {
                            "account_address": "account_address_test_3",
                            "name": "name_test_3",
                            "address": "address_test_3",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2020/01/01",
                            "d-test1-3": "a",
                            "d-test2-3": "b"
                        },
                        {
                            "account_address": "account_address_test_4",
                            "name": "name_test_4",
                            "address": "address_test_4",
                            "amount": 20,
                            "price": 30,
                            "balance": 600,
                            "acquisition_date": "2020/01/02",
                            "d-test1-3": "a",
                            "d-test2-3": "b"
                        }
                    ]
                },
            ]
        }

    # <Normal_4>
    # Most Recent Default Corporate Bond Ledger
    def test_normal_4(self, client, db):
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
            "原簿作成日": "2022/12/01",
            "原簿名称": "",
            "項目": {
                "社債の説明": "",
                "社債の総額": None,
                "各社債の金額": None,
                "払込情報": {
                    "払込金額": None,
                    "払込日": "",
                    "払込状況": None
                },
                "社債の種類": "",
                "社債原簿管理人": {
                    "氏名または名称": "",
                    "住所": "",
                    "事務取扱場所": ""
                },
            },
            "権利": [
                {
                    "権利名称": "社債",
                    "項目": {},
                    "明細": [
                        {
                            "アカウントアドレス": account_address_1,
                            "氏名または名称": "name_test_1",
                            "住所": "address_test_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                        {
                            "アカウントアドレス": account_address_2,
                            "氏名または名称": "name_test_2",
                            "住所": "address_test_2",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                }
            ]
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
            "原簿作成日": "2022/12/01",
            "原簿名称": "",
            "項目": {
                "社債の説明": "",
                "社債の総額": None,
                "各社債の金額": None,
                "払込情報": {
                    "払込金額": None,
                    "払込日": "",
                    "払込状況": None
                },
                "社債の種類": "",
                "社債原簿管理人": {
                    "氏名または名称": "",
                    "住所": "",
                    "事務取扱場所": ""
                },
            },
            "権利": [
                {
                    "権利名称": "社債",
                    "項目": {},
                    "明細": [
                        {
                            "アカウントアドレス": account_address_1,
                            "氏名または名称": "name_db_1",
                            "住所": "address_db_1",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                        {
                            "アカウントアドレス": account_address_2,
                            "氏名または名称": "name_contract_2",
                            "住所": "address_contract_2",
                            "保有口数": 2,
                            "一口あたりの金額": 100,
                            "保有残高": 200,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        }
                    ]
                }
            ]
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

    # <Error_8>
    # Country Code Changed
    def test_error_8(self, client, db):
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

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND
        _ledger_1.ledger = {
            "原簿作成日": "2022/12/01",
            "原簿名称": "テスト原簿",
            "項目": {},
            "権利": [
                {
                    "権利名称": "権利_test_1",
                    "項目": {},
                    "明細": []
                },
            ]
        }
        _ledger_1.country_code = "JPN"
        _ledger_1.ledger_created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_ledger_1)

        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.ledger_name = "テスト原簿_update"
        _template.country_code = "USA"
        _template.item = {
            "hoge": "aaaa",
            "fuga": "bbbb",
        }
        db.add(_template)

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
            "detail": "cannot be updated because country_code has changed"
        }
