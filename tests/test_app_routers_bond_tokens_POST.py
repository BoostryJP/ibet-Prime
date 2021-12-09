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
from unittest.mock import (
    ANY,
    patch
)
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware

import config
import string
import random
from app.exceptions import SendTransactionError
from app.model.db import (
    Account,
    Token,
    TokenType,
    AdditionalTokenInfo,
    UpdateToken,
    IDXPosition
)
from app.utils.e2ee_utils import E2EEUtils
from app.model.blockchain.token import IbetStraightBondContract
from app.model.blockchain.token_list import TokenListContract
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAppRoutersBondTokensPOST:
    # target API endpoint
    apiurl = "/bond/tokens"

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    # create only
    def test_normal_1(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token_before = db.query(Token).all()

        # mock
        IbetStraightBondContract_create = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1")
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None
        )

        with IbetStraightBondContract_create, \
                TokenListContract_register:
            # request target api
            req_param = {
                "name": "name_test1",
                "total_supply": 10000,
                "face_value": 200,
                "purpose": "purpose_test1",
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

            # assertion
            IbetStraightBondContract.create.assert_called_with(
                args=[
                    "name_test1", "", 10000, 200, "", 0,
                    "", "", "purpose_test1"
                ],
                tx_from=test_account["address"],
                private_key=ANY
            )
            TokenListContract.register.assert_called_with(
                token_list_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
                token_address="contract_address_test1",
                token_template=TokenType.IBET_STRAIGHT_BOND,
                account_address=test_account["address"],
                private_key=ANY
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = db.query(Token).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)
            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_STRAIGHT_BOND
            assert token_1.tx_hash == "tx_hash_test1"
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 1

            position = db.query(IDXPosition).first()
            assert position.token_address == "contract_address_test1"
            assert position.account_address == test_account["address"]
            assert position.balance == req_param["total_supply"]
            assert position.exchange_balance == 0
            assert position.exchange_commitment == 0
            assert position.pending_transfer == 0

            update_token = db.query(UpdateToken).first()
            assert update_token is None

            additional_info = db.query(AdditionalTokenInfo).first()
            assert additional_info is None

    # <Normal_2>
    # include updates
    def test_normal_2(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token_before = db.query(Token).all()

        # mock
        IbetStraightBondContract_create = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1")
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None
        )

        with IbetStraightBondContract_create, \
                TokenListContract_register:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 10000,
                "face_value": 200,
                "redemption_date": "20211231",
                "redemption_value": 4000,
                "return_date": "20211231",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.0001,  # update
                "interest_payment_date": ["0331", "0930"],  # update
                "transferable": False,  # update
                "image_url": ["image_1"],  # update
                "status": False,  # update
                "is_offering": True,  # update
                "is_redeemed": True,  # update
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test",  # update
                "transfer_approval_required": True,  # update
                "is_manual_transfer_approval": True  # update
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

            # assertion
            IbetStraightBondContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    10000,
                    200,
                    "20211231",
                    4000,
                    "20211231",
                    "return_amount_test1",
                    "purpose_test1"
                ],
                tx_from=test_account["address"],
                private_key=ANY
            )

            TokenListContract.register.assert_not_called()

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 0

            token_after = db.query(Token).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)
            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_STRAIGHT_BOND
            assert token_1.tx_hash == "tx_hash_test1"
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 0

            position = db.query(IDXPosition).first()
            assert position is None

            update_token = db.query(UpdateToken).first()
            assert update_token.id == 1
            assert update_token.token_address == "contract_address_test1"
            assert update_token.issuer_address == test_account["address"]
            assert update_token.type == TokenType.IBET_STRAIGHT_BOND
            assert update_token.arguments == req_param
            assert update_token.status == 0
            assert update_token.trigger == "Issue"

            additional_info = db.query(AdditionalTokenInfo).first()
            assert additional_info.id == 1
            assert additional_info.token_address == "contract_address_test1"
            assert additional_info.is_manual_transfer_approval is True
            assert isinstance(additional_info.block_number, int)
            assert isinstance(additional_info.block_timestamp, datetime)

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation Error
    # missing fields
    def test_error_1(self, client, db):
        # request target api
        resp = client.post(
            self.apiurl
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

    # <Error_2_1>
    # Validation Error
    # format error
    def test_error_2_1(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 12.34567,
            "interest_payment_date": [
                "0101",
                "0201",
                "0301",
                "0401",
                "0501",
                "0601",
                "0701",
                "0801",
                "0901",
                "1001",
                "1101",
                "1201",
                "1231"
            ],
            "tradable_exchange_contract_address": "0x0",
            "personal_info_contract_address": "0x0",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account["address"]
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
                    "loc": [
                        "body",
                        "interest_rate"
                    ],
                    "msg": "interest_rate must be less than or equal to four decimal places",
                    "type": "value_error"
                },
                {
                    "loc": [
                        "body",
                        "interest_payment_date"
                    ],
                    "msg": "list length of interest_payment_date must be less than 13",
                    "type": "value_error"
                },
                {
                    "loc": [
                        "body",
                        "tradable_exchange_contract_address"
                    ],
                    "msg": "tradable_exchange_contract_address is not a valid address",
                    "type": "value_error"
                },
                {
                    "loc": [
                        "body",
                        "personal_info_contract_address"
                    ],
                    "msg": "personal_info_contract_address is not a valid address",
                    "type": "value_error"
                },
            ]
        }

    # <Error_2_2>
    # Validation Error
    # required headers
    def test_error_2_2(self, client, db):
        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": "issuer-address"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }, {
                "loc": ["header", "eoa-password"],
                "msg": "field required",
                "type": "value_error.missing"
            }]
        }

    # <Error_2_3>
    # Validation Error
    # eoa-password is not a Base64-encoded encrypted data
    def test_error_2_3(self, client, db):
        test_account_1 = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_1["address"],
                "eoa-password": "password"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["header", "eoa-password"],
                "msg": "eoa-password is not a Base64-encoded encrypted data",
                "type": "value_error"
            }]
        }

    # <Error_2_4>
    # Validation Error
    # optional fields
    def test_error_2_4(self, client, db):
        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "is_redeemed": "invalid value"
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": "issuer-address"
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
                    "loc": ["body", "is_redeemed"],
                    "msg": "value could not be parsed to a boolean",
                    "type": "type_error.bool"
                }
            ]
        }

    # <Error_2_5>
    # Validation Error
    # min value
    def test_error_2_5(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": -1,
            "face_value": -1,
            "redemption_date": "20211231",
            "redemption_value": -1,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": -0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "is_offering": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "is_manual_transfer_approval": True,  # update
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account["address"]
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
                    "loc": [
                        "body",
                        "total_supply"
                    ],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                },
                {
                    "ctx": {
                        "limit_value": 0
                    },
                    "loc": [
                        "body",
                        "face_value"
                    ],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                },
                {
                    "ctx": {
                        "limit_value": 0
                    },
                    "loc": [
                        "body",
                        "redemption_value"
                    ],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                },
                {
                    "ctx": {
                        "limit_value": 0.0
                    },
                    "loc": [
                        "body",
                        "interest_rate"
                    ],
                    "msg": "ensure this value is greater than or equal to 0.0",
                    "type": "value_error.number.not_ge"
                },
            ]
        }

    # <Error_2_6>
    # Validation Error
    # max value or max length
    def test_error_2_6(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": GetRandomStr(101),
            "symbol": GetRandomStr(101),
            "total_supply": 100_000_001,
            "face_value": 5_000_000_001,
            "redemption_date": "20211231",
            "redemption_value": 5_000_000_001,
            "return_date": "20211231",
            "return_amount": GetRandomStr(2001),
            "purpose": GetRandomStr(2001),
            "interest_rate": 100.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "is_offering": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": GetRandomStr(2001),  # update
            "privacy_policy": GetRandomStr(5001),  # update
            "transfer_approval_required": True,  # update
            "is_manual_transfer_approval": True,  # update
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account["address"]
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
                    "loc": ["body", "name"], 
                    "msg": "ensure this value has at most 100 characters",
                    "type": "value_error.any_str.max_length", 
                    "ctx": {"limit_value": 100}
                },
                {
                    "loc": ["body", "total_supply"], 
                    "msg": "ensure this value is less than or equal to 100000000",
                    "type": "value_error.number.not_le", 
                    "ctx": {"limit_value": 100000000}
                },
                {
                    "loc": ["body", "face_value"], 
                    "msg": "ensure this value is less than or equal to 5000000000",
                    "type": "value_error.number.not_le", 
                    "ctx": {"limit_value": 5000000000}
                },
                {
                    "loc": ["body", "purpose"],
                    "msg": "ensure this value has at most 2000 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 2000}
                },
                {
                    "loc": ["body", "symbol"], 
                    "msg": "ensure this value has at most 100 characters",
                    "type": "value_error.any_str.max_length", 
                    "ctx": {"limit_value": 100}
                },
                {
                    "loc": ["body", "redemption_value"],
                    "msg": "ensure this value is less than or equal to 5000000000",
                    "type": "value_error.number.not_le", 
                    "ctx": {"limit_value": 5000000000}
                },
                {
                    "loc": ["body", "return_amount"], 
                    "msg": "ensure this value has at most 2000 characters",
                    "type": "value_error.any_str.max_length", 
                    "ctx": {"limit_value": 2000}
                },
                {
                    "loc": ["body", "interest_rate"], 
                    "msg": "ensure this value is less than or equal to 100.0",
                    "type": "value_error.number.not_le", 
                    "ctx": {"limit_value": 100.0}
                },
                {
                    "loc": ["body", "contact_information"], 
                    "msg": "ensure this value has at most 2000 characters",
                    "type": "value_error.any_str.max_length", 
                    "ctx": {"limit_value": 2000}
                },
                {
                    "loc": ["body", "privacy_policy"], 
                    "msg": "ensure this value has at most 5000 characters",
                    "type": "value_error.any_str.max_length", 
                    "ctx": {"limit_value": 5000}
                }
            ]
        }

    # <Error_2_7>
    # Validation Error
    # YYYYMMDD/MMDD regex
    def test_error_2_7(self, client, db):
        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "invalid_date",
            "redemption_value": 4000,
            "return_date": "invalid_date",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_payment_date": ["invalid_date"],  # update
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": "issuer-address"
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
                    'loc': ['body', 'redemption_date'],
                    'msg': 'string does not match regex "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"',
                    'type': 'value_error.str.regex',
                    'ctx': {'pattern': '^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'}
                },
                {
                    'loc': ['body', 'return_date'],
                    'msg': 'string does not match regex "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"',
                    'type': 'value_error.str.regex',
                    'ctx': {'pattern': '^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'}
                },
                {
                    'loc': ['body', 'interest_payment_date', 0],
                    'msg': 'string does not match regex "^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"',
                    'type': 'value_error.str.regex',
                    'ctx': {'pattern': '^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'}
                }
            ]
        }

    # <Error_3_1>
    # Not Exists Address
    def test_error_3_1(self, client, db):
        test_account_1 = config_eth_account("user1")
        test_account_2 = config_eth_account("user2")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_2["address"],
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
        }

    # <Error_3_2>
    # Password Mismatch
    def test_error_3_2(self, client, db):
        test_account_1 = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_1["address"],
                "eoa-password": E2EEUtils.encrypt("password_test")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
        }

    # <Error_4_1>
    # Send Transaction Error
    # IbetStraightBondContract.create
    def test_error_4_1(self, client, db):
        test_account_1 = config_eth_account("user1")
        test_account_2 = config_eth_account("user2")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_2["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # mock
        IbetStraightBondContract_create = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.create",
            side_effect=SendTransactionError()
        )

        with IbetStraightBondContract_create:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 10000,
                "face_value": 200,
                "redemption_date": "20211231",
                "redemption_value": 4000,
                "return_date": "20211231",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account_1["address"],
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

            # assertion
            assert resp.status_code == 400
            assert resp.json() == {
                "meta": {
                    "code": 2,
                    "title": "SendTransactionError"
                },
                "detail": "failed to send transaction"
            }

    # <Error_5>
    # Send Transaction Error
    # TokenListContract.register
    def test_error_5(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # mock
        IbetStraightBondContract_create = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1")
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            side_effect=SendTransactionError()
        )

        with IbetStraightBondContract_create, \
                TokenListContract_register:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 10000,
                "face_value": 200,
                "redemption_date": "20211231",
                "redemption_value": 4000,
                "return_date": "20211231",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

            # assertion
            assert resp.status_code == 400
            assert resp.json() == {
                "meta": {
                    "code": 2,
                    "title": "SendTransactionError"
                },
                "detail": "failed to register token address token list"
            }


def GetRandomStr(num):
    dat = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return ''.join([random.choice(dat) for i in range(num)])
