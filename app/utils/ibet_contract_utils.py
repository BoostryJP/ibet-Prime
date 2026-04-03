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
from typing import Any, TypeAlias, cast

from eth_typing import HexStr
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import AsyncAdaptedQueuePool, create_engine, select
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
from web3.types import TxData, TxParams, TxReceipt

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import TransactionLock
from app.utils.ibet_web3_utils import AsyncWeb3Wrapper, Web3Wrapper
from config import ASYNC_DATABASE_URL, CHAIN_ID, DATABASE_URL, TX_GAS_LIMIT

web3 = Web3Wrapper()
async_web3 = AsyncWeb3Wrapper()

ContractArtifact: TypeAlias = dict[str, Any]
EventArgumentFilters: TypeAlias = dict[str, Any] | None
TransactionHashInput: TypeAlias = str | HexStr | HexBytes


def _as_hex_str(tx_hash: TransactionHashInput) -> HexStr:
    if isinstance(tx_hash, HexBytes):
        return HexStr(tx_hash.to_0x_hex())
    return HexStr(tx_hash)


class ContractUtils:
    factory_map: dict[str, type[Contract]] = {}

    @staticmethod
    def get_contract_code(contract_name: str) -> tuple[Any, Any, Any]:
        """Get contract code

        :param contract_name: contract name
        :return: ABI, bytecode, deployedBytecode
        """
        contract_json: ContractArtifact = json.load(
            open(f"contracts/ibet/{contract_name}.json", "r")
        )

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
        contract_name: str,
        args: list[Any],
        deployer: str,
        private_key: bytes,
    ) -> tuple[str, Any, str]:
        """Deploy contract

        :param contract_name: contract name
        :param args: arguments given to constructor
        :param deployer: contract deployer
        :param private_key: private key
        :return: contract address, ABI, transaction hash
        """
        contract_file = f"contracts/ibet/{contract_name}.json"
        try:
            contract_json: ContractArtifact = json.load(open(contract_file, "r"))
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

        contract_address = tx_receipt.get("contractAddress")
        if contract_address is None:
            raise SendTransactionError(
                "Contract address not found in transaction receipt"
            )

        return cast(str, contract_address), contract_json["abi"], tx_hash

    @classmethod
    def get_contract(cls, contract_name: str, contract_address: str) -> Contract:
        """Get contract

        :param contract_name: contract name
        :param contract_address: contract address
        :return: Contract
        """
        contract_factory = cls.factory_map.get(contract_name)
        if contract_factory is not None:
            return contract_factory(address=to_checksum_address(contract_address))

        contract_file = f"contracts/ibet/{contract_name}.json"
        contract_json: ContractArtifact = json.load(open(contract_file, "r"))
        contract_factory = web3.eth.contract(abi=contract_json["abi"])
        cls.factory_map[contract_name] = contract_factory
        return contract_factory(address=to_checksum_address(contract_address))

    @staticmethod
    def call_function[T](
        contract: Contract,
        function_name: str,
        args: tuple[Any, ...],
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
    def send_transaction(
        transaction: TxParams, private_key: bytes
    ) -> tuple[str, TxReceipt]:
        """Send transaction"""
        tx_from_value = transaction.get("from")
        if tx_from_value is None:
            raise SendTransactionError("Transaction sender is required")
        tx_from = cast(str, tx_from_value)

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
                .where(TransactionLock.tx_from == tx_from)
                .limit(1)
                .with_for_update()
            ).first()
        except (OperationalError, DBAPIError) as err:
            local_session.rollback()
            local_session.close()
            raise SendTransactionError(err)

        try:
            # Get nonce
            nonce = web3.eth.get_transaction_count(cast(Any, tx_from_value))
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
    def inspect_tx_failure(tx_hash: TransactionHashInput) -> str:
        tx = web3.eth.get_transaction(_as_hex_str(tx_hash))

        # build a new transaction to replay:
        replay_tx = cast(
            TxParams,
            {
                "to": tx.get("to"),
                "from": tx.get("from"),
                "value": tx.get("value"),
                "data": tx.get("input"),
            },
        )
        block_number = tx.get("blockNumber")
        if block_number is None:
            raise SendTransactionError("Transaction has not been mined yet")

        # replay the transaction locally:
        try:
            web3.eth.call(replay_tx, block_number - 1)
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
    def get_block_by_transaction_hash(tx_hash: TransactionHashInput):
        """Get block by transaction hash

        :param tx_hash: transaction hash
        :return: block
        """
        tx = web3.eth.get_transaction(_as_hex_str(tx_hash))
        block_number = tx.get("blockNumber")
        if block_number is None:
            raise SendTransactionError("Transaction has not been mined yet")
        block = web3.eth.get_block(block_number)
        return block

    @staticmethod
    def get_transaction(tx_hash: TransactionHashInput) -> TxData:
        """Get transaction by hash

        :param tx_hash: Transaction hash
        :return: Transaction details
        """
        tx = web3.eth.get_transaction(_as_hex_str(tx_hash))
        return tx

    @staticmethod
    def get_event_logs(
        contract: Contract,
        event: str,
        block_from: int | None = None,
        block_to: int | None = None,
        argument_filters: EventArgumentFilters = None,
    ) -> list[Any]:
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
            get_logs_kwargs: dict[str, Any] = {}
            if block_from is not None:
                get_logs_kwargs["from_block"] = block_from
            if block_to is not None:
                get_logs_kwargs["to_block"] = block_to
            if argument_filters is not None:
                get_logs_kwargs["argument_filters"] = argument_filters
            result = _event.get_logs(**get_logs_kwargs)
        except ABIEventNotFound:
            return []

        return cast(list[Any], result)


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
    factory_map: dict[str, type[AsyncContract]] = {}

    @staticmethod
    def get_contract_code(contract_name: str) -> tuple[Any, Any, Any]:
        """Get contract code

        :param contract_name: contract name
        :return: ABI, bytecode, deployedBytecode
        """
        contract_json: ContractArtifact = json.load(
            open(f"contracts/ibet/{contract_name}.json", "r")
        )

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
        contract_name: str,
        args: list[Any],
        deployer: str,
        private_key: bytes,
    ) -> tuple[str, Any, str]:
        """Deploy contract

        :param contract_name: contract name
        :param args: arguments given to constructor
        :param deployer: contract deployer
        :param private_key: private key
        :return: contract address, ABI, transaction hash
        """
        contract_file = f"contracts/ibet/{contract_name}.json"
        try:
            contract_json: ContractArtifact = json.load(open(contract_file, "r"))
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

        contract_address = tx_receipt.get("contractAddress")
        if contract_address is None:
            raise SendTransactionError(
                "Contract address not found in transaction receipt"
            )

        return cast(str, contract_address), contract_json["abi"], tx_hash

    @classmethod
    def get_contract(cls, contract_name: str, contract_address: str) -> AsyncContract:
        """Get contract

        :param contract_name: contract name
        :param contract_address: contract address
        :return: Contract
        """
        contract_factory = cls.factory_map.get(contract_name)
        if contract_factory is not None:
            return contract_factory(address=to_checksum_address(contract_address))

        contract_file = f"contracts/ibet/{contract_name}.json"
        contract_json: ContractArtifact = json.load(open(contract_file, "r"))
        contract_factory = async_web3.eth.contract(abi=contract_json["abi"])
        cls.factory_map[contract_name] = contract_factory
        return contract_factory(address=to_checksum_address(contract_address))

    @staticmethod
    async def call_function[T](
        contract: AsyncContract,
        function_name: str,
        args: tuple[Any, ...],
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
    async def send_transaction(
        transaction: TxParams, private_key: bytes
    ) -> tuple[str, TxReceipt]:
        """Send transaction"""
        tx_from_value = transaction.get("from")
        if tx_from_value is None:
            raise SendTransactionError("Transaction sender is required")
        tx_from = cast(str, tx_from_value)

        # local database session
        DB_URI = ASYNC_DATABASE_URL
        async_engine = create_async_engine(
            DB_URI,
            connect_args={"server_settings": {"lock_timeout": "10000"}},
            echo=False,
            pool_pre_ping=True,
            poolclass=AsyncAdaptedQueuePool,
        )
        local_session = AsyncSession(
            autocommit=False,
            autoflush=True,
            bind=async_engine,
        )

        # Exclusive control within transaction execution address
        # 10-sec timeout
        # Lock record
        try:
            _tm = (
                await local_session.scalars(
                    select(TransactionLock)
                    .where(TransactionLock.tx_from == tx_from)
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
            nonce = await async_web3.eth.get_transaction_count(cast(Any, tx_from_value))
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
    async def send_transaction_no_wait(
        transaction: TxParams, private_key: bytes
    ) -> str:
        """Send transaction no wait"""
        tx_from_value = transaction.get("from")
        if tx_from_value is None:
            raise SendTransactionError("Transaction sender is required")
        tx_from = cast(str, tx_from_value)

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
                    .where(TransactionLock.tx_from == tx_from)
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
            nonce = await async_web3.eth.get_transaction_count(cast(Any, tx_from_value))
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
    async def wait_for_transaction_receipt(
        tx_hash: TransactionHashInput, timeout: int = 1
    ):
        """Wait for transaction receipt"""
        try:
            tx_receipt: TxReceipt = await async_web3.eth.wait_for_transaction_receipt(
                transaction_hash=_as_hex_str(tx_hash), timeout=timeout
            )
        except TimeExhausted:
            raise

        return tx_receipt

    @staticmethod
    async def inspect_tx_failure(tx_hash: TransactionHashInput) -> str:
        tx = await async_web3.eth.get_transaction(_as_hex_str(tx_hash))

        # build a new transaction to replay:
        replay_tx = cast(
            TxParams,
            {
                "to": tx.get("to"),
                "from": tx.get("from"),
                "value": tx.get("value"),
                "data": tx.get("input"),
            },
        )
        block_number = tx.get("blockNumber")
        if block_number is None:
            raise SendTransactionError("Transaction has not been mined yet")

        # replay the transaction locally:
        try:
            await async_web3.eth.call(replay_tx, block_number - 1)
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
    async def get_block_by_transaction_hash(tx_hash: TransactionHashInput):
        """Get block by transaction hash

        :param tx_hash: transaction hash
        :return: block
        """
        tx = await async_web3.eth.get_transaction(_as_hex_str(tx_hash))
        block_number = tx.get("blockNumber")
        if block_number is None:
            raise SendTransactionError("Transaction has not been mined yet")
        block = await async_web3.eth.get_block(block_number)
        return block

    @staticmethod
    async def get_transaction(tx_hash: TransactionHashInput) -> TxData:
        """Get transaction by hash

        :param tx_hash: Transaction hash
        :return: Transaction details
        """
        tx = await async_web3.eth.get_transaction(_as_hex_str(tx_hash))
        return tx

    @staticmethod
    async def get_event_logs(
        contract: AsyncContract | AsyncContractEventsView,
        event: str,
        block_from: int | None = None,
        block_to: int | None = None,
        argument_filters: EventArgumentFilters = None,
    ) -> list[Any]:
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
            get_logs_kwargs: dict[str, Any] = {}
            if block_from is not None:
                get_logs_kwargs["from_block"] = block_from
            if block_to is not None:
                get_logs_kwargs["to_block"] = block_to
            if argument_filters is not None:
                get_logs_kwargs["argument_filters"] = argument_filters
            result = await _event.get_logs(**get_logs_kwargs)
        except ABIEventNotFound:
            return []

        return cast(list[Any], result)
