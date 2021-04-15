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

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted

from config import (
    WEB3_HTTP_PROVIDER,
    CHAIN_ID,
    TX_GAS_LIMIT
)
from app.exceptions import SendTransactionError
from .utils import ContractUtils

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TokenListContract:

    @staticmethod
    def create(account_address: str, private_key: str) -> Tuple[str, dict, str]:
        """Deploy token

        :param account_address: deployer_address
        :param private_key: deployer's private key
        :return: contract address, ABI, transaction hash
        """
        contract_address, abi, tx_hash = ContractUtils.deploy_contract(
            contract_name="TokenList",
            args=[],
            deployer=account_address,
            private_key=private_key
        )
        return contract_address, abi, tx_hash

    @staticmethod
    def register(
            token_list_address: str,
            token_address: str,
            token_template: str,
            account_address: str,
            private_key: str
    ) -> None:
        """Register TokenList

        :param token_list_address: token list contract address
        :param token_address: token_address
        :param token_template: TokenType
        :param account_address: token owner account address
        :param private_key: private_key
        :return: None
        """
        try:
            contract = ContractUtils.get_contract(
                contract_name="TokenList",
                contract_address=token_list_address,
            )
            tx = contract.functions.register(token_address, token_template). \
                buildTransaction({
                    "chainId": CHAIN_ID,
                    "from": account_address,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)

        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)
