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

import json
from unittest.mock import patch

import pytest
from hexbytes import HexBytes
from web3 import Web3
from web3.exceptions import Web3Exception

from app.exceptions import SendTransactionError
from app.utils.eth_contract_utils import EthAsyncContractUtils
from tests.account_config import default_eth_account


# Test for get_contract_code
@pytest.mark.asyncio
class TestGetContractCode:
    ########################################################
    # Normal
    ########################################################

    # <Normal_1>
    # Get contract code
    async def test_normal_1(self):
        # Get contract code
        (
            rtn_abi,
            rtn_bytecode,
            rtn_deploy_bytecode,
        ) = EthAsyncContractUtils.get_contract_code(contract_name="AuthIbetWST")

        # Assert
        expected_json = json.load(open("contracts/eth/AuthIbetWST.json", "r"))
        assert rtn_abi == expected_json["abi"]
        assert rtn_bytecode == expected_json["bytecode"]
        assert rtn_deploy_bytecode == expected_json["deployedBytecode"]

    ########################################################
    # Error
    ########################################################

    # <Error_1>
    # Contract does not exist
    async def test_error_1(self):
        with pytest.raises(FileNotFoundError):
            EthAsyncContractUtils.get_contract_code(contract_name="not_exist_contract")


# Test for deploy_contract, send_transaction
@pytest.mark.asyncio
class TestDeployContract:
    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")

    ########################################################
    # Normal
    ########################################################

    # <Normal_1>
    # Deploy contract
    async def test_normal_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Assert
        assert tx_hash is not None

    ########################################################
    # Error
    ########################################################

    # <Error_1>
    # Contract does not exist
    async def test_error_1(self):
        with pytest.raises(SendTransactionError):
            await EthAsyncContractUtils.deploy_contract(
                contract_name="NOT_EXIST_CONTRACT",
                args=[
                    "Test Token",
                    self.issuer["address"],
                ],
                deployer=self.deployer["address"],
                private_key=bytes.fromhex(self.deployer["private_key"]),
            )

    # <Error_2>
    # Send transaction error
    async def test_error_2(self):
        send_tx_mock = patch(
            target="app.utils.eth_contract_utils.EthAsyncContractUtils.send_transaction",
            side_effect=SendTransactionError,
        )

        with send_tx_mock:
            with pytest.raises(SendTransactionError):
                await EthAsyncContractUtils.deploy_contract(
                    contract_name="AuthIbetWST",
                    args=[
                        "Test Token",
                        self.issuer["address"],
                    ],
                    deployer=self.deployer["address"],
                    private_key=bytes.fromhex(self.deployer["private_key"]),
                )


# Test for get_contract, wait_for_transaction_receipt
@pytest.mark.asyncio
class TestGetContract:
    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")

    ########################################################
    # Normal
    ########################################################

    # <Normal_1>
    # Get contract
    async def test_normal_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.get("contractAddress")

        # Get contract
        contract = EthAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST",
            contract_address=contract_address,
        )
        assert contract is not None
        assert contract.address == Web3.to_checksum_address(contract_address)

    ########################################################
    # Error
    ########################################################

    # <Error_1>
    # Contract does not exist
    async def test_error_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.get("contractAddress")

        # Get contract
        with pytest.raises(FileNotFoundError):
            EthAsyncContractUtils.get_contract(
                contract_name="NOT_EXIST_CONTRACT",
                contract_address=contract_address,
            )


# Test for call_function
@pytest.mark.asyncio
class TestCallFunction:
    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")

    ########################################################
    # Normal
    ########################################################

    # <Normal_1>
    # Call function
    async def test_normal_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.get("contractAddress")

        # Get contract
        contract = EthAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST",
            contract_address=contract_address,
        )

        # Call a function
        owner_address = await EthAsyncContractUtils.call_function(
            contract=contract,
            function_name="owner",
            args=(),
        )
        assert owner_address == self.issuer["address"]

    ########################################################
    # Error
    ########################################################

    # <Error_1_1>
    # Call function that does not exist
    async def test_error_1_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.get("contractAddress")

        # Get contract
        contract = EthAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST",
            contract_address=contract_address,
        )

        # Call a function
        with pytest.raises(Web3Exception):
            await EthAsyncContractUtils.call_function(
                contract=contract,
                function_name="not_exist_function",  # This function does not exist
                args=(),
            )

    # <Error_1_2>
    async def test_error_1_2(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.get("contractAddress")

        # Get contract
        contract = EthAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST",
            contract_address=contract_address,
        )

        # Call a function
        owner_address = await EthAsyncContractUtils.call_function(
            contract=contract,
            function_name="not_exist_function",  # This function does not exist
            args=(),
            default_returns="default_value",  # Default return value if an error occurs
        )
        assert owner_address == "default_value"


# Test for get_block_by_transaction_hash
@pytest.mark.asyncio
class TestGetBlockByTransactionHash:
    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")

    ########################################################
    # Normal
    ########################################################

    # <Normal_1>
    # Get block by transaction hash
    async def test_normal_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get block by transaction hash
        block = await EthAsyncContractUtils.get_block_by_transaction_hash(tx_hash)

        # Assert
        assert block is not None
        assert HexBytes(tx_hash) in block["transactions"]


# Test for get_event_logs
@pytest.mark.asyncio
class TestGetEventLogs:
    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")

    ########################################################
    # Normal
    ########################################################

    # <Normal_1>
    # Get event logs
    async def test_normal_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.get("contractAddress")

        # Get contract
        contract = EthAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST",
            contract_address=contract_address,
        )

        # Execute a transaction to trigger an event
        # - Mint tokens to the issuer
        tx = await contract.functions.mint(
            self.issuer["address"], 1000
        ).build_transaction(
            {
                "from": self.issuer["address"],
                "gas": 2000000,
            }
        )
        tx_hash = await EthAsyncContractUtils.send_transaction(
            transaction=tx,
            private_key=bytes.fromhex(self.issuer["private_key"]),
        )
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)

        # Get event logs
        logs = await EthAsyncContractUtils.get_event_logs(
            contract=contract,
            event="Mint",
            block_from=tx_receipt["blockNumber"],
        )

        # Assert
        assert logs is not None
        assert len(logs) == 1

        assert logs[0]["event"] == "Mint"
        assert logs[0]["args"]["to"] == self.issuer["address"]
        assert logs[0]["args"]["amount"] == 1000

    ########################################################
    # Error
    ########################################################

    # <Error_1>
    # Get event logs with non-existent event
    async def test_error_1(self):
        # Deploy contract
        tx_hash = await EthAsyncContractUtils.deploy_contract(
            contract_name="AuthIbetWST",
            args=[
                "Test Token",
                self.issuer["address"],
            ],
            deployer=self.deployer["address"],
            private_key=bytes.fromhex(self.deployer["private_key"]),
        )

        # Get transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        contract_address = tx_receipt.get("contractAddress")

        # Get contract
        contract = EthAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST",
            contract_address=contract_address,
        )

        # Execute a transaction to trigger an event
        # - Mint tokens to the issuer
        tx = await contract.functions.mint(
            self.issuer["address"], 1000
        ).build_transaction(
            {
                "from": self.issuer["address"],
                "gas": 2000000,
            }
        )
        tx_hash = await EthAsyncContractUtils.send_transaction(
            transaction=tx,
            private_key=bytes.fromhex(self.issuer["private_key"]),
        )
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)

        # Get event logs
        logs = await EthAsyncContractUtils.get_event_logs(
            contract=contract,
            event="NotExistEvent",  # This event does not exist
            block_from=tx_receipt["blockNumber"],
        )

        # Assert
        assert logs == []
