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

from app.model.db import Token, TokenType, BondLedger
from tests.account_config import config_eth_account


class TestAppBondLedgerTokenAddressHistoryLedgerIdGET:
    # target API endpoint
    base_url = "/bond_ledger/{}/history/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Localized:JPN
    @mock.patch("app.routers.localized.bond_ledger_JPN.retrieve_bond_ledger_history")
    def test_normal_1(self, mock_localized_func, client, db):
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

        _bond_ledger = BondLedger()
        _bond_ledger.token_address = token_address
        _bond_ledger.ledger = {}
        _bond_ledger.country_code = "JPN"
        db.add(_bond_ledger)

        mock_resp = {
            "テスト1": "test1",
            "テスト2": "test2",
        }
        mock_localized_func.side_effect = [
            mock_resp
        ]

        # request target API
        req_param = {
            "latest_flg": 0
        }
        resp = client.get(
            self.base_url.format(token_address, 1),
            params=req_param,
            headers={
                "country-code": "jpn",
                "issuer-address": issuer_address,
            }
        )

        # assertion
        mock_localized_func.assert_any_call(token_address, 1, issuer_address, 0, db)

        assert resp.status_code == 200
        assert resp.json() == mock_resp

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address, 1),
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
                    "loc": ["header", "country-code"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_2>
    # Parameter Error(latest_flg range)
    def test_error_2(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "latest_flg": -1
        }
        resp = client.get(
            self.base_url.format(token_address, 1),
            params=req_param,
            headers={
                "country-code": "usa",
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

        # request target API
        req_param = {
            "latest_flg": 2
        }
        resp = client.get(
            self.base_url.format(token_address, 1),
            params=req_param,
            headers={
                "country-code": "usa",
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

    # <Error_3>
    # Not Supported
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "latest_flg": 0
        }
        resp = client.get(
            self.base_url.format(token_address, 1),
            params=req_param,
            headers={
                "country-code": "usa",
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
            "detail": "Not Supported country-code:usa"
        }

    # <Error_4>
    # Token Not Found
    def test_error_4(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "latest_flg": 0
        }
        resp = client.get(
            self.base_url.format(token_address, 1),
            params=req_param,
            headers={
                "country-code": "jpn",
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
    # Ledger Not Found
    def test_error_5(self, client, db):
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
            "latest_flg": 0
        }
        resp = client.get(
            self.base_url.format(token_address, 1),
            params=req_param,
            headers={
                "country-code": "jpn",
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
