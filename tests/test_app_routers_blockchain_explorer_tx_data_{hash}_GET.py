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

from eth_utils import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import IDXTxData, Token, TokenVersion


class TestGetTxData:
    # API to be tested
    apiurl = "/blockchain_explorer/tx_data/{}"

    # Test data
    tx_data = {
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
    def insert_tx_data(session, tx_data):
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
        session.add(tx_model)
        session.commit()

    @staticmethod
    def insert_token_data(session, token_info):
        token = Token()
        token.type = token_info.get("type")
        token.tx_hash = ""
        token.issuer_address = ""
        token.token_address = token_info.get("token_address")
        token.abi = ""
        token.version = TokenVersion.V_24_6
        session.add(token)
        session.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # Contract information is not set
    def test_normal_1(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.tx_data)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            resp = client.get(
                self.apiurl.format(
                    "0x403f9cea4db07aecf71a440c45ae415569cb218bb1a7f4d3a2d83004e29d1644"
                )
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "hash": "0x403f9cea4db07aecf71a440c45ae415569cb218bb1a7f4d3a2d83004e29d1644",
            "block_hash": "0x6698ebc4866223855dbea153eec7a9455682fd6d2f8451746102afb320412a6b",
            "block_number": 10407084,
            "transaction_index": 0,
            "from_address": "0x8456ac4FEc4869A16ad5C3584306181Af6410682",
            "to_address": "0xECeB9FdBd2CF677Be5fA8B1ceEb53e53D582f0Eb",
            "contract_name": None,
            "contract_function": None,
            "contract_parameters": None,
            "gas": 6000000,
            "gas_price": 0,
            "value": 0,
            "nonce": 199601,
        }

    # Normal_2
    # Contract information is set
    def test_normal_2(self, client: TestClient, db: Session):
        self.insert_tx_data(db, self.tx_data)

        token_info = {
            "token_address": to_checksum_address(self.tx_data.get("to_address")),
            "type": "IbetShare",
        }
        self.insert_token_data(db, token_info)

        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            resp = client.get(
                self.apiurl.format(
                    "0x403f9cea4db07aecf71a440c45ae415569cb218bb1a7f4d3a2d83004e29d1644"
                )
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "hash": "0x403f9cea4db07aecf71a440c45ae415569cb218bb1a7f4d3a2d83004e29d1644",
            "block_hash": "0x6698ebc4866223855dbea153eec7a9455682fd6d2f8451746102afb320412a6b",
            "block_number": 10407084,
            "transaction_index": 0,
            "from_address": "0x8456ac4FEc4869A16ad5C3584306181Af6410682",
            "to_address": "0xECeB9FdBd2CF677Be5fA8B1ceEb53e53D582f0Eb",
            "contract_name": "IbetShare",
            "contract_function": "approveTransfer",
            "contract_parameters": {"_index": 1, "_data": "1652976627.637778"},
            "gas": 6000000,
            "gas_price": 0,
            "value": 0,
            "nonce": 199601,
        }

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # BC_EXPLORER_ENABLED = False (default)
    def test_error_1(self, client: TestClient, db: Session):
        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", False):
            resp = client.get(
                self.apiurl.format(
                    "0x403f9cea4db07aecf71a440c45ae415569cb218bb1a7f4d3a2d83004e29d1644"
                )
            )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "This URL is not available in the current settings",
        }

    # Error_2
    # DataNotExistsError
    def test_error_2(self, client: TestClient, db: Session):
        # Request target API
        with mock.patch("app.routers.bc_explorer.BC_EXPLORER_ENABLED", True):
            resp = client.get(
                self.apiurl.format(
                    "0x403f9cea4db07aecf71a440c45ae415569cb218bb1a7f4d3a2d83004e29d1644"
                )
            )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "block data not found",
        }
