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
import threading
from typing import Type, TypeVar

from eth_utils import to_checksum_address
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.contract import AsyncContract
from web3.contract.async_contract import AsyncContractEvents
from web3.exceptions import (
    ABIEventNotFound,
    ABIFunctionNotFound,
    BadFunctionCallOutput,
    ContractLogicError,
    TimeExhausted,
)
from web3.types import TxReceipt

from app.exceptions import SendTransactionError
from app.model import EthereumAddress
from eth_config import ETH_CHAIN_ID, ETH_TX_GAS_LIMIT, ETH_WEB3_HTTP_PROVIDER

thread_local = threading.local()


http_provider = AsyncHTTPProvider(endpoint_uri=ETH_WEB3_HTTP_PROVIDER)
web3 = AsyncWeb3(http_provider)


class EthAsyncContractEventsView:
    def __init__(self, address: str, contract_events: AsyncContractEvents) -> None:
        self._address = address
        self._events = contract_events

    @property
    def address(self) -> str:
        return self._address

    @property
    def events(self) -> AsyncContractEvents:
        return self._events


class EthAsyncContractUtils:
    factory_map: dict[str, Type[AsyncContract]] = {}

    @staticmethod
    def get_contract_code(contract_name: str):
        """Get contract code

        :param contract_name: contract name
        :return: ABI, bytecode, deployedBytecode
        """
        contract_json = json.load(open(f"contracts/eth/{contract_name}.json", "r"))

        if "bytecode" not in contract_json.keys():
            contract_json["bytecode"] = None
            contract_json["deployedBytecode"] = None

        return (
            contract_json["abi"],
            contract_json["bytecode"],
            contract_json["deployedBytecode"],
        )

    @staticmethod
    async def deploy_contract(
        contract_name: str, args: list, deployer: EthereumAddress, private_key: bytes
    ) -> str:
        """Deploy contract

        :param contract_name: contract name
        :param args: arguments given to constructor
        :param deployer: contract deployer
        :param private_key: private key
        :return: contract address, ABI, transaction hash
        """
        contract_file = f"contracts/eth/{contract_name}.json"
        try:
            contract_json = json.load(open(contract_file, "r"))
        except FileNotFoundError as file_not_found_err:
            raise SendTransactionError(file_not_found_err)

        async_contract = web3.eth.contract(
            abi=contract_json["abi"],
            bytecode=contract_json["bytecode"],
            bytecode_runtime=contract_json["deployedBytecode"],
        )

        try:
            # Build transaction
            tx = await async_contract.constructor(*args).build_transaction(
                transaction={
                    "chainId": ETH_CHAIN_ID,
                    "from": deployer,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )
            # Send transaction
            tx_hash = await EthAsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
        except TimeExhausted as timeout_error:
            # NOTE: Time-out occurred because sending transaction stays in pending, etc.
            raise SendTransactionError(timeout_error)
        except Exception as error:
            raise SendTransactionError(error)

        return tx_hash

    @classmethod
    def get_contract(cls, contract_name: str, contract_address: EthereumAddress):
        """Get contract

        :param contract_name: contract name
        :param contract_address: contract address
        :return: Contract
        """
        contract_factory = cls.factory_map.get(contract_name)
        if contract_factory is not None:
            return contract_factory(address=to_checksum_address(contract_address))

        contract_file = f"contracts/eth/{contract_name}.json"
        contract_json = json.load(open(contract_file, "r"))
        contract_factory = web3.eth.contract(abi=contract_json["abi"])
        cls.factory_map[contract_name] = contract_factory
        return contract_factory(address=to_checksum_address(contract_address))

    T = TypeVar("T")

    @staticmethod
    async def call_function(
        contract: AsyncContract,
        function_name: str,
        args: tuple,
        default_returns: T = None,
    ) -> T:
        """Call contract function

        :param contract: Contract
        :param function_name: Function name
        :param args: Function args
        :param default_returns: Default return when web3 exceptions are raised
        :return: Return from function or default return
        """
        try:
            _function = getattr(contract.functions, function_name)
            result = await _function(*args).call()
        except (
            BadFunctionCallOutput,
            ABIFunctionNotFound,
            ContractLogicError,
        ) as web3_exception:
            if default_returns is not None:
                return default_returns
            else:
                raise web3_exception

        return result

    @staticmethod
    async def send_transaction(transaction: dict, private_key: bytes):
        """Send transaction"""
        _tx_from = transaction["from"]

        # Get nonce
        nonce = await web3.eth.get_transaction_count(_tx_from)
        transaction["nonce"] = nonce
        signed_tx = web3.eth.account.sign_transaction(
            transaction_dict=transaction, private_key=private_key
        )
        # Send Transaction
        tx_hash = await web3.eth.send_raw_transaction(
            signed_tx.raw_transaction.to_0x_hex()
        )
        return tx_hash.to_0x_hex()

    @staticmethod
    async def wait_for_transaction_receipt(tx_hash: str, timeout: int = 10):
        """Wait for transaction receipt"""
        try:
            tx_receipt: TxReceipt = await web3.eth.wait_for_transaction_receipt(
                transaction_hash=tx_hash, timeout=timeout
            )
        except TimeExhausted:
            raise

        return tx_receipt

    @staticmethod
    async def inspect_tx_failure(tx_hash: str) -> str:
        tx = await web3.eth.get_transaction(tx_hash)

        # build a new transaction to replay:
        replay_tx = {
            "to": tx.get("to"),
            "from": tx.get("from"),
            "value": tx.get("value"),
            "data": tx.get("input"),
        }

        # replay the transaction locally:
        try:
            await web3.eth.call(replay_tx, tx.blockNumber - 1)
        except ContractLogicError as e:
            if len(e.args) == 0:
                return str(e)
            if len(e.args[0].split("execution reverted: ")) == 2:
                msg = e.args[0].split("execution reverted: ")[1]
            else:
                msg = e.args[0]
            return msg
        except Exception as e:
            raise e
        raise Exception("Inspecting transaction revert is failed.")

    @staticmethod
    async def get_block_by_transaction_hash(tx_hash: str):
        """Get block by transaction hash

        :param tx_hash: transaction hash
        :return: block
        """
        tx = await web3.eth.get_transaction(tx_hash)
        block = await web3.eth.get_block(tx["blockNumber"])
        return block

    @staticmethod
    async def get_event_logs(
        contract: AsyncContract,
        event: str,
        block_from: int = None,
        block_to: int = None,
        argument_filters: dict = None,
    ):
        """Get contract event logs

        :param contract: Contract
        :param event: Event
        :param block_from: from_block
        :param block_to: to_block
        :param argument_filters: Argument filter
        :return: Event logs
        """
        try:
            _event = getattr(contract.events, event)
            result = await _event.get_logs(
                from_block=block_from,
                to_block=block_to,
                argument_filters=argument_filters,
            )
        except ABIEventNotFound:
            return []

        return result
