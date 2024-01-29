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

from sqlalchemy import select

from app.model.db import (
    LedgerDetailsDataType,
    LedgerDetailsTemplate,
    LedgerTemplate,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressTemplateDELETE:
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.token_name = "テスト原簿"
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "hoge": "aaaa",
                "fuga": "bbbb",
            },
        ]
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge": "f-aaaa",
                "f-fuga": "f-bbbb",
            },
        ]
        db.add(_template)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_1"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {"test1": "a", "test2": "b"},
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {"f-test1": "a", "f-test2": "b"},
        ]
        _details_1.data_type = LedgerDetailsDataType.IBET_FIN.value
        _details_1.data_source = token_address
        db.add(_details_1)

        _details_2 = LedgerDetailsTemplate()
        _details_2.token_address = token_address
        _details_2.token_detail_type = "権利_test_2"
        _details_2.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {"test3": "a", "test4": "b"},
        ]
        _details_2.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {"f-test3": "a", "f-test4": "b"},
        ]
        _details_2.data_type = LedgerDetailsDataType.DB.value
        _details_2.data_source = "data_id_2"
        db.add(_details_2)

        db.commit()

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None
        _template_list = db.scalars(select(LedgerTemplate)).all()
        assert len(_template_list) == 0
        _details_list = db.scalars(select(LedgerDetailsTemplate)).all()
        assert len(_details_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address),
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # <Error_2>
    # Parameter Error(issuer-address)
    def test_error_2(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address),
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

    # <Error_3>
    # Token Not Found
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address),
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

    # <Error_4>
    # Processing Token
    def test_error_4(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        db.commit()

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address),
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

    # <Error_5>
    # Ledger Template Not Found
    def test_error_5(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_23_12
        db.add(_token)

        db.commit()

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "ledger template does not exist",
        }
