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

from app.model.db import (
    IDXBlockData,
    IDXBlockDataBlockNumber
)
from config import CHAIN_ID


class TestListBlockData:
    # API to be tested
    apiurl = "/blockchain_explorer/block_data"

    # Test data
    block_0 = {
        'number': 0,
        'difficulty': 1,
        'proof_of_authority_data': '0x0000000000000000000000000000000000000000000000000000000000000000f89af8549447a847fbdf801154253593851ac9a2e7753235349403ee8c85944b16dfa517cb0ddefe123c7341a5349435d56a7515e824be4122f033d60063d035573a0c94c25d04978fd86ee604feb88f3c635d555eb6d42db8410000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0',
        'gas_limit': 800000000,
        'gas_used': 0,
        'hash': '0x307166a396b99259ed2072f4b99d850e332db4ef4c72656870680728944ad445',
        'logs_bloom': '0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
        'miner': '0x0000000000000000000000000000000000000000',
        'mix_hash': '0x63746963616c2062797a616e74696e65206661756c7420746f6c6572616e6365',
        'nonce': '0x0000000000000000',
        'parent_hash': '0x0000000000000000000000000000000000000000000000000000000000000000',
        'receipts_root': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
        'sha3_uncles': '0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347',
        'size': 698,
        'state_root': '0x260aa025c613224aaa46e2134b6469f3d956c07949a6ca23143936c574838995',
        'timestamp': 1524130695,
        'transactions': [],
        'transactions_root': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
    }
    block_1 = {
        'number': 1,
        'difficulty': 1,
        'proof_of_authority_data': '0xd983010907846765746889676f312e31332e3135856c696e7578000000000000f90164f8549403ee8c85944b16dfa517cb0ddefe123c7341a5349435d56a7515e824be4122f033d60063d035573a0c9447a847fbdf801154253593851ac9a2e77532353494c25d04978fd86ee604feb88f3c635d555eb6d42db841d6b123b02f015f4f0b0d47648e22c043dca3f803e6498084522c07ccbea58f8c39e498f6c8c604abb406dc323246c30525cc0dd01c39bcadbb608733bdf3f08300f8c9b84186503892a4b314f2b8aba73b1a7434c69bd95695ac285d5db6d15f879b5dbbf83471502e13eb1d0fce4d2e7ea41be91e8ecf744f0eeb8c808fb2e4a7833377f901b84141f6e74ea7f1365fa01ab90318c066f05b65fe82a2fd856203407653aa242c5875bd016f68d169951aec61958f4ad9654ecc1c8edc686e55c601e3db45f4cc8a01b8414e3259ec82771a0c83d0b5db72c0199549efa80736e6e1f892c50504d187eb505f784cb8623ce475195fe1287ceb85bccf703fca919da23940ce29e4f9f1a7ba01',
        'gas_limit': 800000000,
        'gas_used': 0,
        'hash': '0xa4852f7e1b8ce036b057087e54492524796e0a68bba07a1c110605cf2cb8c01d',
        'logs_bloom': '0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
        'miner': '0x0000000000000000000000000000000000000000',
        'mix_hash': '0x63746963616c2062797a616e74696e65206661756c7420746f6c6572616e6365',
        'nonce': '0x0000000000000000',
        'parent_hash': '0x307166a396b99259ed2072f4b99d850e332db4ef4c72656870680728944ad445',
        'receipts_root': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
        'sha3_uncles': '0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347',
        'size': 902,
        'state_root': '0x260aa025c613224aaa46e2134b6469f3d956c07949a6ca23143936c574838995',
        'timestamp': 1638960161,
        'transactions': [],
        'transactions_root': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
    }
    block_2 = {
        'number': 2,
        'difficulty': 1,
        'proof_of_authority_data': '0xd983010907846765746889676f312e31332e3135856c696e7578000000000000f90164f8549403ee8c85944b16dfa517cb0ddefe123c7341a5349435d56a7515e824be4122f033d60063d035573a0c9447a847fbdf801154253593851ac9a2e77532353494c25d04978fd86ee604feb88f3c635d555eb6d42db8416ac645ecda42d11985f8d00d25664e336e8588d3bf595a88eb78ef200e5aa0f732a4822141420fba7ccf33248ed5a45038334c5e50561779e427a4fe4b04b08a00f8c9b8415568d4c4a3edcafaed146a43dc7046d9fcd31d5f6d64f8dcf581ba473b868f5145129066188ffef9b8a9e9065d13fa96a81f1196bad98393a70f6461245c097a01b841ea249f9f16bc3c5a13de6df4be7b6933b4908395d1517f7099cc7718ec438a8744aaa356584a3929d1dec2d596268ddbd29d476954d2080b94f82b07b223492300b841804f0f78afa930c7249a81cc3a7a2810098803c6f6cb4c2ed3778c1a0c35962e57c8a1328f670362cfbe3f30e58cac7d78f9059e379bd9c195afecb27b907faf01',
        'gas_limit': 800000000,
        'gas_used': 0,
        'hash': '0x8aade0ef6b0c8a2854b7d71503fe74b8a1edc13e95f7f117467ec2a327ea6f99',
        'logs_bloom': '0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
        'miner': '0x0000000000000000000000000000000000000000',
        'mix_hash': '0x63746963616c2062797a616e74696e65206661756c7420746f6c6572616e6365',
        'nonce': '0x0000000000000000',
        'parent_hash': '0xa4852f7e1b8ce036b057087e54492524796e0a68bba07a1c110605cf2cb8c01d',
        'receipts_root': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
        'sha3_uncles': '0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347',
        'size': 902,
        'state_root': '0x260aa025c613224aaa46e2134b6469f3d956c07949a6ca23143936c574838995',
        'timestamp': 1638960172,
        'transactions': [],
        'transactions_root': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
    }

    @staticmethod
    def filter_response_item(block_data):
        return {
            "number": block_data.get("number"),
            "hash": block_data.get("hash"),
            "transactions": block_data.get("transactions"),
            "timestamp": block_data.get("timestamp"),
            "gas_limit": block_data.get("gas_limit"),
            "gas_used": block_data.get("gas_used"),
            "size": block_data.get("size")
        }

    @staticmethod
    def insert_block_data(db, block_data):
        block_model = IDXBlockData()
        block_model.number = block_data.get("number")
        block_model.parent_hash = block_data.get("parent_hash")
        block_model.sha3_uncles = block_data.get("sha3_uncles")
        block_model.miner = block_data.get("miner")
        block_model.state_root = block_data.get("state_root")
        block_model.transactions_root = block_data.get("transactions_root")
        block_model.receipts_root = block_data.get("receipts_root")
        block_model.logs_bloom = block_data.get("logs_bloom")
        block_model.difficulty = block_data.get("difficulty")
        block_model.gas_limit = block_data.get("gas_limit")
        block_model.gas_used = block_data.get("gas_used")
        block_model.timestamp = block_data.get("timestamp")
        block_model.proof_of_authority_data = block_data.get("proof_of_authority_data")
        block_model.mix_hash = block_data.get("mix_hash")
        block_model.nonce = block_data.get("nonce")
        block_model.hash = block_data.get("hash")
        block_model.size = block_data.get("size")
        block_model.transactions = block_data.get("transactions")
        db.add(block_model)
        db.commit()

    @staticmethod
    def insert_block_data_block_number(session: Session, latest_block_number: int):
        idx_block_data_block_number = IDXBlockDataBlockNumber()
        idx_block_data_block_number.chain_id = CHAIN_ID
        idx_block_data_block_number.latest_block_number = latest_block_number
        session.add(idx_block_data_block_number)
        session.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1_1
    # IDXBlockDataBlockNumber is None
    def test_normal_1_1(self, client: TestClient, db: Session):
        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            resp = client.get(self.apiurl)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 0,
            "offset": None,
            "limit": None,
            "total": 0
        }
        assert response_data["block_data"] == []

    # Normal_1_2
    def test_normal_1_2(self, client: TestClient, db: Session):
        self.insert_block_data(db, self.block_0)
        self.insert_block_data(db, self.block_1)
        self.insert_block_data(db, self.block_2)

        self.insert_block_data_block_number(db, latest_block_number=2)

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
            "total": 3
        }
        assert response_data["block_data"] == [
            self.filter_response_item(self.block_0),
            self.filter_response_item(self.block_1),
            self.filter_response_item(self.block_2)
        ]

    # Normal_2_1
    # Query parameter: from_block_number
    def test_normal_2_1(self, client: TestClient, db: Session):
        self.insert_block_data(db, self.block_0)
        self.insert_block_data(db, self.block_1)
        self.insert_block_data(db, self.block_2)

        self.insert_block_data_block_number(db, latest_block_number=2)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"from_block_number": 1}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": None,
            "total": 3
        }
        assert response_data["block_data"] == [
            self.filter_response_item(self.block_1),
            self.filter_response_item(self.block_2)
        ]

    # Normal_2_2
    # Query parameter: to_block_number
    def test_normal_2_2(self, client: TestClient, db: Session):
        self.insert_block_data(db, self.block_0)
        self.insert_block_data(db, self.block_1)
        self.insert_block_data(db, self.block_2)

        self.insert_block_data_block_number(db, latest_block_number=2)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"to_block_number": 1}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 2,
            "offset": None,
            "limit": None,
            "total": 3
        }
        assert response_data["block_data"] == [
            self.filter_response_item(self.block_0),
            self.filter_response_item(self.block_1)
        ]

    # Normal_3_1
    # Pagination: offset
    def test_normal_3_1(self, client: TestClient, db: Session):
        self.insert_block_data(db, self.block_0)
        self.insert_block_data(db, self.block_1)
        self.insert_block_data(db, self.block_2)

        self.insert_block_data_block_number(db, latest_block_number=2)

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
            "total": 3
        }
        assert response_data["block_data"] == [
            self.filter_response_item(self.block_1),
            self.filter_response_item(self.block_2)
        ]

    # Normal_3_2
    # Pagination: limit
    def test_normal_3_2(self, client: TestClient, db: Session):
        self.insert_block_data(db, self.block_0)
        self.insert_block_data(db, self.block_1)
        self.insert_block_data(db, self.block_2)

        self.insert_block_data_block_number(db, latest_block_number=2)

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
            "total": 3
        }
        assert response_data["block_data"] == [
            self.filter_response_item(self.block_0)
        ]

    # Normal_4
    # sort_order
    def test_normal_4(self, client: TestClient, db: Session):
        self.insert_block_data(db, self.block_0)
        self.insert_block_data(db, self.block_1)
        self.insert_block_data(db, self.block_2)

        self.insert_block_data_block_number(db, latest_block_number=2)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {"sort_order": 1}
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3
        }
        assert response_data["block_data"] == [
            self.filter_response_item(self.block_2),
            self.filter_response_item(self.block_1),
            self.filter_response_item(self.block_0)
        ]

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
            'meta': {
                'code': 1,
                'title': 'NotFound'
            },
            'detail': 'This URL is not available in the current settings'
        }

    # Error_2
    # Invalid Parameter
    def test_error_2(self, client: TestClient, db: Session):
        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            params = {
                "offset": -1,
                "limit": -1,
                "from_block_number": -1,
                "to_block_number": -1
            }
            resp = client.get(self.apiurl, params=params)

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            'meta': {
                'code': 1,
                'title': 'RequestValidationError'
            },
            'detail': [
                {
                    'loc': ['query', 'offset'],
                    'msg': 'ensure this value is greater than or equal to 0',
                    'type': 'value_error.number.not_ge',
                    'ctx': {'limit_value': 0}
                },
                {
                    'loc': ['query', 'limit'],
                    'msg': 'ensure this value is greater than or equal to 0',
                    'type': 'value_error.number.not_ge',
                    'ctx': {'limit_value': 0}
                },
                {
                    'loc': ['query', 'from_block_number'],
                    'msg': 'ensure this value is greater than or equal to 0',
                    'type': 'value_error.number.not_ge',
                    'ctx': {'limit_value': 0}
                },
                {
                    'loc': ['query', 'to_block_number'],
                    'msg': 'ensure this value is greater than or equal to 0',
                    'type': 'value_error.number.not_ge',
                    'ctx': {'limit_value': 0}
                }
            ]
        }

    # Error_3
    # ResponseLimitExceededError
    def test_error_3(self, client: TestClient, db: Session):
        self.insert_block_data(db, self.block_0)
        self.insert_block_data(db, self.block_1)
        self.insert_block_data(db, self.block_2)

        self.insert_block_data_block_number(db, latest_block_number=2)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True),\
                mock.patch("app.routers.bc_explorer.BLOCK_RESPONSE_LIMIT", 2):
            resp = client.get(self.apiurl)

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            'meta': {
                'code': 4,
                'title': 'ResponseLimitExceededError'
            },
            'detail': 'Search results exceed the limit'
        }
