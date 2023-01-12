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
from web3.exceptions import TimeExhausted

from config import (
    CHAIN_ID,
    TX_GAS_LIMIT
)
from app.exceptions import SendTransactionError, ContractRevertError
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper

web3 = Web3Wrapper()


class TokenListContract:

    def __init__(self, contract_address: str):
        self.contract_address = contract_address

    def register(self,
                 token_address: str, token_template: str,
                 tx_from: str, private_key: str) -> None:
        """Register TokenList

        :param token_address: token address
        :param token_template: token type
        :param tx_from: transaction from
        :param private_key: private_key
        :return: None
        """
        try:
            contract = ContractUtils.get_contract(
                contract_name="TokenList",
                contract_address=self.contract_address,
            )
            tx = contract.functions.register(
                token_address,
                token_template
            ).build_transaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            ContractUtils.send_transaction(
                transaction=tx,
                private_key=private_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)
