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
import hashlib
import random
import string
from datetime import datetime, timezone
from unittest.mock import ANY, patch

from web3 import Web3
from web3.middleware import geth_poa_middleware

import config
from app.exceptions import SendTransactionError
from app.model.blockchain.token import IbetShareContract
from app.model.blockchain.token_list import TokenListContract
from app.model.db import (
    UTXO,
    Account,
    AuthToken,
    IDXPosition,
    Token,
    TokenType,
    UpdateToken,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAppRoutersShareTokensPOST:
    # target API endpoint
    apiurl = "/share/tokens"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # create only
    def test_normal_1_1(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token_before = db.query(Token).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1"),
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(
                    2021, 4, 27, 12, 34, 56, tzinfo=timezone.utc
                ).timestamp(),
            },
        )

        with (
            IbetShareContract_create
        ), TokenListContract_register, ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_SHARE.value,
                tx_from=test_account["address"],
                private_key=ANY,
            )
            ContractUtils.get_block_by_transaction_hash(tx_hash="tx_hash_test1")

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = db.query(Token).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)
            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE.value
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

            utxo = db.query(UTXO).first()
            assert utxo.transaction_hash == "tx_hash_test1"
            assert utxo.account_address == test_account["address"]
            assert utxo.token_address == "contract_address_test1"
            assert utxo.amount == req_param["total_supply"]
            assert utxo.block_number == 12345
            assert utxo.block_timestamp == datetime(2021, 4, 27, 12, 34, 56)

            update_token = db.query(UpdateToken).first()
            assert update_token is None

    # <Normal_1_2>
    # create only
    # No input for symbol, dividends and cancellation_date.
    def test_normal_1_2(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token_before = db.query(Token).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1"),
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(
                    2021, 4, 27, 12, 34, 56, tzinfo=timezone.utc
                ).timestamp(),
            },
        )

        with (
            IbetShareContract_create
        ), TokenListContract_register, ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {
                "name": "name_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "principal_value": 1000,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=["name_test1", "", 1000, 10000, 0, "", "", "", 1000],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_SHARE.value,
                tx_from=test_account["address"],
                private_key=ANY,
            )
            ContractUtils.get_block_by_transaction_hash(tx_hash="tx_hash_test1")

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = db.query(Token).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)
            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE.value
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

            utxo = db.query(UTXO).first()
            assert utxo.transaction_hash == "tx_hash_test1"
            assert utxo.account_address == test_account["address"]
            assert utxo.token_address == "contract_address_test1"
            assert utxo.amount == req_param["total_supply"]
            assert utxo.block_number == 12345
            assert utxo.block_timestamp == datetime(2021, 4, 27, 12, 34, 56)

            update_token = db.query(UpdateToken).first()
            assert update_token is None

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
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1"),
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(
                    2021, 4, 27, 12, 34, 56, tzinfo=timezone.utc
                ).timestamp(),
            },
        )

        with (
            IbetShareContract_create
        ), TokenListContract_register, ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "transferable": False,  # update
                "status": False,  # update
                "is_offering": True,  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test",  # update
                "transfer_approval_required": True,  # update
                "principal_value": 1000,
                "is_canceled": True,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_not_called()
            ContractUtils.get_block_by_transaction_hash.assert_not_called()

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 0

            token_after = db.query(Token).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)
            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE.value
            assert token_1.tx_hash == "tx_hash_test1"
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 0

            position = db.query(IDXPosition).first()
            assert position is None

            utxo = db.query(UTXO).first()
            assert utxo is None

            update_token = db.query(UpdateToken).first()
            assert update_token.id == 1
            assert update_token.token_address == "contract_address_test1"
            assert update_token.issuer_address == test_account["address"]
            assert update_token.type == TokenType.IBET_SHARE.value
            assert update_token.arguments == req_param
            assert update_token.status == 0
            assert update_token.trigger == "Issue"

    # <Normal_3>
    # Authorization by auth-token
    def test_normal_3(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        db.add(auth_token)

        token_before = db.query(Token).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1"),
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(
                    2021, 4, 27, 12, 34, 56, tzinfo=timezone.utc
                ).timestamp(),
            },
        )

        with (
            IbetShareContract_create
        ), TokenListContract_register, ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "auth-token": "test_auth_token",
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_SHARE.value,
                tx_from=test_account["address"],
                private_key=ANY,
            )
            ContractUtils.get_block_by_transaction_hash(tx_hash="tx_hash_test1")

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = db.query(Token).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)
            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE.value
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

            utxo = db.query(UTXO).first()
            assert utxo.transaction_hash == "tx_hash_test1"
            assert utxo.account_address == test_account["address"]
            assert utxo.token_address == "contract_address_test1"
            assert utxo.amount == req_param["total_supply"]
            assert utxo.block_number == 12345
            assert utxo.block_timestamp == datetime(2021, 4, 27, 12, 34, 56)

            update_token = db.query(UpdateToken).first()
            assert update_token is None

    # <Normal_4_1>
    # YYYYMMDD parameter is not empty
    def test_normal_4_1(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # mock
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1"),
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(
                    2021, 4, 27, 12, 34, 56, tzinfo=timezone.utc
                ).timestamp(),
            },
        )

        with (
            IbetShareContract_create
        ), TokenListContract_register, ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

    # <Normal_4_2>
    # YYYYMMDD parameter is empty
    def test_normal_4_2(self, client, db):
        test_account = config_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # mock
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1"),
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(
                    2021, 4, 27, 12, 34, 56, tzinfo=timezone.utc
                ).timestamp(),
            },
        )

        with (
            IbetShareContract_create
        ), TokenListContract_register, ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "",
                "dividend_payment_date": "",
                "cancellation_date": "",
                "principal_value": 1000,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "",
                    "",
                    "",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation Error
    # missing fields
    def test_error_1(self, client, db):
        # request target api
        resp = client.post(self.apiurl)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
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
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 0.00000000000001,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0",
            "personal_info_contract_address": "0x0",
            "principal_value": 1000,
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body", "dividends"],
                    "msg": "dividends must be rounded to 13 decimal places",
                    "type": "value_error",
                },
                {
                    "loc": ["body", "tradable_exchange_contract_address"],
                    "msg": "tradable_exchange_contract_address is not a valid address",
                    "type": "value_error",
                },
                {
                    "loc": ["body", "personal_info_contract_address"],
                    "msg": "personal_info_contract_address is not a valid address",
                    "type": "value_error",
                },
            ],
        }

    # <Error_2_2>
    # Validation Error
    # required headers
    def test_error_2_2(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = client.post(
            self.apiurl, json=req_param, headers={"issuer-address": "issuer-address"}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
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
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_1["address"],
                "eoa-password": "password",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2_4>
    # Validation Error
    # min value
    def test_error_2_4(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": -1,
            "total_supply": -1,
            "dividends": -0.01,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "transferable": False,  # update
            "status": False,  # update
            "is_offering": True,  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "principal_value": -1,
            "is_canceled": True,
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["body", "issue_price"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge",
                },
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["body", "principal_value"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge",
                },
                {
                    "ctx": {"limit_value": 0},
                    "loc": ["body", "total_supply"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge",
                },
                {
                    "ctx": {"limit_value": 0.0},
                    "loc": ["body", "dividends"],
                    "msg": "ensure this value is greater than or equal to 0.0",
                    "type": "value_error.number.not_ge",
                },
            ],
        }

    # <Error_2_5>
    # Validation Error
    # max value or max length
    def test_error_2_5(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": GetRandomStr(101),
            "symbol": GetRandomStr(101),
            "issue_price": 5_000_000_001,
            "total_supply": 1_000_000_000_001,
            "dividends": 5_000_000_000.01,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "transferable": False,  # update
            "status": False,  # update
            "is_offering": True,  # update
            "contact_information": GetRandomStr(2001),  # update
            "privacy_policy": GetRandomStr(5001),  # update
            "transfer_approval_required": True,  # update
            "principal_value": 5_000_000_001,
            "is_canceled": True,
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body", "name"],
                    "msg": "ensure this value has at most 100 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 100},
                },
                {
                    "loc": ["body", "issue_price"],
                    "msg": "ensure this value is less than or equal to 5000000000",
                    "type": "value_error.number.not_le",
                    "ctx": {"limit_value": 5000000000},
                },
                {
                    "loc": ["body", "principal_value"],
                    "msg": "ensure this value is less than or equal to 5000000000",
                    "type": "value_error.number.not_le",
                    "ctx": {"limit_value": 5000000000},
                },
                {
                    "loc": ["body", "total_supply"],
                    "msg": "ensure this value is less than or equal to 1000000000000",
                    "type": "value_error.number.not_le",
                    "ctx": {"limit_value": 1000000000000},
                },
                {
                    "loc": ["body", "symbol"],
                    "msg": "ensure this value has at most 100 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 100},
                },
                {
                    "loc": ["body", "dividends"],
                    "msg": "ensure this value is less than or equal to 5000000000.0",
                    "type": "value_error.number.not_le",
                    "ctx": {"limit_value": 5000000000.0},
                },
                {
                    "loc": ["body", "contact_information"],
                    "msg": "ensure this value has at most 2000 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 2000},
                },
                {
                    "loc": ["body", "privacy_policy"],
                    "msg": "ensure this value has at most 5000 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 5000},
                },
            ],
        }

    # <Error_2_6>
    # Validation Error
    # YYYYMMDD regex
    def test_error_2_6(self, client, db):
        test_account = config_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "202101010",
            "dividend_payment_date": "202101010",
            "cancellation_date": "202201010",
            "principal_value": 1000,
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body", "dividend_record_date"],
                    "msg": 'string does not match regex "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"',
                    "type": "value_error.str.regex",
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                },
                {
                    "loc": ["body", "dividend_record_date"],
                    "msg": "unexpected value; permitted: ''",
                    "type": "value_error.const",
                    "ctx": {"given": "202101010", "permitted": [""]},
                },
                {
                    "loc": ["body", "dividend_payment_date"],
                    "msg": 'string does not match regex "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"',
                    "type": "value_error.str.regex",
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                },
                {
                    "loc": ["body", "dividend_payment_date"],
                    "msg": "unexpected value; permitted: ''",
                    "type": "value_error.const",
                    "ctx": {"given": "202101010", "permitted": [""]},
                },
                {
                    "loc": ["body", "cancellation_date"],
                    "msg": 'string does not match regex "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"',
                    "type": "value_error.str.regex",
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                },
                {
                    "loc": ["body", "cancellation_date"],
                    "msg": "unexpected value; permitted: ''",
                    "type": "value_error.const",
                    "ctx": {"given": "202201010", "permitted": [""]},
                },
            ],
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
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_2["address"],
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_3_2>
    # Password Mismatch
    def test_error_3_2(self, client, db):
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
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_1["address"],
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_4_1>
    # Send Transaction Error
    # IbetShareContract.create
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
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            side_effect=SendTransactionError(),
        )

        with IbetShareContract_create:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account_1["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 400
            assert resp.json() == {
                "meta": {"code": 2, "title": "SendTransactionError"},
                "detail": "failed to send transaction",
            }

    # <Error_5>
    # Send Transaction Error
    # TokenListContract.register
    def test_error_5(self, client, db):
        test_account_1 = config_eth_account("user1")
        test_account_2 = config_eth_account("user2")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_2["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # mock
        IbetShareContract_create = patch(
            target="app.model.blockchain.token.IbetShareContract.create",
            return_value=("contract_address_test1", "abi_test1", "tx_hash_test1"),
        )
        TokenListContract_register = patch(
            target="app.model.blockchain.token_list.TokenListContract.register",
            side_effect=SendTransactionError(),
        )

        with IbetShareContract_create, TokenListContract_register:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account_1["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 400
            assert resp.json() == {
                "meta": {"code": 2, "title": "SendTransactionError"},
                "detail": "failed to register token address token list",
            }


def GetRandomStr(num):
    dat = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return "".join([random.choice(dat) for i in range(num)])
