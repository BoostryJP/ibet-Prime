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
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import config
from app.model.db import (
    Token,
    TokenHolderBatchStatus,
    TokenHoldersList,
    TokenType,
    TokenVersion,
)
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestCreateTokenHoldersCollection:
    # target API endpoint
    base_url = "/token/holders/{token_address}/collection"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # POST collection request.
    @pytest.mark.asyncio
    async def test_normal_1(self, client, db):
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        list_id = str(uuid.uuid4())

        # mock setting
        block_number_mock = AsyncMock()
        block_number_mock.return_value = 100

        # request target API
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            req_param = {"list_id": list_id, "block_number": 100}
            resp = client.post(
                self.base_url.format(token_address=token_address),
                json=req_param,
                headers={"issuer-address": issuer_address},
            )

        # assertion
        stored_data: TokenHoldersList = db.scalars(
            select(TokenHoldersList).where(TokenHoldersList.list_id == list_id).limit(1)
        ).first()
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
    # POST collection request with already existing contract_address and block_number.
    @pytest.mark.asyncio
    async def test_normal_2(self, client, db):
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # mock setting
        block_number_mock = AsyncMock()
        block_number_mock.return_value = 100

        # request target API
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            list_id1 = str(uuid.uuid4())
            req_param = {"list_id": list_id1, "block_number": 100}
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

        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            list_id2 = str(uuid.uuid4())
            req_param = {"list_id": list_id2, "block_number": 100}
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

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # 422: Validation Error
    # List id in request body is empty.
    @pytest.mark.asyncio
    async def test_error_1(self, client, db):
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # request target API
        req_param = {"block_number": 100}
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
                    "input": {"block_number": 100},
                    "loc": ["body", "list_id"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # Error_2
    # 404: Not Found Error
    # Invalid contract address
    @pytest.mark.asyncio
    async def test_error_2(self, client, db):
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # request target API
        list_id = str(uuid.uuid4())
        req_param = {"block_number": 100, "list_id": list_id}
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
    @pytest.mark.asyncio
    async def test_error_3(self, client, db):
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # request target API
        list_id = "some_id"
        req_param = {"block_number": 100, "list_id": list_id}
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
                    "ctx": {"error": {}},
                    "input": "some_id",
                    "loc": ["body", "list_id"],
                    "msg": "Value error, list_id is not UUIDv4.",
                    "type": "value_error",
                }
            ],
        }

    # Error_4
    # 400: Invalid Parameter Error
    # Block number is future one or negative.
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # mock setting
        block_number_mock = AsyncMock()
        block_number_mock.return_value = 100

        # request target API
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            list_id = str(uuid.uuid4())
            req_param = {"block_number": 101, "list_id": list_id}
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
        _token1.version = TokenVersion.V_24_09
        db.add(_token1)

        db.commit()

        # mock setting
        block_number_mock = AsyncMock()
        block_number_mock.return_value = 100

        # request target API
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            list_id = str(uuid.uuid4())
            req_param = {"block_number": 100, "list_id": list_id}
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
        _token2.version = TokenVersion.V_24_09
        db.add(_token2)

        db.commit()

        # request target API
        with mock.patch(
            "web3.eth.async_eth.AsyncEth.block_number", block_number_mock()
        ):
            req_param = {"block_number": 100, "list_id": list_id}
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
    # 400: Invalid Parameter Error
    # Not listed token
    @pytest.mark.asyncio
    async def test_error_6(self, client, db):
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        list_id = str(uuid.uuid4())

        # request target API
        req_param = {"list_id": list_id, "block_number": 100}
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # Error_7
    # 422: Validation Error
    # Issuer-address in request header is not set.
    @pytest.mark.asyncio
    async def test_error_7(self, client, db):
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
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        list_id = str(uuid.uuid4())

        # request target API
        req_param = {"block_number": 100, "list_id": list_id}
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }
