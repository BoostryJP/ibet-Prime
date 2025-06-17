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
from app.model.ibet.tx_params.ibet_security_token_dvp import (
    AbortDeliveryParams,
    CancelDeliveryParams,
    CreateDeliveryParams,
    FinishDeliveryParams,
    WithdrawPartialParams,
)
from app.model.ibet.tx_params.ibet_security_token_escrow import (
    ApproveTransferParams,
)
from app.utils.ibet_contract_utils import AsyncContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT


class IbetExchangeInterface:
    """IbetExchangeInterface model"""

    def __init__(
        self, contract_address: str, contract_name: str = "IbetExchangeInterface"
    ):
        self.exchange_contract = AsyncContractUtils.get_contract(
            contract_name=contract_name, contract_address=contract_address
        )

    async def get_account_balance(self, account_address: str, token_address: str):
        """Get account balance

        :param account_address: account address
        :param token_address: token address
        :return: account balance
        """
        balance = await AsyncContractUtils.call_function(
            contract=self.exchange_contract,
            function_name="balanceOf",
            args=(
                account_address,
                token_address,
            ),
            default_returns=0,
        )
        commitment = await AsyncContractUtils.call_function(
            contract=self.exchange_contract,
            function_name="commitmentOf",
            args=(
                account_address,
                token_address,
            ),
            default_returns=0,
        )

        return {"balance": balance, "commitment": commitment}


class IbetSecurityTokenEscrow(IbetExchangeInterface):
    """IbetSecurityTokenEscrow contract"""

    def __init__(self, contract_address: str):
        super().__init__(
            contract_address=contract_address, contract_name="IbetSecurityTokenEscrow"
        )

    async def approve_transfer(
        self, data: ApproveTransferParams, tx_from: str, private_key: bytes
    ):
        """Approve Transfer"""
        try:
            tx = await self.exchange_contract.functions.approveTransfer(
                data.escrow_id, data.data
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)


class IbetSecurityTokenDVP(IbetExchangeInterface):
    """IbetSecurityTokenDVP contract"""

    def __init__(self, contract_address: str):
        super().__init__(
            contract_address=contract_address, contract_name="IbetSecurityTokenDVP"
        )

    async def create_delivery(
        self, data: CreateDeliveryParams, tx_from: str, private_key: bytes
    ):
        """Create Delivery"""
        try:
            tx = await self.exchange_contract.functions.createDelivery(
                data.token_address,
                data.buyer_address,
                data.amount,
                data.agent_address,
                data.data,
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            latest_delivery_id = await AsyncContractUtils.call_function(
                contract=self.exchange_contract,
                function_name="latestDeliveryId",
                args=(),
                default_returns=None,
            )
            return tx_hash, tx_receipt, latest_delivery_id
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def cancel_delivery(
        self, data: CancelDeliveryParams, tx_from: str, private_key: bytes
    ):
        """Cancel Delivery"""
        try:
            tx = await self.exchange_contract.functions.cancelDelivery(
                data.delivery_id
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def finish_delivery(
        self, data: FinishDeliveryParams, tx_from: str, private_key: bytes
    ):
        """Finish Delivery"""
        try:
            tx = await self.exchange_contract.functions.finishDelivery(
                data.delivery_id
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def abort_delivery(
        self, data: AbortDeliveryParams, tx_from: str, private_key: bytes
    ):
        """Abort Delivery"""
        try:
            tx = await self.exchange_contract.functions.abortDelivery(
                data.delivery_id
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def withdraw_partial(
        self, data: WithdrawPartialParams, tx_from: str, private_key: bytes
    ):
        """Withdraw Partial"""
        try:
            tx = await self.exchange_contract.functions.withdrawPartial(
                data.token_address, data.value
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)


class IbetSecurityTokenDVPNoWait(IbetExchangeInterface):
    """IbetSecurityTokenDVP contract (No wait transaction)"""

    def __init__(self, contract_address: str):
        super().__init__(
            contract_address=contract_address, contract_name="IbetSecurityTokenDVP"
        )

    async def create_delivery(
        self, data: CreateDeliveryParams, tx_from: str, private_key: bytes
    ):
        """Create Delivery (No wait)"""
        try:
            tx = await self.exchange_contract.functions.createDelivery(
                data.token_address,
                data.buyer_address,
                data.amount,
                data.agent_address,
                data.data,
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash = await AsyncContractUtils.send_transaction_no_wait(
                transaction=tx, private_key=private_key
            )
            return tx_hash
        except Exception as err:
            raise SendTransactionError(err)

    async def withdraw_partial(
        self, data: WithdrawPartialParams, tx_from: str, private_key: bytes
    ):
        """Withdraw Partial (No wait)"""
        try:
            tx = await self.exchange_contract.functions.withdrawPartial(
                data.token_address, data.value
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash = await AsyncContractUtils.send_transaction_no_wait(
                transaction=tx, private_key=private_key
            )
            return tx_hash
        except Exception as err:
            raise SendTransactionError(err)
