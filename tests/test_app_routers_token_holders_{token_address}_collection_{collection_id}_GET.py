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
import uuid
from unittest import mock
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model.db import (
    Token,
    TokenType,
    TokenHolderBatchStatus,
    TokenHoldersList,
    TokenHolder,
)
import config
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAppRoutersHoldersTokenAddressCollectionIdGET:
    # target API endpoint
    base_url = "/token/holders/{token_address}/collection/{list_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # GET
    # Holders in response is empty.
    @mock.patch("web3.eth.Eth.block_number", 100)
    def test_normal_1(self, client, db):
        # Issue Token
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

        list_id = str(uuid.uuid4())
        _token_holders_collection = TokenHoldersList()
        _token_holders_collection.list_id = list_id
        _token_holders_collection.token_address = token_address
        _token_holders_collection.block_number = 100
        _token_holders_collection.batch_status = TokenHolderBatchStatus.DONE.value

        db.add(_token_holders_collection)

        # request target api
        resp = client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "status": TokenHolderBatchStatus.DONE.value,
            "holders": [],
        }

    # Normal_2
    # GET
    # Holders in response is filled.
    def test_normal_2(self, client, db):
        # Issue Token
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

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(_token_holders_list)
        db.commit()

        holders = []

        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = config_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i+1)
            db.add(_token_holder)
            holders.append(_token_holder.json())

        # request target api
        resp = client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )
        db.query(TokenHolder).filter().all()
        sorted_holders = sorted(holders, key=lambda x: x['account_address'])
        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "status": TokenHolderBatchStatus.DONE.value,
            "holders": sorted_holders,
        }

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 404: Not Found Error
    # Invalid contract address
    def test_error_1(self, client, db):
        # issue token
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        list_id = str(uuid.uuid4())

        # request target api with not_listed contract_address
        resp = client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # Error_2
    # 400: Invalid Parameter Error
    # Token is pending
    def test_error_2(self, client, db):
        # issue token
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        # set status pending
        _token.token_status = 0
        _token.abi = {}
        db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(_token_holders_list)

        # request target api
        resp = client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # Error_3
    # 400: Invalid Parameter Error
    # Invalid list_id
    def test_error_3(self, client, db):
        # issue token
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

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(_token_holders_list)

        # request target api with invalid list_id
        resp = client.get(
            self.base_url.format(token_address=token_address, list_id="some_id"),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "list_id must be UUIDv4.",
        }

    # Error_4
    # 404: Not Found Error
    # There is no holder list record with given list_id.
    def test_error_4(self, client, db):
        # issue token
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

        list_id = str(uuid.uuid4())
        # request target api
        resp = client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "list not found",
        }

    # Error_5
    # 400: Invalid Parameter Error
    # Invalid contract address and list id combi.
    def test_error_5(self, client, db):
        # issue token
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address1 = "0xABCdeF1234567890abcdEf123456789000000000"
        token_address2 = "0x000000000987654321fEdcba0987654321FedCBA"

        # prepare data
        _token1 = Token()
        _token1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token1.tx_hash = ""
        _token1.issuer_address = issuer_address
        _token1.token_address = token_address1
        _token1.abi = {}
        db.add(_token1)
        _token2 = Token()
        _token2.type = TokenType.IBET_STRAIGHT_BOND.value
        _token2.tx_hash = ""
        _token2.issuer_address = issuer_address
        _token2.token_address = token_address2
        _token2.abi = {}
        db.add(_token2)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address1
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(_token_holders_list)
        # request target api
        resp = client.get(
            self.base_url.format(token_address=token_address2, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": f"list_id: {list_id} is not related to token_address: {token_address2}",
        }

    # Error_6
    # 422: Request Validation Error
    # Issuer-address in request header is not set.
    @mock.patch("web3.eth.Eth.block_number", 100)
    def test_error_6(self, client, db):
        # Issue Token
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

        list_id = str(uuid.uuid4())
        _token_holders_collection = TokenHoldersList()
        _token_holders_collection.list_id = list_id
        _token_holders_collection.token_address = token_address
        _token_holders_collection.block_number = 100
        _token_holders_collection.batch_status = TokenHolderBatchStatus.DONE.value

        db.add(_token_holders_collection)

        # request target api
        resp = client.get(
            self.base_url.format(token_address=token_address, list_id=list_id)
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    'loc': ['header', 'issuer-address'],
                    'msg': 'field required',
                    'type': 'value_error.missing'
                }
            ]
        }
