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

from app.exceptions import ContractRevertError, SendTransactionError
from app.model import EthereumAddress
from app.utils.ibet_contract_utils import AsyncContractUtils
from app.utils.ibet_web3_utils import Web3Wrapper
from config import CHAIN_ID, TX_GAS_LIMIT

web3 = Web3Wrapper()


class TokenListContract:
    """TokenList contract"""

    def __init__(self, contract_address: str):
        self.contract_address = contract_address

    async def register(
        self,
        token_address: str,
        token_template: str,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> None:
        """Register TokenList

        :param token_address: token address
        :param token_template: token type
        :param tx_sender: transaction from
        :param tx_sender_key: private_key
        :return: None
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name="TokenList",
                contract_address=self.contract_address,
            )
            tx = await contract.functions.register(
                token_address, token_template
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)
