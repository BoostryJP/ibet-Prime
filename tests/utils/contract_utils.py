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

from config import WEB3_HTTP_PROVIDER, TX_GAS_LIMIT
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
