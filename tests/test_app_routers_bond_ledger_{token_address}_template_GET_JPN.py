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
from app.model.db import Token, TokenType, CorporateBondLedgerTemplateJPN
from tests.account_config import config_eth_account


class TestAppBondLedgerTokenAddressTemplateGETJPN:
    # target API endpoint
    base_url = "/bond_ledger/{}/template"

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

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
            params={
                "locale": "jpn",
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "token_address": token_address,
            "bond_name": "bond_name_test",
            "bond_description": "bond_description_test",
            "bond_type": "bond_type_test",
            "total_amount": 10,
            "face_value": 20,
            "payment_amount": 30,
            "payment_date": "20211231",
            "payment_status": False,
            "hq_name": "hq_name_test",
            "hq_address": "hq_address_test",
            "hq_office_address": "hq_office_address_test",
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # LedgerTemplate Not Found
    def test_error_1(self, client, db):
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
            self.base_url.format(token_address),
            params={
                "locale": "jpn",
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
