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
    LedgerDetailsData
)
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressDetailsDataPOST:
    # target API endpoint
    base_url = "/ledger/{token_address}/details_data"

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
        db.add(_token)

        # request target API
        req_param = [
            {
                "name": "name_test_1",
                "address": "address_test_1",
                "amount": 100,
                "price": 200,
                "balance": 20000,
                "acquisition_date": "2020/01/01",
            },
            {
                "name": "name_test_2",
                "address": "address_test_2",
                "amount": 10,
                "price": 20,
                "balance": 200,
                "acquisition_date": "2020/01/02",
            },
        ]
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["data_id"] is not None
        _details_data_list = db.query(LedgerDetailsData). \
            order_by(LedgerDetailsData.id). \
            all()
        assert len(_details_data_list) == 2
        _details_data = _details_data_list[0]
        assert _details_data.id == 1
        assert _details_data.data_id == resp.json()["data_id"]
        assert _details_data.name == "name_test_1"
        assert _details_data.address == "address_test_1"
        assert _details_data.amount == 100
        assert _details_data.price == 200
        assert _details_data.balance == 20000
        assert _details_data.acquisition_date == "2020/01/01"
        _details_data = _details_data_list[1]
        assert _details_data.id == 2
        assert _details_data.data_id == resp.json()["data_id"]
        assert _details_data.name == "name_test_2"
        assert _details_data.address == "address_test_2"
        assert _details_data.amount == 10
        assert _details_data.price == 20
        assert _details_data.balance == 200
        assert _details_data.acquisition_date == "2020/01/02"

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
        req_param = [
            {
                "name": "name_test_1",
                "address": "address_test_1",
                "amount": 100,
                "price": 200,
                "balance": 20000,
                "acquisition_date": "2020/01/01",
            },
            {
                "name": "name_test_2",
                "address": "address_test_2",
                "amount": 10,
                "price": 20,
                "balance": 200,
                "acquisition_date": "2020/01/02",
            },
        ]
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
        req_param = [
            {
                "name": "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                        "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                        "1",
                "address": "address_test_1",
                "amount": 2 ** 31,
                "price": -1,
                "balance": 2 ** 31,
                "acquisition_date": "2020/01/01a",
            },
            {
                "name": "name_test_2",
                "address": "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                           "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
                           "1",
                "amount": -1,
                "price": 2 ** 31,
                "balance": -1,
                "acquisition_date": "2020/02/31",
            },
        ]
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
                    "ctx": {"limit_value": 200},
                    "loc": ["body", 0, "name"],
                    "msg": "ensure this value has at most 200 characters",
                    "type": "value_error.any_str.max_length"
                },
                {
                    "ctx": {"limit_value": 2 ** 31 - 1},
                    "loc": ["body", 0, "amount"],
                    "msg": "ensure this value is less than or equal to 2147483647",
                    "type": "value_error.number.not_le"
                },
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["body", 0, "price"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                },
                {
                    "ctx": {"limit_value": 2 ** 31 - 1},
                    "loc": ["body", 0, "balance"],
                    "msg": "ensure this value is less than or equal to 2147483647",
                    "type": "value_error.number.not_le"
                },
                {
                    "ctx": {"limit_value": 10},
                    "loc": ["body", 0, "acquisition_date"],
                    "msg": "ensure this value has at most 10 characters",
                    "type": "value_error.any_str.max_length"
                },
                {
                    "ctx": {"limit_value": 200},
                    "loc": ["body", 1, "address"],
                    "msg": "ensure this value has at most 200 characters",
                    "type": "value_error.any_str.max_length"
                },
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["body", 1, "amount"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                },
                {
                    "ctx": {"limit_value": 2 ** 31 - 1},
                    "loc": ["body", 1, "price"],
                    "msg": "ensure this value is less than or equal to 2147483647",
                    "type": "value_error.number.not_le"
                },
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["body", 1, "balance"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                },
                {
                    "loc": ["body", 1, "acquisition_date"],
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
        req_param = [
            {
                "name": "name_test_1",
                "address": "address_test_1",
                "amount": 100,
                "price": 200,
                "balance": 20000,
                "acquisition_date": "2020/01/01",
            },
            {
                "name": "name_test_2",
                "address": "address_test_2",
                "amount": 10,
                "price": 20,
                "balance": 200,
                "acquisition_date": "2020/01/02",
            },
        ]
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
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
        req_param = [
            {
                "name": "name_test_1",
                "address": "address_test_1",
                "amount": 100,
                "price": 200,
                "balance": 20000,
                "acquisition_date": "2020/01/01",
            },
            {
                "name": "name_test_2",
                "address": "address_test_2",
                "amount": 10,
                "price": 20,
                "balance": 200,
                "acquisition_date": "2020/01/02",
            },
        ]
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
            "detail": "this token is temporarily unavailable"
        }
