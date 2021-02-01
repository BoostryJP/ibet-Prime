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

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted
from eth_utils import to_checksum_address

from config import WEB3_HTTP_PROVIDER, CHAIN_ID, TX_GAS_LIMIT
from app.exceptions import SendTransactionError

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

        # Get nonce
        nonce = web3.eth.getTransactionCount(deployer)

        # Build transaction
        tx = contract.constructor(*args).buildTransaction(
            transaction={
                "nonce": nonce,
                "chainId": CHAIN_ID,
                "from": deployer,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            }
        )

        # Send transaction
        try:
            tx_hash, txn_receipt = ContractUtils.send_transaction(
                transaction=tx,
                private_key=private_key
            )
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)

        contract_address = None
        if txn_receipt is not None:
            # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
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
        signed_tx = web3.eth.account.signTransaction(
            transaction_dict=transaction,
            private_key=private_key
        )
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction.hex())
        txn_receipt = web3.eth.waitForTransactionReceipt(
            transaction_hash=tx_hash,
            timeout=10
        )

        return tx_hash.hex(), txn_receipt
