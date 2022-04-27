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

from app.model.db import Token, TokenType, TokenHolderBatchStatus, TokenHoldersList
import config
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAppRoutersHoldersTokenAddressCollectionPOST:
    # target API endpoint
    base_url = "/token/holders/{token_address}/collection"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # POST collection request.
    @mock.patch("web3.eth.Eth.blockNumber", 100)
    def test_normal_1(self, client, db):
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

        # request target API
        req_param = {"list_id": list_id, "block_number": 100}

        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )

        stored_data: TokenHoldersList = db.query(TokenHoldersList).filter(TokenHoldersList.list_id == list_id).first()
        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "list_id": list_id,
            "status": TokenHolderBatchStatus.PENDING.value,
        }
        assert stored_data.list_id == list_id
        assert stored_data.token_address == token_address
        assert stored_data.batch_status == TokenHolderBatchStatus.PENDING.value
        assert stored_data.block_number == 100

    # Normal_2
    # POST collection request twice.
    @mock.patch("web3.eth.Eth.blockNumber", 101)
    def test_normal_2(self, client, db):
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

        for i in range(2):
            list_id = str(uuid.uuid4())
            # request target API
            req_param = {"list_id": list_id, "block_number": 100 + i}

            # request target api
            resp = client.post(
                self.base_url.format(token_address=token_address),
                json=req_param,
                headers={"issuer-address": issuer_address},
            )

            # assertion
            assert resp.status_code == 200
            assert resp.json() == {
                "list_id": list_id,
                "status": TokenHolderBatchStatus.PENDING.value,
            }

    # Normal_3
    # POST collection request with already existing contract_address and block_number.
    @mock.patch("web3.eth.Eth.blockNumber", 100)
    def test_normal_3(self, client, db):
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

        # request target API
        list_id1 = str(uuid.uuid4())
        req_param = {"list_id": list_id1, "block_number": 100}

        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )
        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "list_id": list_id1,
            "status": TokenHolderBatchStatus.PENDING.value,
        }

        list_id2 = str(uuid.uuid4())
        # request target API
        req_param = {"list_id": list_id2, "block_number": 100}
        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )
        # assertion
        # response is same as in the past.
        assert resp.status_code == 200
        assert resp.json() == {
            "list_id": list_id1,
            "status": TokenHolderBatchStatus.PENDING.value,
        }

    # Error_1
    # 422: Validation Error
    # List id in request body is empty.
    @mock.patch("web3.eth.Eth.blockNumber", 100)
    def test_error_1(self, client, db):
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

        # request target API
        req_param = {"block_number": 100}
        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )
        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body", "list_id"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
        }

    # Error_2
    # 404: Not Found Error
    # Invalid contract address
    @mock.patch("web3.eth.Eth.blockNumber", 100)
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
        _token.abi = {}
        db.add(_token)

        # request target API
        list_id = str(uuid.uuid4())
        req_param = {"block_number": 100, "list_id": list_id}
        # request target api
        resp = client.post(
            self.base_url.format(token_address="0xABCdeF123456789"),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )
        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # Error_3
    # 422: Invalid Parameter Error
    # "list_id" is not UUIDv4.
    @mock.patch("web3.eth.Eth.blockNumber", 100)
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

        # request target API
        list_id = "some_id"
        req_param = {"block_number": 100, "list_id": list_id}
        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )
        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [{"loc": ["body", "list_id"], "msg": "list_id is not UUIDv4.", "type": "value_error"}],
        }

    # Error_4
    # 400: Invalid Parameter Error
    # Block number is future one or negative.
    @mock.patch("web3.eth.Eth.blockNumber", 100)
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

        # request target API
        list_id = str(uuid.uuid4())
        req_param = {"block_number": 101, "list_id": list_id}
        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )
        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "Block number must be current or past one.",
        }

    # Error_5
    # 400: Invalid Parameter Error
    # Duplicate list_id is posted.
    @mock.patch("web3.eth.Eth.blockNumber", 100)
    def test_error_5(self, client, db):
        # issue token
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address1 = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token1 = Token()
        _token1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token1.tx_hash = ""
        _token1.issuer_address = issuer_address
        _token1.token_address = token_address1
        _token1.abi = {}
        db.add(_token1)

        # request target API
        list_id = str(uuid.uuid4())
        req_param = {"block_number": 100, "list_id": list_id}
        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address1),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )
        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "list_id": list_id,
            "status": TokenHolderBatchStatus.PENDING.value,
        }

        # prepare data
        token_address2 = "0x000000000987654321fEdcba0987654321FedCBA"
        _token2 = Token()
        _token2.type = TokenType.IBET_STRAIGHT_BOND.value
        _token2.tx_hash = ""
        _token2.issuer_address = issuer_address
        _token2.token_address = token_address2
        _token2.abi = {}
        db.add(_token2)

        # request target API with same list id as in the past
        req_param = {"block_number": 100, "list_id": list_id}

        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address2),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "list_id must be unique.",
        }

    # Error_6
    # 400: Invalid Parameter Errori
    # Not listed token
    @mock.patch("web3.eth.Eth.blockNumber", 100)
    def test_error_6(self, client, db):
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
        _token.token_status = 0
        db.add(_token)

        list_id = str(uuid.uuid4())

        # request target API
        req_param = {"list_id": list_id, "block_number": 100}

        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "wait for a while as the token is being processed",
        }

    # Error_7
    # 422: Validation Error
    # Issuer-address in request header is not set.
    @mock.patch("web3.eth.Eth.blockNumber", 100)
    def test_error_7(self, client, db):
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

        # request target API
        req_param = {"block_number": 100, "list_id": list_id}
        # request target api
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
        )
        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [{"loc": ["header", "issuer-address"], "msg": "field required", "type": "value_error.missing"}],
        }
