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

from app.model.db import Token, TokenType
from tests.account_config import config_eth_account


class TestAppBondLedgerTokenAddressTemplateGET:
    # target API endpoint
    base_url = "/bond_ledger/{}/template"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Localized:JPN
    @mock.patch("app.routers.localized.bond_ledger_JPN.retrieve_bond_ledger_template")
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

        mock_resp = {
            "token_address": token_address,
            "bond_name": "bond_name_test",
            "bond_description": "bond_description_test",
            "bond_type": "bond_type_test",
            "total_amount": 10,
            "face_value": 20,
            "payment_amount": 30,
            "payment_date": "20211231",
            "payment_status": False,
            "ledger_admin_name": "ledger_admin_name_test",
            "ledger_admin_address": "ledger_admin_address_test",
            "ledger_admin_location": "ledger_admin_location_test",
        }
        mock_localized_func.side_effect = [
            mock_resp
        ]

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
            headers={
                "country-code": "jpn",
                "issuer-address": issuer_address,
            }
        )

        # assertion
        mock_localized_func.assert_any_call(token_address, issuer_address, db)

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
            self.base_url.format(token_address),
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
    # Not Supported
    def test_error_2(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
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

    # <Error_3>
    # Token Not Found
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
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
