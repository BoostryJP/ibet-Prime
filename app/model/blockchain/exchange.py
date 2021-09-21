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
from app.utils.contract_utils import ContractUtils


class IbetExchangeInterface:
    """IbetExchangeInterface model"""

    def __init__(self, contract_address: str):
        self.exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchangeInterface",
            contract_address=contract_address
        )

    def get_account_balance(self, account_address: str, token_address: str):
        """Get account balance

        :param account_address: account address
        :param token_address: token address
        :return: account balance
        """
        balance = self.exchange_contract.functions.balanceOf(
            account_address,
            token_address
        ).call()

        commitment = self.exchange_contract.functions.commitmentOf(
            account_address,
            token_address
        ).call()

        return {
            "balance": balance,
            "commitment": commitment
        }
