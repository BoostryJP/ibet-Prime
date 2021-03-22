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
import time

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted
from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config import WEB3_HTTP_PROVIDER, CHAIN_ID, TX_GAS_LIMIT, DATABASE_URL
from app.exceptions import SendTransactionError
from app.model.db import TransactionLock

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class ContractUtils:

    @staticmethod
    def get_contract_code(contract_name: str):
        """Get contract code

        :param contract_name: contract name
        :return: ABI, bytecode, deployedBytecode
        """
        contract_json = json.load(open(f"contracts/{contract_name}.json", "r"))

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
        contract_json = json.load(open(contract_file, "r"))

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
            tx_hash, txn_receipt = ContractUtils.send_transaction(
                transaction=tx,
                private_key=private_key
            )
        except TimeExhausted as timeout_error:
            # NOTE: Time-out occurred because sending transaction stays in pending, etc.
            raise SendTransactionError(timeout_error)
        except Exception as error:
            raise SendTransactionError(error)

        contract_address = None
        if txn_receipt is not None:
            # Check if contract address is registered from transaction receipt result.
            if 'contractAddress' in txn_receipt.keys():
                contract_address = txn_receipt['contractAddress']

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
    def send_transaction(transaction: dict, private_key: str):
        """Send transaction"""
        _tx_from = transaction["from"]

        # local database session
        DB_URI = DATABASE_URL
        db_engine = create_engine(DB_URI, echo=False)
        local_session = Session(autocommit=False, autoflush=True, bind=db_engine)

        # exclusive control within transaction execution address
        # 10-sec timeout
        start_time = time.time()
        while True:
            if time.time() - start_time > 10:
                local_session.close()
                raise TimeExhausted
            else:
                # lock record
                _tm = local_session.query(TransactionLock). \
                    filter(TransactionLock.tx_from == _tx_from). \
                    populate_existing(). \
                    with_for_update(). \
                    first()
                break

        try:
            nonce = web3.eth.getTransactionCount(_tx_from)
            transaction["nonce"] = nonce
            signed_tx = web3.eth.account.sign_transaction(
                transaction_dict=transaction,
                private_key=private_key
            )
            tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction.hex())
            txn_receipt = web3.eth.waitForTransactionReceipt(
                transaction_hash=tx_hash,
                timeout=10
            )
            if txn_receipt["status"] == 0:
                raise SendTransactionError
        except:
            raise
        finally:
            local_session.rollback()  # unlock record
            local_session.close()

        return tx_hash.hex(), txn_receipt
