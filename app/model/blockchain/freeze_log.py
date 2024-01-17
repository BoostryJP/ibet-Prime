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
import logging
import os
import sys

from eth_keyfile import decode_keyfile_json
from web3.exceptions import TimeExhausted

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import FreezeLogAccount
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import Web3Wrapper
from config import CHAIN_ID, TX_GAS_LIMIT

web3 = Web3Wrapper()


class FreezeLogContract:
    """FreezeLog contract"""

    def __init__(self, log_account: FreezeLogAccount, contract_address: str):
        self.log_contract = ContractUtils.get_contract(
            contract_name="FreezeLog", contract_address=contract_address
        )
        self.log_account = log_account

    def record_log(self, log_message: str, freezing_grace_block_count: int):
        """Record new log

        :param log_message: Log text
        :param freezing_grace_block_count: Freezing grace block count
        :return: tx_hash, log_index
        """

        try:
            password = E2EEUtils.decrypt(self.log_account.eoa_password)
            private_key = decode_keyfile_json(
                raw_keyfile_json=self.log_account.keyfile,
                password=password.encode("utf-8"),
            )
            tx = self.log_contract.functions.recordLog(
                log_message, freezing_grace_block_count
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": self.log_account.account_address,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            last_log_index = ContractUtils.call_function(
                contract=self.log_contract,
                function_name="lastLogIndex",
                args=(self.log_account.account_address,),
                default_returns=1,
            )
            log_index = last_log_index - 1
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            logging.exception(f"{err}")
            raise SendTransactionError(err)

        return tx_hash, log_index

    def update_log(self, log_index: int, log_message: str):
        """Update recorded log

        :param log_index: Log index
        :param log_message: Log text
        :return: tx_hash
        """

        try:
            password = E2EEUtils.decrypt(self.log_account.eoa_password)
            private_key = decode_keyfile_json(
                raw_keyfile_json=self.log_account.keyfile,
                password=password.encode("utf-8"),
            )
            tx = self.log_contract.functions.updateLog(
                log_index, log_message
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": self.log_account.account_address,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            logging.exception(f"{err}")
            raise SendTransactionError(err)

        return tx_hash

    def get_log(self, log_index: int):
        """Get recorded log

        :param log_index: Log index
        :return: block_number, freezing_grace_block_count, log_message
        """

        log = ContractUtils.call_function(
            contract=self.log_contract,
            function_name="getLog",
            args=(
                self.log_account.account_address,
                log_index,
            ),
        )
        return log[0], log[1], log[2]
