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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import IDXTxData


class TestListTxData:
    # API to be tested
    apiurl = "/blockchain_explorer/tx_data"

    # Test data
    A_tx_1 = {
        "block_hash": "0x94670853c83f3c444d8515cbb9902c9e88b3619c27b9577714baaa07d35874ff",
        "block_number": 6791869,
        "from_address": "0x30406Cd5f18DD87367B782b9D63b4d79F7f5eBb8",
        "to_address": "0x1FBb27d6682aB47654f0150457B64F9A96C926d4",
        "gas": 6000000,
        "gas_price": 0,
        "hash": "0x560f6761de57832d2a1adcd10434f85762c9f833b45717b1cae778f8a23fc6cb",
        "input": "0x5ccef3e7000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000010313634393237303331302e383734303400000000000000000000000000000000",
        "nonce": 86942,
        "transaction_index": 0,
        "value": 0,
    }
    A_tx_2 = {
        "block_hash": "0x077e42cfe8bc9577b85a6347136c2d38a2b165e7b31bb340c33d302565b900b6",
        "block_number": 6791871,
        "from_address": "0x30406Cd5f18DD87367B782b9D63b4d79F7f5eBb8",
        "to_address": "0x1FBb27d6682aB47654f0150457B64F9A96C926d4",
        "gas": 6000000,
        "gas_price": 0,
        "hash": "0x4ad0b5e395f8c7cc843ba9ffc8b86e6a8b0c71cb724c68b5842839954410892c",
        "input": "0x5ccef3e7000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000011313634393237303331322e383235303432000000000000000000000000000000",
        "nonce": 86943,
        "transaction_index": 0,
        "value": 0,
    }
    B_tx_1 = {
        "block_hash": "0x6698ebc4866223855dbea153eec7a9455682fd6d2f8451746102afb320412a6b",
        "block_number": 10407084,
        "from_address": "0x8456ac4FEc4869A16ad5C3584306181Af6410682",
        "to_address": "0xECeB9FdBd2CF677Be5fA8B1ceEb53e53D582f0Eb",
        "gas": 6000000,
        "gas_price": 0,
        "hash": "0x403f9cea4db07aecf71a440c45ae415569cb218bb1a7f4d3a2d83004e29d1644",
        "input": "0x5ccef3e7000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000011313635323937363632372e363337373738000000000000000000000000000000",
        "nonce": 199601,
        "transaction_index": 0,
        "value": 0,
    }

    @staticmethod
    def filter_response_item(tx_data):
        return {
            "hash": tx_data.get("hash"),
            "block_hash": tx_data.get("block_hash"),
            "block_number": tx_data.get("block_number"),
            "transaction_index": tx_data.get("transaction_index"),
            "from_address": tx_data.get("from_address"),
            "to_address": tx_data.get("to_address"),
        }

    @staticmethod
    def insert_tx_data(db, tx_data):
        tx_model = IDXTxData()
        tx_model.hash = tx_data.get("hash")
        tx_model.block_hash = tx_data.get("block_hash")
        tx_model.block_number = tx_data.get("block_number")
        tx_model.transaction_index = tx_data.get("transaction_index")
        tx_model.from_address = tx_data.get("from_address")
        tx_model.to_address = tx_data.get("to_address")
        tx_model.input = tx_data.get("input")
        tx_model.gas = tx_data.get("gas")
        tx_model.gas_price = tx_data.get("gas_price")
        tx_model.value = tx_data.get("value")
        tx_model.nonce = tx_data.get("nonce")
        db.add(tx_model)
        db.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    def test_normal_1(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.A_tx_1)
        self.insert_tx_data(db, self.A_tx_2)
        self.insert_tx_data(db, self.B_tx_1)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            resp = client.get(self.apiurl)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        assert response_data["tx_data"] == [
            self.filter_response_item(self.B_tx_1),
            self.filter_response_item(self.A_tx_2),
            self.filter_response_item(self.A_tx_1),
        ]

    # Normal_2_1
    # Query parameter: block_number
    def test_normal_2_1(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.A_tx_1)
        self.insert_tx_data(db, self.A_tx_2)
        self.insert_tx_data(db, self.B_tx_1)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"block_number": 6791871}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        assert response_data["tx_data"] == [self.filter_response_item(self.A_tx_2)]

    # Normal_2_2
    # Query parameter: from_address
    def test_normal_2_2(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.A_tx_1)
        self.insert_tx_data(db, self.A_tx_2)
        self.insert_tx_data(db, self.B_tx_1)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"from_address": "0x30406cd5f18dd87367b782b9d63b4d79f7f5ebb8"}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        assert response_data["tx_data"] == [
            self.filter_response_item(self.A_tx_2),
            self.filter_response_item(self.A_tx_1),
        ]

    # Normal_2_3
    # Query parameter: to_address
    def test_normal_2_3(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.A_tx_1)
        self.insert_tx_data(db, self.A_tx_2)
        self.insert_tx_data(db, self.B_tx_1)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"to_address": "0xeceb9fdbd2cf677be5fa8b1ceeb53e53d582f0eb"}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 1,
            "offset": None,
            "limit": None,
            "total": 3,
        }
        assert response_data["tx_data"] == [self.filter_response_item(self.B_tx_1)]

    # Normal_3_1
    # Pagination: offset
    def test_normal_3_1(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.A_tx_1)
        self.insert_tx_data(db, self.A_tx_2)
        self.insert_tx_data(db, self.B_tx_1)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"offset": 1}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 3,
            "offset": 1,
            "limit": None,
            "total": 3,
        }
        assert response_data["tx_data"] == [
            self.filter_response_item(self.A_tx_2),
            self.filter_response_item(self.A_tx_1),
        ]

    # Normal_3_2
    # Pagination: limit
    def test_normal_3_2(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.A_tx_1)
        self.insert_tx_data(db, self.A_tx_2)
        self.insert_tx_data(db, self.B_tx_1)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"limit": 1}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": 1,
            "total": 3,
        }
        assert response_data["tx_data"] == [self.filter_response_item(self.B_tx_1)]

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # BC_EXPLORER_ENABLED = False (default)
    def test_error_1(self, client: TestClient, db: Session):
        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", False):
            resp = client.get(self.apiurl)

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "This URL is not available in the current settings",
        }

    # Error_2_1
    # Invalid Parameter
    def test_error_2_1(self, client: TestClient, db: Session):
        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"offset": -1, "limit": -1, "block_number": -1}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "block_number"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
        }

    # Error_2_2
    # Invalid Parameter
    def test_error_2_2(self, client: TestClient, db: Session):
        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"from_address": "abcd", "to_address": "abcd"}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["query", "from_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "abcd",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "to_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "abcd",
                    "ctx": {"error": {}},
                },
            ],
        }

    # Error_3
    # ResponseLimitExceededError
    def test_error_3(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.A_tx_1)
        self.insert_tx_data(db, self.A_tx_2)
        self.insert_tx_data(db, self.B_tx_1)

        # Request target API
        with mock.patch(
            "app.routers.bc_explorer.BC_EXPLORER_ENABLED", True
        ), mock.patch("app.routers.bc_explorer.TX_RESPONSE_LIMIT", 2):
            resp = client.get(self.apiurl)

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 4, "title": "ResponseLimitExceededError"},
            "detail": "Search results exceed the limit",
        }
