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
from typing import Tuple, Type, TypeVar

from eth_typing import HexStr
from eth_utils import to_checksum_address
from sqlalchemy import create_engine, select
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session
from web3.contract import AsyncContract, Contract
from web3.contract.async_contract import AsyncContractEvents
from web3.exceptions import (
    ABIEventNotFound,
    ABIFunctionNotFound,
    BadFunctionCallOutput,
    ContractLogicError,
    TimeExhausted,
)
from web3.types import TxReceipt

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import TransactionLock
from app.utils.web3_utils import AsyncWeb3Wrapper, Web3Wrapper
from config import CHAIN_ID, DATABASE_URL, TX_GAS_LIMIT

web3 = Web3Wrapper()
async_web3 = AsyncWeb3Wrapper()


class ContractUtils:
    factory_map: dict[str, Type[Contract]] = {}

    @staticmethod
    def get_contract_code(contract_name: str):
        """Get contract code

        :param contract_name: contract name
        :return: ABI, bytecode, deployedBytecode
        """
        contract_json = json.load(open(f"contracts/{contract_name}.json", "r"))

        if "bytecode" not in contract_json.keys():
            contract_json["bytecode"] = None
            contract_json["deployedBytecode"] = None

        return (
            contract_json["abi"],
            contract_json["bytecode"],
            contract_json["deployedBytecode"],
        )

    @staticmethod
    def deploy_contract(
        contract_name: str, args: list, deployer: str, private_key: bytes
    ) -> Tuple[str, dict, str]:
        """Deploy contract

        :param contract_name: contract name
        :param args: arguments given to constructor
        :param deployer: contract deployer
        :param private_key: private key
        :return: contract address, ABI, transaction hash
        """
        contract_file = f"contracts/{contract_name}.json"
        try:
            contract_json = json.load(open(contract_file, "r"))
        except FileNotFoundError as file_not_found_err:
            raise SendTransactionError(file_not_found_err)

        contract = web3.eth.contract(
            abi=contract_json["abi"],
            bytecode=contract_json["bytecode"],
            bytecode_runtime=contract_json["deployedBytecode"],
        )

        try:
            # Build transaction
            tx = contract.constructor(*args).build_transaction(
                transaction={
                    "chainId": CHAIN_ID,
                    "from": deployer,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            # Send transaction
            tx_hash, tx_receipt = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
        except TimeExhausted as timeout_error:
            # NOTE: Time-out occurred because sending transaction stays in pending, etc.
            raise SendTransactionError(timeout_error)
        except Exception as error:
            raise SendTransactionError(error)

        contract_address = None
        if tx_receipt is not None:
            # Check if contract address is registered from transaction receipt result.
            if "contractAddress" in tx_receipt.keys():
                contract_address = tx_receipt["contractAddress"]

        return contract_address, contract_json["abi"], tx_hash

    @classmethod
    def get_contract(cls, contract_name: str, contract_address: str):
        """Get contract

        :param contract_name: contract name
        :param contract_address: contract address
        :return: Contract
        """
        contract_factory = cls.factory_map.get(contract_name)
        if contract_factory is not None:
            return contract_factory(address=to_checksum_address(contract_address))

        contract_file = f"contracts/{contract_name}.json"
        contract_json = json.load(open(contract_file, "r"))
        contract_factory = web3.eth.contract(abi=contract_json["abi"])
        cls.factory_map[contract_name] = contract_factory
        return contract_factory(address=to_checksum_address(contract_address))

    T = TypeVar("T")

    @staticmethod
    def call_function(
        contract: Contract, function_name: str, args: tuple, default_returns: T = None
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
            result = _function(*args).call()
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
    def send_transaction(transaction: dict, private_key: bytes):
        """Send transaction"""
        _tx_from = transaction["from"]

        # local database session
        DB_URI = DATABASE_URL
        db_engine = create_engine(
            DB_URI,
            connect_args={"options": "-c lock_timeout=10000"},
            echo=False,
            pool_pre_ping=True,
        )
        local_session = Session(autocommit=False, autoflush=True, bind=db_engine)

        # Exclusive control within transaction execution address
        # 10-sec timeout
        # Lock record
        try:
            _tm = local_session.scalars(
                select(TransactionLock)
                .where(TransactionLock.tx_from == _tx_from)
                .limit(1)
                .with_for_update()
            ).first()
        except (OperationalError, DBAPIError) as err:
            local_session.rollback()
            local_session.close()
            raise SendTransactionError(err)

        try:
            # Get nonce
            nonce = web3.eth.get_transaction_count(_tx_from)
            transaction["nonce"] = nonce
            signed_tx = web3.eth.account.sign_transaction(
                transaction_dict=transaction, private_key=private_key
            )
            # Send Transaction
            tx_hash = web3.eth.send_raw_transaction(
                signed_tx.raw_transaction.to_0x_hex()
            )
            tx_receipt = web3.eth.wait_for_transaction_receipt(
                transaction_hash=tx_hash, timeout=10
            )
            if tx_receipt["status"] == 0:
                # inspect reason of transaction fail
                code_msg = ContractUtils.inspect_tx_failure(tx_hash.to_0x_hex())
                raise ContractRevertError(code_msg=code_msg)
        except:
            raise
        finally:
            local_session.rollback()  # unlock record
            local_session.close()

        return tx_hash.to_0x_hex(), tx_receipt

    @staticmethod
    def inspect_tx_failure(tx_hash: str) -> str:
        tx = web3.eth.get_transaction(tx_hash)

        # build a new transaction to replay:
        replay_tx = {
            "to": tx.get("to"),
            "from": tx.get("from"),
            "value": tx.get("value"),
            "data": tx.get("input"),
        }

        # replay the transaction locally:
        try:
            web3.eth.call(replay_tx, tx.blockNumber - 1)
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
    def get_block_by_transaction_hash(tx_hash: str):
        """Get block by transaction hash

        :param tx_hash: transaction hash
        :return: block
        """
        tx = web3.eth.get_transaction(tx_hash)
        block = web3.eth.get_block(tx["blockNumber"])
        return block

    @staticmethod
    def get_event_logs(
        contract: Contract,
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
            result = _event.get_logs(
                from_block=block_from,
                to_block=block_to,
                argument_filters=argument_filters,
            )
        except ABIEventNotFound:
            return []

        return result


class AsyncContractEventsView:
    def __init__(self, address: str, contract_events: AsyncContractEvents) -> None:
        self._address = address
        self._events = contract_events

    @property
    def address(self) -> str:
        return self._address

    @property
    def events(self) -> AsyncContractEvents:
        return self._events


class AsyncContractUtils:
    factory_map: dict[str, Type[AsyncContract]] = {}

    @staticmethod
    def get_contract_code(contract_name: str):
        """Get contract code

        :param contract_name: contract name
        :return: ABI, bytecode, deployedBytecode
        """
        contract_json = json.load(open(f"contracts/{contract_name}.json", "r"))

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
        contract_name: str, args: list, deployer: str, private_key: bytes
    ) -> Tuple[str, dict, str]:
        """Deploy contract

        :param contract_name: contract name
        :param args: arguments given to constructor
        :param deployer: contract deployer
        :param private_key: private key
        :return: contract address, ABI, transaction hash
        """
        contract_file = f"contracts/{contract_name}.json"
        try:
            contract_json = json.load(open(contract_file, "r"))
        except FileNotFoundError as file_not_found_err:
            raise SendTransactionError(file_not_found_err)

        async_contract = async_web3.eth.contract(
            abi=contract_json["abi"],
            bytecode=contract_json["bytecode"],
            bytecode_runtime=contract_json["deployedBytecode"],
        )

        try:
            # Build transaction
            tx = await async_contract.constructor(*args).build_transaction(
                transaction={
                    "chainId": CHAIN_ID,
                    "from": deployer,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            # Send transaction
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
        except TimeExhausted as timeout_error:
            # NOTE: Time-out occurred because sending transaction stays in pending, etc.
            raise SendTransactionError(timeout_error)
        except Exception as error:
            raise SendTransactionError(error)

        contract_address = None
        if tx_receipt is not None:
            # Check if contract address is registered from transaction receipt result.
            if "contractAddress" in tx_receipt.keys():
                contract_address = tx_receipt["contractAddress"]

        return contract_address, contract_json["abi"], tx_hash

    @classmethod
    def get_contract(cls, contract_name: str, contract_address: str):
        """Get contract

        :param contract_name: contract name
        :param contract_address: contract address
        :return: Contract
        """
        contract_factory = cls.factory_map.get(contract_name)
        if contract_factory is not None:
            return contract_factory(address=to_checksum_address(contract_address))

        contract_file = f"contracts/{contract_name}.json"
        contract_json = json.load(open(contract_file, "r"))
        contract_factory = async_web3.eth.contract(abi=contract_json["abi"])
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

        # local database session
        DB_URI = DATABASE_URL
        db_engine = create_async_engine(
            DB_URI,
            connect_args={"options": "-c lock_timeout=10000"},
            echo=False,
            pool_pre_ping=True,
        )
        local_session = AsyncSession(
            autocommit=False,
            autoflush=True,
            bind=db_engine,
        )

        # Exclusive control within transaction execution address
        # 10-sec timeout
        # Lock record
        try:
            _tm = (
                await local_session.scalars(
                    select(TransactionLock)
                    .where(TransactionLock.tx_from == _tx_from)
                    .limit(1)
                    .with_for_update()
                )
            ).first()
        except (OperationalError, DBAPIError) as err:
            await local_session.rollback()
            await local_session.close()
            raise SendTransactionError(err)

        try:
            # Get nonce
            nonce = await async_web3.eth.get_transaction_count(_tx_from)
            transaction["nonce"] = nonce
            signed_tx = async_web3.eth.account.sign_transaction(
                transaction_dict=transaction, private_key=private_key
            )
            # Send Transaction
            tx_hash = await async_web3.eth.send_raw_transaction(
                signed_tx.raw_transaction.to_0x_hex()
            )
            tx_receipt = await async_web3.eth.wait_for_transaction_receipt(
                transaction_hash=tx_hash, timeout=10
            )
            if tx_receipt["status"] == 0:
                # inspect reason of transaction fail
                code_msg = await AsyncContractUtils.inspect_tx_failure(
                    tx_hash.to_0x_hex()
                )
                raise ContractRevertError(code_msg=code_msg)
        except:
            raise
        finally:
            await local_session.rollback()  # unlock record
            await local_session.close()

        return tx_hash.to_0x_hex(), tx_receipt

    @staticmethod
    async def send_transaction_no_wait(transaction: dict, private_key: bytes):
        """Send transaction no wait"""
        _tx_from = transaction["from"]

        # local database session
        DB_URI = DATABASE_URL
        db_engine = create_async_engine(
            DB_URI,
            connect_args={"options": "-c lock_timeout=10000"},
            echo=False,
            pool_pre_ping=True,
        )
        local_session = AsyncSession(
            autocommit=False,
            autoflush=True,
            bind=db_engine,
        )

        # Exclusive control within transaction execution address
        # 10-sec timeout
        # Lock record
        try:
            _tm = (
                await local_session.scalars(
                    select(TransactionLock)
                    .where(TransactionLock.tx_from == _tx_from)
                    .limit(1)
                    .with_for_update()
                )
            ).first()
        except (OperationalError, DBAPIError) as err:
            await local_session.rollback()
            await local_session.close()
            raise SendTransactionError(err)

        try:
            # Get nonce
            nonce = await async_web3.eth.get_transaction_count(_tx_from)
            transaction["nonce"] = nonce
            signed_tx = async_web3.eth.account.sign_transaction(
                transaction_dict=transaction, private_key=private_key
            )
            # Send Transaction
            tx_hash = await async_web3.eth.send_raw_transaction(
                signed_tx.raw_transaction.to_0x_hex()
            )
        except:
            raise
        finally:
            await local_session.rollback()  # unlock record
            await local_session.close()

        return tx_hash.to_0x_hex()

    @staticmethod
    async def wait_for_transaction_receipt(tx_hash: HexStr, timeout: int = 1):
        """Wait for transaction receipt"""
        try:
            tx_receipt: TxReceipt = await async_web3.eth.wait_for_transaction_receipt(
                transaction_hash=tx_hash, timeout=timeout
            )
        except TimeExhausted:
            raise

        return tx_receipt

    @staticmethod
    async def inspect_tx_failure(tx_hash: str) -> str:
        tx = await async_web3.eth.get_transaction(tx_hash)

        # build a new transaction to replay:
        replay_tx = {
            "to": tx.get("to"),
            "from": tx.get("from"),
            "value": tx.get("value"),
            "data": tx.get("input"),
        }

        # replay the transaction locally:
        try:
            await async_web3.eth.call(replay_tx, tx.blockNumber - 1)
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
        tx = await async_web3.eth.get_transaction(tx_hash)
        block = await async_web3.eth.get_block(tx["blockNumber"])
        return block

    @staticmethod
    async def get_event_logs(
        contract: AsyncContract | AsyncContractEventsView,
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
