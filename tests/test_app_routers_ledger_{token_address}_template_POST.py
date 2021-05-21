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

from app.model.db import (
    Token,
    TokenType,
    LedgerTemplate,
    LedgerTemplateRights,
    LedgerRightsDetails
)
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressHistoryTemplatePOST:
    # target API endpoint
    base_url = "/ledger/{token_address}/template"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Create
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

        # request target API
        req_param = {
            "ledger_name": "テスト原簿",
            "country_code": "JPN",
            "item": {
                "hoge": "aaa",
                "fuga": "bbb",
            },
            "rights": [
                {
                    "rights_name": "権利_test_1",
                    "item": {
                        "hoge-1": "aaa-1",
                        "fuga-1": "bbb-1",
                    },
                    "details_item": {
                        "d-hoge-1": "d-aaa-1",
                        "d-fuga-1": "d-bbb-1",
                    },
                },
                {
                    "rights_name": "権利_test_2",
                    "is_uploaded_details": True,
                    "item": {
                        "hoge-2": "aaa-2",
                        "fuga-2": "bbb-2",
                    },
                    "details_item": {
                        "d-hoge-2": "d-aaa-2",
                        "d-fuga-2": "d-bbb-2",
                        "アカウントアドレス": "dummy",
                        "氏名または名称": "dummy",
                        "住所": "dummy",
                        "保有口数": "dummy",
                        "一口あたりの金額": "dummy",
                        "保有残高": "dummy",
                        "取得日": "dummy",
                    },
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        _template = db.query(LedgerTemplate). \
            first()
        assert _template.token_address == token_address
        assert _template.issuer_address == issuer_address
        assert _template.ledger_name == "テスト原簿"
        assert _template.country_code == "JPN"
        assert _template.item == {
            "hoge": "aaa",
            "fuga": "bbb",
        }
        _rights_list = db.query(LedgerTemplateRights). \
            order_by(LedgerTemplateRights.id). \
            all()
        assert len(_rights_list) == 2
        _rights = _rights_list[0]
        assert _rights.id == 1
        assert _rights.token_address == token_address
        assert _rights.rights_name == "権利_test_1"
        assert _rights.item == {
            "hoge-1": "aaa-1",
            "fuga-1": "bbb-1",
        }
        assert _rights.details_item == {
            "d-hoge-1": "d-aaa-1",
            "d-fuga-1": "d-bbb-1",
        }
        assert _rights.is_uploaded_details == False
        _rights = _rights_list[1]
        assert _rights.id == 2
        assert _rights.token_address == token_address
        assert _rights.rights_name == "権利_test_2"
        assert _rights.item == {
            "hoge-2": "aaa-2",
            "fuga-2": "bbb-2",
        }
        assert _rights.details_item == {
            "d-hoge-2": "d-aaa-2",
            "d-fuga-2": "d-bbb-2",
        }
        assert _rights.is_uploaded_details == True

    # <Normal_2>
    # Update
    @mock.patch("app.model.schema.ledger.SYSTEM_LOCALE", ["JPN", "USA"])
    def test_normal_2(self, client, db):
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

        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.ledger_name = "テスト原簿"
        _template.country_code = "JPN"
        _template.item = {
            "hoge": "aaa",
            "fuga": "bbb",
        }
        db.add(_template)

        _rights_1 = LedgerTemplateRights()
        _rights_1.token_address = token_address
        _rights_1.rights_name = "権利_test_2"
        _rights_1.item = {
            "hoge-2": "aaa-2",
            "fuga-2": "bbb-2",
        }
        _rights_1.details_item = {
            "d-hoge-2": "d-aaa-2",
            "d-fuga-2": "d-bbb-2",
        }
        db.add(_rights_1)

        _rights_2 = LedgerTemplateRights()
        _rights_2.token_address = token_address
        _rights_2.rights_name = "権利_test_3"
        _rights_2.item = {
            "hoge-2": "aaa-2",
            "fuga-2": "bbb-2",
        }
        _rights_2.details_item = {
            "d-hoge-2": "d-aaa-2",
            "d-fuga-2": "d-bbb-2",
        }
        _rights_2.is_uploaded_details = True
        db.add(_rights_2)

        _rights_2_details_1 = LedgerRightsDetails()
        _rights_2_details_1.token_address = token_address
        _rights_2_details_1.rights_name = "権利_test_3"
        _rights_2_details_1.account_address = "dummy1-1"
        _rights_2_details_1.name = "dummy2-1"
        _rights_2_details_1.address = "dummy3-1"
        _rights_2_details_1.amount = 1
        _rights_2_details_1.price = 2
        _rights_2_details_1.balance = 3
        _rights_2_details_1.acquisition_date = "2020/01/01"
        db.add(_rights_2_details_1)

        _rights_2_details_2 = LedgerRightsDetails()
        _rights_2_details_2.token_address = token_address
        _rights_2_details_2.rights_name = "権利_test_3"
        _rights_2_details_2.account_address = "dummy1-2"
        _rights_2_details_2.name = "dummy2-2"
        _rights_2_details_2.address = "dummy3-2"
        _rights_2_details_2.amount = 10
        _rights_2_details_2.price = 20
        _rights_2_details_2.balance = 30
        _rights_2_details_2.acquisition_date = "2020/01/02"
        db.add(_rights_2_details_1)

        # request target API
        req_param = {
            "ledger_name": "テスト原簿_update",
            "country_code": "USA",
            "item": {
                "hoge_update": "aaa_update",
                "fuga_update": "bbb_update",
            },
            "rights": [
                {
                    "rights_name": "権利_test_1",
                    "item": {
                        "hoge-1": "aaa-1",
                        "fuga-1": "bbb-1",
                    },
                    "details_item": {
                        "d-hoge-1": "d-aaa-1",
                        "d-fuga-1": "d-bbb-1",
                    },
                },
                {
                    "rights_name": "権利_test_2",
                    "is_uploaded_details": True,
                    "item": {
                        "hoge-2_update": "aaa-2_update",
                        "fuga-2_update": "bbb-2_update",
                    },
                    "details_item": {
                        "d-hoge-2_update": "d-aaa-2_update",
                        "d-fuga-2_update": "d-bbb-2_update",
                        "account_address": "dummy",
                        "name": "dummy",
                        "address": "dummy",
                        "amount": "dummy",
                        "price": "dummy",
                        "balance": "dummy",
                        "acquisition_date": "dummy",
                    },
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        _template = db.query(LedgerTemplate). \
            first()
        assert _template.token_address == token_address
        assert _template.issuer_address == issuer_address
        assert _template.ledger_name == "テスト原簿_update"
        assert _template.country_code == "USA"
        assert _template.item == {
            "hoge_update": "aaa_update",
            "fuga_update": "bbb_update",
        }
        _rights_list = db.query(LedgerTemplateRights). \
            order_by(LedgerTemplateRights.id). \
            all()
        assert len(_rights_list) == 2
        _rights = _rights_list[0]
        assert _rights.id == 1
        assert _rights.token_address == token_address
        assert _rights.rights_name == "権利_test_2"
        assert _rights.item == {
            "hoge-2_update": "aaa-2_update",
            "fuga-2_update": "bbb-2_update",
        }
        assert _rights.details_item == {
            "d-hoge-2_update": "d-aaa-2_update",
            "d-fuga-2_update": "d-bbb-2_update",
        }
        assert _rights.is_uploaded_details == True
        _rights = _rights_list[1]
        assert _rights.id == 3
        assert _rights.token_address == token_address
        assert _rights.rights_name == "権利_test_1"
        assert _rights.item == {
            "hoge-1": "aaa-1",
            "fuga-1": "bbb-1",
        }
        assert _rights.details_item == {
            "d-hoge-1": "d-aaa-1",
            "d-fuga-1": "d-bbb-1",
        }
        assert _rights.is_uploaded_details == False
        _details_list = db.query(LedgerRightsDetails). \
            all()
        assert len(_details_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.post(
            self.base_url.format(token_address=token_address),
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
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_2>
    # Parameter Error(issuer-address)
    def test_error_2(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "ledger_name": "テスト原簿",
            "country_code": "JPN",
            "item": {
                "hoge": "aaa",
                "fuga": "bbb",
            },
            "rights": [
                {
                    "rights_name": "権利_test_1",
                    "item": {
                        "hoge-1": "aaa-1",
                        "fuga-1": "bbb-1",
                    },
                    "details_item": {
                        "d-hoge-1": "d-aaa-1",
                        "d-fuga-1": "d-bbb-1",
                    },
                },
                {
                    "rights_name": "権利_test_2",
                    "is_uploaded_details": True,
                    "item": {
                        "hoge-2": "aaa-2",
                        "fuga-2": "bbb-2",
                    },
                    "details_item": {
                        "d-hoge-2": "d-aaa-2",
                        "d-fuga-2": "d-bbb-2",
                        "アカウントアドレス": "dummy",
                        "氏名または名称": "dummy",
                        "住所": "dummy",
                        "保有口数": "dummy",
                        "一口あたりの金額": "dummy",
                        "保有残高": "dummy",
                        "取得日": "dummy",
                    },
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
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
    # Parameter Error(body request)
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "ledger_name": "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                           "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                           "1",
            "country_code": "USA",
            "item": {
                "hoge": "aaa",
                "fuga": "bbb",
            },
            "rights": [],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
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
                    "loc": ["body", "ledger_name"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "country_code"],
                    "msg": 'Not supported country_code',
                    "type": "value_error"
                },
                {
                    "loc": ["body", "rights"],
                    "msg": "The length must be greater than or equal to 1",
                    "type": "value_error"
                }
            ]
        }

    # <Error_4>
    # Parameter Error(body request:rights)
    def test_error_4(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "ledger_name": "テスト原簿",
            "country_code": "JPN",
            "item": {
                "hoge": "aaa",
                "fuga": "bbb",
            },
            "rights": [
                {
                    "rights_name": "12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901",
                    "item": {
                        "hoge-1": "aaa-1",
                        "fuga-1": "bbb-1",
                    },
                    "details_item": {
                        "d-hoge-1": "d-aaa-1",
                        "d-fuga-1": "d-bbb-1",
                    },
                },
                {
                    "rights_name": "権利_test_2",
                    "is_uploaded_details": True,
                    "item": {
                        "hoge-2": "aaa-2",
                        "fuga-2": "bbb-2",
                    },
                    "details_item": {
                        "d-hoge-2": "d-aaa-2",
                        "d-fuga-2": "d-bbb-2",
                        "アカウントアドレス": "dummy",
                        "氏名または名称": "dummy",
                        "住所": "dummy",
                        "保有口数": "dummy",
                        "一口あたりの金額": "dummy",
                        "保有残高": "dummy",
                        "取得日": "dummy",
                    },
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
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
                    "loc": ["body", "rights", 0, "rights_name"],
                    "msg": "The length must be less than or equal to 100",
                    "type": "value_error"
                }
            ]
        }

    # <Error_4>
    # Token Not Found
    def test_error_4(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "ledger_name": "テスト原簿",
            "country_code": "JPN",
            "item": {
                "hoge": "aaa",
                "fuga": "bbb",
            },
            "rights": [
                {
                    "rights_name": "権利_test_1",
                    "item": {
                        "hoge-1": "aaa-1",
                        "fuga-1": "bbb-1",
                    },
                    "details_item": {
                        "d-hoge-1": "d-aaa-1",
                        "d-fuga-1": "d-bbb-1",
                    },
                },
                {
                    "rights_name": "権利_test_2",
                    "is_uploaded_details": True,
                    "item": {
                        "hoge-2": "aaa-2",
                        "fuga-2": "bbb-2",
                    },
                    "details_item": {
                        "d-hoge-2": "d-aaa-2",
                        "d-fuga-2": "d-bbb-2",
                        "アカウントアドレス": "dummy",
                        "氏名または名称": "dummy",
                        "住所": "dummy",
                        "保有口数": "dummy",
                        "一口あたりの金額": "dummy",
                        "保有残高": "dummy",
                        "取得日": "dummy",
                    },
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
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
