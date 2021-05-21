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
from app.model.db import (
    Token,
    TokenType,
    LedgerRightsDetails,
    LedgerTemplate,
    LedgerTemplateRights
)
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressRightsDetailsPOST:
    # target API endpoint
    base_url = "/ledger/{token_address}/rights_details"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
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

        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.ledger_name = "テスト原簿"
        _template.country_code = "JPN"
        _template.item = {
            "hoge": "aaaa",
            "fuga": "bbbb",
        }
        db.add(_template)

        _rights_1 = LedgerTemplateRights()
        _rights_1.token_address = token_address
        _rights_1.rights_name = "権利_test_1"
        _rights_1.item = {
            "test1": "a",
            "test2": "b"
        }
        _rights_1.details_item = {
            "d-test1": "a",
            "d-test2": "b"
        }
        _rights_1.is_uploaded_details = True
        db.add(_rights_1)

        _rights_1_details_1 = LedgerRightsDetails()
        _rights_1_details_1.token_address = token_address
        _rights_1_details_1.rights_name = "権利_test_1"
        _rights_1_details_1.account_address = "account_address_test_0"
        _rights_1_details_1.name = "name_test_0"
        _rights_1_details_1.address = "address_test_0"
        _rights_1_details_1.amount = 0
        _rights_1_details_1.price = 1
        _rights_1_details_1.balance = 2
        _rights_1_details_1.acquisition_date = "2000/12/31"
        db.add(_rights_1_details_1)

        # request target API
        req_param = {
            "rights_name": "権利_test_1",
            "details": [
                {
                    "account_address": "account_address_test_1",
                    "name": "name_test_1",
                    "address": "address_test_1",
                    "amount": 100,
                    "price": 200,
                    "balance": 20000,
                    "acquisition_date": "2020/01/01",
                },
                {
                    "account_address": "account_address_test_2",
                    "name": "name_test_2",
                    "address": "address_test_2",
                    "amount": 10,
                    "price": 20,
                    "balance": 200,
                    "acquisition_date": "2020/01/02",
                },
            ]
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
        _details_list = db.query(LedgerRightsDetails). \
            order_by(LedgerRightsDetails.id). \
            all()
        assert len(_details_list) == 2
        _details = _details_list[0]
        assert _details.id == 2
        assert _details.rights_name == "権利_test_1"
        assert _details.account_address == "account_address_test_1"
        assert _details.name == "name_test_1"
        assert _details.address == "address_test_1"
        assert _details.amount == 100
        assert _details.price == 200
        assert _details.balance == 20000
        assert _details.acquisition_date == "2020/01/01"
        _details = _details_list[1]
        assert _details.id == 3
        assert _details.rights_name == "権利_test_1"
        assert _details.account_address == "account_address_test_2"
        assert _details.name == "name_test_2"
        assert _details.address == "address_test_2"
        assert _details.amount == 10
        assert _details.price == 20
        assert _details.balance == 200
        assert _details.acquisition_date == "2020/01/02"

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
            "rights_name": "権利_test_1",
            "details": [
                {
                    "account_address": "account_address_test_1",
                    "name": "name_test_1",
                    "address": "address_test_1",
                    "amount": 100,
                    "price": 200,
                    "balance": 20000,
                    "acquisition_date": "2020/01/01",
                },
                {
                    "account_address": "account_address_test_2",
                    "name": "name_test_2",
                    "address": "address_test_2",
                    "amount": 10,
                    "price": 20,
                    "balance": 200,
                    "acquisition_date": "2020/01/02",
                },
            ]
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
            "rights_name": "12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901",
            "details": [
                {
                    "account_address": "1234567890123456789012345678901234567890123",
                    "name": "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                            "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                            "1",
                    "address": "address_test_1",
                    "amount": 100,
                    "price": 200,
                    "balance": 20000,
                    "acquisition_date": "2020/01/01",
                },
                {
                    "account_address": "account_address_test_2",
                    "name": "name_test_2",
                    "address": "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                               "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                               "1",
                    "amount": 10,
                    "price": 20,
                    "balance": 200,
                    "acquisition_date": "2020/02/31",
                },
            ]
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
                    "loc": ["body", "details", 0, "account_address"],
                    "msg": "The length must be less than or equal to 42",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "details", 0, "name"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "details", 1, "address"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "details", 1, "acquisition_date"],
                    "msg": "The date format must be YYYY/MM/DD",
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
            "rights_name": "権利_test_1",
            "details": [
                {
                    "account_address": "account_address_test_1",
                    "name": "name_test_1",
                    "address": "address_test_1",
                    "amount": 100,
                    "price": 200,
                    "balance": 20000,
                    "acquisition_date": "2020/01/01",
                },
                {
                    "account_address": "account_address_test_2",
                    "name": "name_test_2",
                    "address": "address_test_2",
                    "amount": 10,
                    "price": 20,
                    "balance": 200,
                    "acquisition_date": "2020/01/02",
                },
            ]
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

    # <Error_5>
    # Ledger Template Not Found
    def test_error_5(self, client, db):
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
        req_param = {
            "rights_name": "権利_test_1",
            "details": [
                {
                    "account_address": "account_address_test_1",
                    "name": "name_test_1",
                    "address": "address_test_1",
                    "amount": 100,
                    "price": 200,
                    "balance": 20000,
                    "acquisition_date": "2020/01/01",
                },
                {
                    "account_address": "account_address_test_2",
                    "name": "name_test_2",
                    "address": "address_test_2",
                    "amount": 10,
                    "price": 20,
                    "balance": 200,
                    "acquisition_date": "2020/01/02",
                },
            ]
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
            "detail": "ledger template does not exist"
        }

    # <Error_6>
    # Ledger Rights Template Not Found
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

        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.ledger_name = "テスト原簿"
        _template.country_code = "JPN"
        _template.item = {
            "hoge": "aaaa",
            "fuga": "bbbb",
        }
        db.add(_template)

        _rights_1 = LedgerTemplateRights()
        _rights_1.token_address = token_address
        _rights_1.rights_name = "権利_test_1"
        _rights_1.item = {
            "test1": "a",
            "test2": "b"
        }
        _rights_1.details_item = {
            "d-test1": "a",
            "d-test2": "b"
        }
        _rights_1.is_uploaded_details = False  # not upload rights
        db.add(_rights_1)

        # request target API
        req_param = {
            "rights_name": "権利_test_1",
            "details": [
                {
                    "account_address": "account_address_test_1",
                    "name": "name_test_1",
                    "address": "address_test_1",
                    "amount": 100,
                    "price": 200,
                    "balance": 20000,
                    "acquisition_date": "2020/01/01",
                },
                {
                    "account_address": "account_address_test_2",
                    "name": "name_test_2",
                    "address": "address_test_2",
                    "amount": 10,
                    "price": 20,
                    "balance": 200,
                    "acquisition_date": "2020/01/02",
                },
            ]
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
            "detail": "ledger rights template does not exist"
        }
