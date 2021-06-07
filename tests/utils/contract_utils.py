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
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.utils.contract_utils import ContractUtils
from config import (
    WEB3_HTTP_PROVIDER,
    TX_GAS_LIMIT,
    CHAIN_ID
)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

"""
Helper Methods for Contract Testing

Helper methods to make it easier for test code to handle operations 
on contracts that are not executed by the issuer.
"""


class PersonalInfoContractTestUtils:

    @staticmethod
    def register(contract_address: str, tx_from: str, private_key: str, args: list):
        personal_info_contract = ContractUtils.get_contract(
            contract_name="PersonalInfo",
            contract_address=contract_address
        )
        tx = personal_info_contract.functions. \
            register(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)


class IbetShareContractTestUtils:

    @staticmethod
    def apply_for_transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        share_contract = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=contract_address
        )
        tx = share_contract.functions.\
            applyForTransfer(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)
