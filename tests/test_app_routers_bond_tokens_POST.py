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
from unittest.mock import MagicMock, ANY

from web3 import Web3
from web3.middleware import geth_poa_middleware

import config
from app.exceptions import SendTransactionError
from app.model.db import Account, Token, TokenType
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAppRoutersBondTokensPOST:
    # target API endpoint
    apiurl = "/bond/tokens"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal Case 1>
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.create")
    def test_normal_1(self, mock_create, client, db):
        test_account = config_eth_account("user1")

        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        db.add(account)

        token_before = db.query(Token).all()

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

        mock_create.side_effect = [
            ("contract_address_test1", "abi_test1", "tx_hash_test1")
        ]

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": test_account["address"]})

        # assertion mock call arguments
        arguments = [value for value in req_param.values()]
        mock_create.assert_any_call(args=arguments, tx_from=account.issuer_address, private_key=ANY)

        token_after = db.query(Token).all()

        assert resp.status_code == 200
        assert resp.json()["token_address"] == "contract_address_test1"

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

    # <Error Case 1>
    # Parameter Error
    def test_error_1(self, client):
        resp = client.post(self.apiurl, headers={"issuer-address": ""})
        assert resp.status_code == 422
        assert resp.json()["meta"] == {
            "code": 1,
            "title": "RequestValidationError"
        }
        assert resp.json()["detail"] is not None
    
    # <Error Case 2>
    # Not Exists Address
    def test_error_2(self, client, db):
        test_account = config_eth_account("user1")

        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        db.add(account)

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
            headers={"issuer-address": "not_exists_issuer"}
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "issuer does not exist"
        }

    # <Error Case 3>
    # Send Transaction Error
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.create", MagicMock(side_effect=SendTransactionError()))
    def test_error_3(self, client, db):
        test_account_1 = config_eth_account("user1")
        test_account_2 = config_eth_account("user2")

        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_2["keyfile_json"]
        db.add(account)

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

        resp = client.post(self.apiurl, json=req_param, headers={"issuer-address": test_account_1["address"]})

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 2,
                "title": "SendTransactionError"
            },
            "detail": "failed to send transaction"
        }
