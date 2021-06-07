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


class TestAppRoutersLedgerTokenAddressDetailsDataDataIdDELETE:
    # target API endpoint
    base_url = "/ledger/{token_address}/details_data/{data_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        data_id = "data_id_1"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _details_1_data_1 = LedgerDetailsData()
        _details_1_data_1.token_address = token_address
        _details_1_data_1.data_id = data_id
        _details_1_data_1.name = "name_test_0"
        _details_1_data_1.address = "address_test_0"
        _details_1_data_1.amount = 0
        _details_1_data_1.price = 1
        _details_1_data_1.balance = 2
        _details_1_data_1.acquisition_date = "2000/12/31"
        db.add(_details_1_data_1)

        _details_1_data_2 = LedgerDetailsData()
        _details_1_data_2.token_address = token_address
        _details_1_data_2.data_id = data_id
        _details_1_data_2.name = "name_test_0"
        _details_1_data_2.address = "address_test_0"
        _details_1_data_2.amount = 0
        _details_1_data_2.price = 1
        _details_1_data_2.balance = 2
        _details_1_data_2.acquisition_date = "2000/12/31"
        db.add(_details_1_data_2)

        # Not Target Data
        _details_1_data_3 = LedgerDetailsData()
        _details_1_data_3.token_address = token_address
        _details_1_data_3.data_id = "not_target"
        _details_1_data_3.name = "name_test_0"
        _details_1_data_3.address = "address_test_0"
        _details_1_data_3.amount = 0
        _details_1_data_3.price = 1
        _details_1_data_3.balance = 2
        _details_1_data_3.acquisition_date = "2000/12/31"
        db.add(_details_1_data_3)

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address, data_id=data_id),
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        _details_data_list = db.query(LedgerDetailsData).all()
        assert len(_details_data_list) == 1
        assert _details_data_list[0].id == 3
        assert _details_data_list[0].token_address == token_address
        assert _details_data_list[0].data_id == "not_target"

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Parameter Error(issuer-address)
    def test_error_1(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        data_id = "data_id_1"

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address, data_id=data_id)
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
        data_id = "data_id_1"

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address, data_id=data_id),
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
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        data_id = "data_id_1"

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address, data_id=data_id),
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
    # Processing Token
    def test_error_4(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        data_id = "data_id_1"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 0
        db.add(_token)

        # request target API
        resp = client.delete(
            self.base_url.format(token_address=token_address, data_id=data_id),
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
