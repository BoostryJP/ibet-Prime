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
from typing import Tuple
import json

from web3 import contract
from web3.exceptions import (
    TimeExhausted,
    BadFunctionCallOutput,
    ABIFunctionNotFound,
    ABIEventFunctionNotFound
)
from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from config import (
    CHAIN_ID,
    TX_GAS_LIMIT,
    DATABASE_URL
)
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import SendTransactionError
from app.model.db import TransactionLock

web3 = Web3Wrapper()


class ContractUtils:

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

        return contract_json["abi"], \
               contract_json["bytecode"], \
               contract_json["deployedBytecode"]

    @staticmethod
    def deploy_contract(
            contract_name: str,
            args: list,
            deployer: str,
            private_key: str
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
            tx = contract.constructor(*args).buildTransaction(
                transaction={
                    "chainId": CHAIN_ID,
                    "from": deployer,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                }
            )
            # Send transaction
            tx_hash, tx_receipt = ContractUtils.send_transaction(
                transaction=tx,
                private_key=private_key
            )
        except TimeExhausted as timeout_error:
            # NOTE: Time-out occurred because sending transaction stays in pending, etc.
            raise SendTransactionError(timeout_error)
        except Exception as error:
            raise SendTransactionError(error)

        contract_address = None
        if tx_receipt is not None:
            # Check if contract address is registered from transaction receipt result.
            if 'contractAddress' in tx_receipt.keys():
                contract_address = tx_receipt['contractAddress']

        return contract_address, contract_json['abi'], tx_hash

    @staticmethod
    def get_contract(contract_name: str, contract_address: str):
        """Get contract

        :param contract_name: contract name
        :param contract_address: contract address
        :return: Contract
        """
        contract_file = f"contracts/{contract_name}.json"
        contract_json = json.load(open(contract_file, "r"))
        contract = web3.eth.contract(
            address=to_checksum_address(contract_address),
            abi=contract_json['abi'],
        )
        return contract

    @staticmethod
    def call_function(contract: contract,
                      function_name: str,
                      args: tuple,
                      default_returns=None):
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
        except (BadFunctionCallOutput, ABIFunctionNotFound) as web3_exception:
            if default_returns is not None:
                return default_returns
            else:
                raise web3_exception

        return result

    @staticmethod
    def send_transaction(transaction: dict, private_key: str):
        """Send transaction"""
        _tx_from = transaction["from"]

        # local database session
        DB_URI = DATABASE_URL
        db_engine = create_engine(
            DB_URI,
            connect_args={"options": "-c lock_timeout=10000"},
            echo=False,
            pool_pre_ping=True
        )
        local_session = Session(autocommit=False, autoflush=True, bind=db_engine)

        # Exclusive control within transaction execution address
        # 10-sec timeout
        # Lock record
        try:
            _tm = local_session.query(TransactionLock). \
                filter(TransactionLock.tx_from == _tx_from). \
                populate_existing(). \
                with_for_update(). \
                first()
        except OperationalError as op_err:
            local_session.rollback()
            local_session.close()
            raise SendTransactionError(op_err)

        try:
            # Get nonce
            nonce = web3.eth.getTransactionCount(_tx_from)
            transaction["nonce"] = nonce
            signed_tx = web3.eth.account.sign_transaction(
                transaction_dict=transaction,
                private_key=private_key
            )
            # Send Transaction
            tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction.hex())
            tx_receipt = web3.eth.waitForTransactionReceipt(
                transaction_hash=tx_hash,
                timeout=10
            )
            if tx_receipt["status"] == 0:
                raise SendTransactionError
        except:
            raise
        finally:
            local_session.rollback()  # unlock record
            local_session.close()

        return tx_hash.hex(), tx_receipt

    @staticmethod
    def get_block_by_transaction_hash(tx_hash: str):
        """Get block by transaction hash

        :param tx_hash: transaction hash
        :return: block
        """
        tx = web3.eth.getTransaction(tx_hash)
        block = web3.eth.get_block(tx["blockNumber"])
        return block

    @staticmethod
    def get_event_logs(contract: contract,
                       event: str,
                       block_from: int = None,
                       block_to: int = None,
                       argument_filters: dict = None):
        """Get contract event logs

        :param contract: Contract
        :param event: Event
        :param block_from: fromBlock
        :param block_to: toBlock
        :return: Event logs
        """
        try:
            _event = getattr(contract.events, event)
            result = _event.getLogs(
                fromBlock=block_from,
                toBlock=block_to,
                argument_filters=argument_filters
            )
        except ABIEventFunctionNotFound:
            return []

        return result
