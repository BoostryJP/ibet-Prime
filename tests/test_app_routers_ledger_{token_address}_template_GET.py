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
    LedgerTemplate,
    LedgerTemplateRights
)
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressHistoryTemplateGET:
    # target API endpoint
    base_url = "/ledger/{token_address}/template"

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
        db.add(_rights_1)

        _rights_2 = LedgerTemplateRights()
        _rights_2.token_address = token_address
        _rights_2.rights_name = "権利_test_2"
        _rights_2.item = {
            "test3": "a",
            "test4": "b"
        }
        _rights_2.details_item = {
            "d-test3": "a",
            "d-test4": "b"
        }
        _rights_2.is_uploaded_details = True
        db.add(_rights_2)

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "ledger_name": "テスト原簿",
            "country_code": "JPN",
            "item": {
                "hoge": "aaaa",
                "fuga": "bbbb",
            },
            "rights": [
                {
                    "rights_name": "権利_test_1",
                    "item": {
                        "test1": "a",
                        "test2": "b"
                    },
                    "details_item": {
                        "d-test1": "a",
                        "d-test2": "b"
                    },
                    "is_uploaded_details": False,
                },
                {
                    "rights_name": "権利_test_2",
                    "item": {
                        "test3": "a",
                        "test4": "b"
                    },
                    "details_item": {
                        "d-test3": "a",
                        "d-test4": "b"
                    },
                    "is_uploaded_details": True,
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
                }
            ]
        }

    # <Error_2>
    # Parameter Error(issuer-address)
    def test_error_2(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
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
    # Token Not Found
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
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

    # <Error_4>
    # Ledger Template Not Found
    def test_error_4(self, client, db):
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
        resp = client.get(
            self.base_url.format(token_address=token_address),
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
