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
from web3 import Web3
from web3.middleware import geth_poa_middleware

from config import (
    WEB3_HTTP_PROVIDER,
    TX_GAS_LIMIT,
    CHAIN_ID
)
from app.exceptions import SendTransactionError
from app.model.blockchain.utils import ContractUtils

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestContractUtils:

    @staticmethod
    def deploy_contract(contract_name: str, args: list, deployer: dict):
        contract_file = f"contracts/{contract_name}.json"
        contract_json = json.load(open(contract_file, "r"))
        contract = web3.eth.contract(
            abi=contract_json["abi"],
            bytecode=contract_json["bytecode"],
            bytecode_runtime=contract_json["deployedBytecode"],
        )

        tx_hash = contract.constructor(*args).transact({
            "from": deployer["address"],
            "gas": TX_GAS_LIMIT
        })
        tx = web3.eth.waitForTransactionReceipt(tx_hash)

        contract_address = ""
        if tx is not None:
            if "contractAddress" in tx.keys():
                contract_address = tx["contractAddress"]

        return contract_address, contract_json["abi"], tx_hash

    @staticmethod
    def set_personal_info(contract_address: str, tx_from: str, private_key: str, personal_info_contract_address: str):
        try:
            share_contract = ContractUtils.get_contract(
                contract_name="IbetShare",
                contract_address=contract_address
            )
            tx = share_contract.functions. \
                setPersonalInfoAddress(personal_info_contract_address). \
                buildTransaction({
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except Exception as ex_info:
            raise SendTransactionError(ex_info)

    @staticmethod
    def set_transfer_approval_required(contract_address: str, tx_from: str, private_key: str):
        try:
            share_contract = ContractUtils.get_contract(
                contract_name="IbetShare",
                contract_address=contract_address
            )
            tx = share_contract.functions. \
                setTransferApprovalRequired(True). \
                buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except Exception as ex_info:
            raise SendTransactionError(ex_info)

    @staticmethod
    def apply_for_transfer(contract_address: str, tx_from: str, private_key: str,
                            to_address: str, value: int, data: str):
        try:
            share_contract = ContractUtils.get_contract(
                contract_name="IbetShare",
                contract_address=contract_address
            )
            tx = share_contract.functions. \
                applyForTransfer(to_address, value, data). \
                buildTransaction({
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except Exception as ex_info:
            raise SendTransactionError(ex_info)

    @staticmethod
    def register_personal_info(issuer_address: str, to_address: str, private_key: str) -> str:
        try:
            contract_address, abi, tx_hash = ContractUtils.deploy_contract(
                contract_name="PersonalInfo",
                deployer=to_address,
                args={},
                private_key=private_key
            )
            personal_info_contract = ContractUtils.get_contract(
                contract_name="PersonalInfo",
                contract_address=contract_address
            )
            tx = personal_info_contract.functions. \
                register(issuer_address, "encrypted_personal_info"). \
                buildTransaction({
                    "chainId": CHAIN_ID,
                    "from": to_address,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            return contract_address
        except Exception as ex_info:
            raise SendTransactionError(ex_info)

    ###########################################################################


# Issue IbetStraightBond Token
def issue_bond_token(invoker: dict, attribute: dict):
    arguments = [
        attribute["name"], attribute["symbol"], attribute["totalSupply"],
        attribute["faceValue"],
        attribute["redemptionDate"], attribute["redemptionValue"],
        attribute["returnDate"], attribute["returnAmount"],
        attribute["purpose"]
    ]

    contract_address, abi, tx_hash = TestContractUtils.deploy_contract(
        contract_name="IbetStraightBond",
        args=arguments,
        deployer=invoker
    )

    # Other settings
    token_contract = ContractUtils.get_contract("IbetStraightBond", contract_address)
    transaction = {
        "from": invoker["address"],
        "gas": TX_GAS_LIMIT
    }

    if attribute.get("tradableExchange") is not None:
        token_contract.functions.\
            setTradableExchange(attribute["tradableExchange"]).\
            transact(transaction=transaction)

    if attribute.get("personalInfoAddress") is not None:
        token_contract.functions.\
            setPersonalInfoAddress(attribute["personalInfoAddress"]).\
            transact(transaction=transaction)

    if attribute.get("contactInformation") is not None:
        token_contract.functions.\
            setContactInformation(attribute["contactInformation"]).\
            transact(transaction=transaction)

    if attribute.get("privacyPolicy") is not None:
        token_contract.functions.\
            setPrivacyPolicy(attribute["privacyPolicy"]).\
            transact(transaction=transaction)

    if attribute.get("imageURL") is not None:
        for (_class, _url) in enumerate(attribute["imageURL"]):
            token_contract.functions.\
                setImageURL(_class, _url).\
                transact(transaction=transaction)

    if attribute.get("interestRate") is not None:
        token_contract.functions.\
            setInterestRate(attribute["interestRate"]).\
            transact(transaction=transaction)

    interest_payment_date = {
        f"interestPaymentDate{index}": attribute[f"interestPaymentDate{index}"] for index in range(1, 13)
        if f"interestPaymentDate{index}" in attribute and attribute[f"interestPaymentDate{index}"] is not None
    }
    if interest_payment_date != {}:
        token_contract.functions.\
            setInterestPaymentDate(json.dumps(interest_payment_date)). \
            transact(transaction=transaction)

    if attribute.get("transferable") is not None:
        token_contract.functions.\
            setTransferable(attribute["transferable"]).\
            transact(transaction=transaction)

    return {"address": contract_address, "abi": abi, "tx_hash": tx_hash}
