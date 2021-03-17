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
from unittest.mock import MagicMock, ANY

from web3 import Web3
from web3.middleware import geth_poa_middleware

import config
from app.exceptions import SendTransactionError
from app.model.db import Account, Token, TokenType
from app.model.schema import IbetStraightBondUpdate
from app.model.utils import E2EEUtils
from app.model.blockchain.token import IbetStraightBondContract
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
        IbetStraightBondContract.create = MagicMock(
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1")
        )
        IbetStraightBondContract.update = MagicMock(
            return_value=None
        )

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account["address"]
            }
        )

        # assertion
        IbetStraightBondContract.create.assert_called_with(
            args=[
                "name_test1", "symbol_test1", 10000, 200, "redemption_date_test1", 4000,
                "return_date_test1", "return_amount_test1", "purpose_test1"
            ],
            tx_from=test_account["address"],
            private_key=ANY
        )
        IbetStraightBondContract.update.assert_called_with(
            contract_address="contract_address_test1",
            data=IbetStraightBondUpdate(),
            tx_from=test_account["address"],
            private_key=ANY
        )

        assert resp.status_code == 200
        assert resp.json()["token_address"] == "contract_address_test1"

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
        IbetStraightBondContract.create = MagicMock(
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1")
        )
        IbetStraightBondContract.update = MagicMock(
            return_value=None
        )

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "initial_offering_status": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test"  # update
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account["address"]
            }
        )

        # assertion
        IbetStraightBondContract.create.assert_called_with(
            args=[
                "name_test1", "symbol_test1",
                10000, 200,
                "redemption_date_test1", 4000,
                "return_date_test1", "return_amount_test1",
                "purpose_test1"
            ],
            tx_from=test_account["address"],
            private_key=ANY
        )

        IbetStraightBondContract.update.assert_called_with(
            contract_address="contract_address_test1",
            data=IbetStraightBondUpdate(
                interest_rate=0.0001, 
                interest_payment_date=["0331", "0930"],
                transferable=False, 
                image_url=None, 
                status=False, 
                initial_offering_status=True, 
                is_redeemed=True, 
                tradable_exchange_contract_address="0x0000000000000000000000000000000000000001", 
                personal_info_contract_address="0x0000000000000000000000000000000000000002", 
                contact_information="contact info test", 
                privacy_policy="privacy policy test"
            ),
            tx_from=test_account["address"],
            private_key=ANY
        )

        assert resp.status_code == 200
        assert resp.json()["token_address"] == "contract_address_test1"

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


    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation Error
    # required fields
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
    # interest_rate, tradable_exchange_contract_address,
    # personal_info_contract_address, image_url
    def test_error_2_1(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 123.45678,
            "tradable_exchange_contract_address": "0x0",
            "personal_info_contract_address": "0x0",
            "image_url": [
                "http://test/test",
                "http://test/test",
                "http://test/test",
                "http://test/test",
            ],
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
                {
                    "loc": [
                        "body",
                        "image_url"
                    ],
                    "msg": "The length of the list must be less than or equal to 3",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2_2>
    # Validation Error
    # issuer-address
    def test_error_2_2(self, client, db):

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
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
            }]
        }

    # <Error_2_3>
    # Validation Error
    # update items
    def test_error_2_3(self, client, db):

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
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

    # <Error_3>
    # Not Exists Address
    def test_error_3(self, client, db):
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
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_2["address"]
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "issuer does not exist"
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
        IbetStraightBondContract.create = MagicMock(side_effect=SendTransactionError())

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_1["address"]
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

    # <Error_4_2>
    # Send Transaction Error
    # IbetStraightBondContract.update
    def test_error_4_2(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # mock
        IbetStraightBondContract.create = MagicMock(
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1")
        )
        IbetStraightBondContract.update = MagicMock(side_effect=SendTransactionError())

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "initial_offering_status": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test"  # update
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account["address"]
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
