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

from app.model.db import Token, TokenType, BondLedger, CorporateBondLedgerTemplateJPN, IDXPersonalInfo
from app.model.blockchain import IbetStraightBondContract
from tests.account_config import config_eth_account


class TestAppBondLedgerTokenAddressHistoryLedgerIdGETJPN:
    # target API endpoint
    base_url = "/bond_ledger/{}/history/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Not Most Recent
    def test_normal_1(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        ledger = {
            "テスト1": "test1",
            "テスト2": "test2",
        }

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _bond_ledger = BondLedger()
        _bond_ledger.token_address = token_address
        _bond_ledger.ledger = ledger
        _bond_ledger.country_code = "JPN"
        db.add(_bond_ledger)

        # request target API
        req_param = {
            "locale": "jpn",
            "latest_flg": 0
        }
        resp = client.get(
            self.base_url.format(token_address, 1),
            params=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == ledger

    # <Normal_2>
    # Most Recent(PersonalInfo from DB)
    def test_normal_2(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"
        personal_info_1 = {
            "key_manager": "string",
            "name": "name_test_1",
            "postal_code": "string",
            "address": "address_test_1",
            "email": "string",
            "birth": "string"
        }
        personal_info_2 = {
            "key_manager": "string",
            "name": "name_test_2",
            "postal_code": "string",
            "address": "address_test_2",
            "email": "string",
            "birth": "string"
        }
        ledger = {
            "社債原簿作成日": "string",
            "社債情報": {
                "社債名称": "string",
                "社債の説明": "string",
                "社債の総額": 0,
                "各社債の金額": 0,
                "払込情報": {
                    "払込金額": 0,
                    "払込日": "string",
                    "払込状況": True,
                },
                "社債の種類": "string"
            },
            "社債原簿管理人": {
                "氏名または名称": "string",
                "住所": "string",
                "事務取扱場所": "string"
            },
            "社債権者": [
                {
                    "アカウントアドレス": account_address_1,
                    "氏名または名称": "string",
                    "住所": "string",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                },
                {
                    "アカウントアドレス": account_address_2,
                    "氏名または名称": "string",
                    "住所": "string",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                }
            ]
        }

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _bond_ledger = BondLedger()
        _bond_ledger.token_address = token_address
        _bond_ledger.ledger = ledger
        _bond_ledger.country_code = "JPN"
        db.add(_bond_ledger)

        _template = CorporateBondLedgerTemplateJPN()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.bond_name = "bond_name_test"
        _template.bond_description = "bond_description_test"
        _template.bond_type = "bond_type_test"
        _template.total_amount = 10
        _template.face_value = 20
        _template.payment_amount = 30
        _template.payment_date = "20211231"
        _template.payment_status = False
        _template.hq_name = "hq_name_test"
        _template.hq_address = "hq_address_test"
        _template.hq_office_address = "hq_office_address_test"
        db.add(_template)

        _idx_personal_info_1 = IDXPersonalInfo()
        _idx_personal_info_1.account_address = account_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = personal_info_1
        db.add(_idx_personal_info_1)
        _idx_personal_info_2 = IDXPersonalInfo()
        _idx_personal_info_2.account_address = account_address_2
        _idx_personal_info_2.issuer_address = issuer_address
        _idx_personal_info_2.personal_info = personal_info_2
        db.add(_idx_personal_info_2)

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token_get_mock = mock.patch("app.model.blockchain.IbetStraightBondContract.get", return_value=token)
        personal_get_info_mock = mock.patch("app.model.blockchain.PersonalInfoContract.get_info")

        # request target API
        with token_get_mock as token_get_mock_patch, personal_get_info_mock as personal_get_info_mock_patch:
            req_param = {
                "locale": "jpn",
                "latest_flg": 1
            }
            resp = client.get(
                self.base_url.format(token_address, 1),
                params=req_param,
                headers={
                    "issuer-address": issuer_address,
                }
            )

            # assertion
            token_get_mock_patch.assert_any_call(token_address)
            personal_get_info_mock_patch.assert_not_called()

        assert resp.status_code == 200
        assert resp.json() == {
            "社債原簿作成日": "string",
            "社債情報": {
                "社債名称": "bond_name_test",
                "社債の説明": "bond_description_test",
                "社債の総額": 10,
                "各社債の金額": 20,
                "払込情報": {
                    "払込金額": 30,
                    "払込日": "20211231",
                    "払込状況": False,
                },
                "社債の種類": "bond_type_test"
            },
            "社債原簿管理人": {
                "氏名または名称": "hq_name_test",
                "住所": "hq_address_test",
                "事務取扱場所": "hq_office_address_test"
            },
            "社債権者": [
                {
                    "アカウントアドレス": account_address_1,
                    "氏名または名称": "name_test_1",
                    "住所": "address_test_1",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                },
                {
                    "アカウントアドレス": account_address_2,
                    "氏名または名称": "name_test_2",
                    "住所": "address_test_2",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                }
            ]
        }

    # <Normal_3>
    # Most Recent(PersonalInfo from Contract)
    def test_normal_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        account_address_1 = "0xABCdeF1234567890abCDeF123456789000000001"
        account_address_2 = "0xaBcdEF1234567890aBCDEF123456789000000002"
        personal_info_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"
        personal_info_1 = {
            "key_manager": "string",
            "name": "name_test_1",
            "postal_code": "string",
            "address": "address_test_1",
            "email": "string",
            "birth": "string"
        }
        personal_info_2 = {
            "key_manager": "string",
            "name": "name_test_2",
            "postal_code": "string",
            "address": "address_test_2",
            "email": "string",
            "birth": "string"
        }
        ledger = {
            "社債原簿作成日": "string",
            "社債情報": {
                "社債名称": "string",
                "社債の説明": "string",
                "社債の総額": 0,
                "各社債の金額": 0,
                "払込情報": {
                    "払込金額": 0,
                    "払込日": "string",
                    "払込状況": True,
                },
                "社債の種類": "string"
            },
            "社債原簿管理人": {
                "氏名または名称": "string",
                "住所": "string",
                "事務取扱場所": "string"
            },
            "社債権者": [
                {
                    "アカウントアドレス": account_address_1,
                    "氏名または名称": "string",
                    "住所": "string",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                },
                {
                    "アカウントアドレス": account_address_2,
                    "氏名または名称": "string",
                    "住所": "string",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                }
            ]
        }

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _bond_ledger = BondLedger()
        _bond_ledger.token_address = token_address
        _bond_ledger.ledger = ledger
        _bond_ledger.country_code = "JPN"
        db.add(_bond_ledger)

        _template = CorporateBondLedgerTemplateJPN()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.bond_name = "bond_name_test"
        _template.bond_description = "bond_description_test"
        _template.bond_type = "bond_type_test"
        _template.total_amount = 10
        _template.face_value = 20
        _template.payment_amount = 30
        _template.payment_date = "20211231"
        _template.payment_status = False
        _template.hq_name = "hq_name_test"
        _template.hq_address = "hq_address_test"
        _template.hq_office_address = "hq_office_address_test"
        db.add(_template)

        # Mock
        token = IbetStraightBondContract()
        token.personal_info_contract_address = personal_info_contract_address
        token_get_mock = mock.patch("app.model.blockchain.IbetStraightBondContract.get", return_value=token)
        personal_get_info_mock = mock.patch("app.model.blockchain.PersonalInfoContract.get_info")

        # request target API
        with token_get_mock as token_get_mock_patch, personal_get_info_mock as personal_get_info_mock_patch:
            personal_get_info_mock_patch.side_effect = [personal_info_1, personal_info_2]

            req_param = {
                "locale": "jpn",
                "latest_flg": 1
            }
            resp = client.get(
                self.base_url.format(token_address, 1),
                params=req_param,
                headers={
                    "issuer-address": issuer_address,
                }
            )

            # assertion
            token_get_mock_patch.assert_any_call(token_address)
            personal_get_info_mock_patch.assert_has_calls([
                call(account_address_1, default_value=""),
                call(account_address_2, default_value="")
            ])

        assert resp.status_code == 200
        assert resp.json() == {
            "社債原簿作成日": "string",
            "社債情報": {
                "社債名称": "bond_name_test",
                "社債の説明": "bond_description_test",
                "社債の総額": 10,
                "各社債の金額": 20,
                "払込情報": {
                    "払込金額": 30,
                    "払込日": "20211231",
                    "払込状況": False,
                },
                "社債の種類": "bond_type_test"
            },
            "社債原簿管理人": {
                "氏名または名称": "hq_name_test",
                "住所": "hq_address_test",
                "事務取扱場所": "hq_office_address_test"
            },
            "社債権者": [
                {
                    "アカウントアドレス": account_address_1,
                    "氏名または名称": "name_test_1",
                    "住所": "address_test_1",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                },
                {
                    "アカウントアドレス": account_address_2,
                    "氏名または名称": "name_test_2",
                    "住所": "address_test_2",
                    "社債金額": 0,
                    "取得日": "string",
                    "金銭以外の財産給付情報": {
                        "財産の価格": "string",
                        "給付日": "string"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "string",
                        "相殺日": "string"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "string",
                        "質権者の住所": "string",
                        "質権の目的である債券": "string"
                    },
                    "備考": "string"
                }
            ]
        }

    ###########################################################################
    # Error Case
    ###########################################################################
