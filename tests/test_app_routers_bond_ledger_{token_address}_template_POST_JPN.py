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
from unittest.mock import ANY

from app.model.schema import CreateUpdateBondLedgerTemplateRequestJPN
from app.model.db import Token, TokenType, CorporateBondLedgerTemplateJPN
from tests.account_config import config_eth_account


class TestAppBondLedgerTokenAddressTemplatePOSTJPN:
    # target API endpoint
    base_url = "/bond_ledger/{}/template"

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
            "bond_name": "bond_name_test",
            "bond_description": "bond_description_test",
            "bond_type": "bond_type_test",
            "total_amount": 10,
            "face_value": 20,
            "payment_amount": 30,
            "payment_date": "20211231",
            "payment_status": False,
            "ledger_admin_name": "ledger_admin_name_test",
            "ledger_admin_headquarters": "ledger_admin_headquarters_test",
            "ledger_admin_office_address": "ledger_admin_office_address_test",
        }
        resp = client.post(
            self.base_url.format(token_address),
            json=req_param,
            params={
                "locale": "jpn",
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        _templete = db.query(CorporateBondLedgerTemplateJPN).first()
        assert _templete is not None
        assert _templete.token_address == token_address
        assert _templete.issuer_address == issuer_address
        assert _templete.bond_name == "bond_name_test"
        assert _templete.bond_description == "bond_description_test"
        assert _templete.bond_type == "bond_type_test"
        assert _templete.total_amount == 10
        assert _templete.face_value == 20
        assert _templete.payment_amount == 30
        assert _templete.payment_date == "20211231"
        assert _templete.payment_status == False
        assert _templete.ledger_admin_name == "ledger_admin_name_test"
        assert _templete.ledger_admin_headquarters == "ledger_admin_headquarters_test"
        assert _templete.ledger_admin_office_address == "ledger_admin_office_address_test"

    # <Normal_2>
    # Update
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

        _templete = CorporateBondLedgerTemplateJPN()
        _templete.token_address = token_address
        _templete.issuer_address = issuer_address
        _templete.bond_name = "bond_name_test"
        _templete.bond_description = "bond_description_test"
        _templete.bond_type = "bond_type_test"
        _templete.total_amount = 10
        _templete.face_value = 20
        _templete.payment_amount = 30
        _templete.payment_date = "20211231"
        _templete.payment_status = False
        _templete.ledger_admin_name = "ledger_admin_name_test"
        _templete.ledger_admin_headquarters = "ledger_admin_headquarters_test"
        _templete.ledger_admin_office_address = "ledger_admin_office_address_test"

        # request target API
        req_param = {
            "bond_name": "bond_name_test_mod",
            "bond_description": "bond_description_test_mod",
            "bond_type": "bond_type_test_mod",
            "total_amount": 40,
            "face_value": 50,
            "payment_amount": 60,
            "payment_date": "20301231",
            "payment_status": True,
            "ledger_admin_name": "ledger_admin_name_test_mod",
            "ledger_admin_headquarters": "ledger_admin_headquarters_test_mod",
            "ledger_admin_office_address": "ledger_admin_office_address_test_mod",
        }
        resp = client.post(
            self.base_url.format(token_address),
            json=req_param,
            params={
                "locale": "jpn",
            },
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        _templete = db.query(CorporateBondLedgerTemplateJPN).first()
        assert _templete is not None
        assert _templete.token_address == token_address
        assert _templete.issuer_address == issuer_address
        assert _templete.bond_name == "bond_name_test_mod"
        assert _templete.bond_description == "bond_description_test_mod"
        assert _templete.bond_type == "bond_type_test_mod"
        assert _templete.total_amount == 40
        assert _templete.face_value == 50
        assert _templete.payment_amount == 60
        assert _templete.payment_date == "20301231"
        assert _templete.payment_status == True
        assert _templete.ledger_admin_name == "ledger_admin_name_test_mod"
        assert _templete.ledger_admin_headquarters == "ledger_admin_headquarters_test_mod"
        assert _templete.ledger_admin_office_address == "ledger_admin_office_address_test_mod"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error(Required)
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

        _templete = CorporateBondLedgerTemplateJPN()
        _templete.token_address = token_address
        _templete.issuer_address = issuer_address
        _templete.bond_name = "bond_name_test"
        _templete.bond_description = "bond_description_test"
        _templete.bond_type = "bond_type_test"
        _templete.total_amount = 10
        _templete.face_value = 20
        _templete.payment_amount = 30
        _templete.payment_date = "20211231"
        _templete.payment_status = False
        _templete.ledger_admin_name = "ledger_admin_name_test"
        _templete.ledger_admin_headquarters = "ledger_admin_headquarters_test"
        _templete.ledger_admin_office_address = "ledger_admin_office_address_test"

        # request target API
        req_param = {}
        resp = client.post(
            self.base_url.format(token_address),
            json=req_param,
            params={
                "locale": "jpn",
            },
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
                    "loc": ["body", "bond_name"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "bond_description"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "bond_type"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "total_amount"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "face_value"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "ledger_admin_name"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "ledger_admin_headquarters"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "ledger_admin_office_address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_2>
    # Parameter Error(Specific)
    def test_error_2(self, client, db):
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

        _templete = CorporateBondLedgerTemplateJPN()
        _templete.token_address = token_address
        _templete.issuer_address = issuer_address
        _templete.bond_name = "bond_name_test"
        _templete.bond_description = "bond_description_test"
        _templete.bond_type = "bond_type_test"
        _templete.total_amount = 10
        _templete.face_value = 20
        _templete.payment_amount = 30
        _templete.payment_date = "20211231"
        _templete.payment_status = False
        _templete.ledger_admin_name = "ledger_admin_name_test"
        _templete.ledger_admin_headquarters = "ledger_admin_headquarters_test"
        _templete.ledger_admin_office_address = "ledger_admin_office_address_test"

        # request target API
        req_param = {
            "bond_name": "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901",
            "bond_description": "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "1234567890123456789012345678901234567890123456789012345678901234567890"
                                "123456789012345678901",
            "bond_type": "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                         "123456789012345678901",
            "total_amount": 1_000_000_000_001,
            "face_value": 100_000_001,
            "payment_amount": 1_000_000_000_001,
            "payment_date": "2021/12/31",
            "ledger_admin_name": "1234567890123456789012345678901234567890123456789012345678901234567890"
                                 "1234567890123456789012345678901234567890123456789012345678901234567890"
                                 "1234567890123456789012345678901234567890123456789012345678901",
            "ledger_admin_headquarters": "1234567890123456789012345678901234567890123456789012345678901234567890"
                                         "1234567890123456789012345678901234567890123456789012345678901234567890"
                                         "1234567890123456789012345678901234567890123456789012345678901",
            "ledger_admin_office_address": "1234567890123456789012345678901234567890123456789012345678901234567890"
                                           "1234567890123456789012345678901234567890123456789012345678901234567890"
                                           "1234567890123456789012345678901234567890123456789012345678901",
        }
        resp = client.post(
            self.base_url.format(token_address),
            json=req_param,
            params={
                "locale": "jpn",
            },
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
                    "loc": ["body", "bond_name"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "bond_description"],
                    "msg": "The length must be less than or equal to 1000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "bond_type"],
                    "msg": "The length must be less than or equal to 1000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "total_amount"],
                    "msg": "The range must be 0 to 1,000,000,000,000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "face_value"],
                    "msg": "The range must be 0 to 100,000,000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "payment_amount"],
                    "msg": "The range must be 0 to 1,000,000,000,000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "payment_date"],
                    "msg": "The date format must be YYYYMMDD",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "ledger_admin_name"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "ledger_admin_headquarters"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "ledger_admin_office_address"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                }
            ]
        }

        # request target API
        req_param = {
            "bond_name": "bond_name_test_mod",
            "bond_description": "bond_description_test_mod",
            "bond_type": "bond_type_test_mod",
            "total_amount": -1,
            "face_value": -1,
            "payment_amount": -1,
            "payment_date": "20301131",  # Invalid date
            "payment_status": True,
            "ledger_admin_name": "ledger_admin_name_test_mod",
            "ledger_admin_headquarters": "ledger_admin_headquarters_test_mod",
            "ledger_admin_office_address": "ledger_admin_office_address_test_mod",
        }
        resp = client.post(
            self.base_url.format(token_address),
            json=req_param,
            params={
                "locale": "jpn",
            },
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
                    "loc": ["body", "total_amount"],
                    "msg": "The range must be 0 to 1,000,000,000,000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "face_value"],
                    "msg": "The range must be 0 to 100,000,000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "payment_amount"],
                    "msg": "The range must be 0 to 1,000,000,000,000",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "payment_date"],
                    "msg": "The date format must be YYYYMMDD",
                    "type": "value_error"
                },
            ]
        }
