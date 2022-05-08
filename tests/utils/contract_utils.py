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


class IbetSecurityTokenContractTestUtils:

    @staticmethod
    def balance_of(contract_address: str, account_address: str):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        return security_token_contract.functions.balanceOf(account_address).call()

    @staticmethod
    def transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            transfer(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def bulk_transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            bulkTransfer(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def authorize_lock_address(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            authorizeLockAddress(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def lock(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            lock(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def unlock(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            unlock(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def issue_from(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            issueFrom(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def redeem_from(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            redeemFrom(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def set_transfer_approve_required(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            setTransferApprovalRequired(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def apply_for_transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            applyForTransfer(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def cancel_transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            cancelTransfer(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def approve_transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address
        )
        tx = security_token_contract.functions.\
            approveTransfer(*args).\
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)


class IbetExchangeContractTestUtils:

    @staticmethod
    def balance_of(contract_address: str, account_address: str, token_address: str):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        return exchange_contract.functions.balanceOf(account_address, token_address).call()

    @staticmethod
    def create_order(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        tx = exchange_contract.functions.\
            createOrder(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def get_latest_order_id(contract_address: str):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        return exchange_contract.functions.latestOrderId().call()

    @staticmethod
    def force_cancel_order(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        tx = exchange_contract.functions. \
            forceCancelOrder(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def cancel_order(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        tx = exchange_contract.functions. \
            cancelOrder(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def execute_order(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        tx = exchange_contract.functions. \
            executeOrder(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def get_latest_agreementid(contract_address: str, order_id: int):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        return exchange_contract.functions.latestAgreementId(order_id).call()

    @staticmethod
    def cancel_agreement(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        tx = exchange_contract.functions. \
            cancelAgreement(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def confirm_agreement(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=contract_address
        )
        tx = exchange_contract.functions. \
            confirmAgreement(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)


class IbetSecurityTokenEscrowContractTestUtils:

    @staticmethod
    def balance_of(contract_address: str, account_address: str, token_address: str):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow",
            contract_address=contract_address
        )
        return escrow_contract.functions.balanceOf(account_address, token_address).call()

    @staticmethod
    def create_escrow(contract_address: str, tx_from: str, private_key: str, args: list):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow",
            contract_address=contract_address
        )
        tx = escrow_contract.functions.\
            createEscrow(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def cancel_escrow(contract_address: str, tx_from: str, private_key: str, args: list):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow",
            contract_address=contract_address
        )
        tx = escrow_contract.functions.\
            cancelEscrow(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def approve_transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow",
            contract_address=contract_address
        )
        tx = escrow_contract.functions.\
            approveTransfer(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def finish_escrow(contract_address: str, tx_from: str, private_key: str, args: list):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow",
            contract_address=contract_address
        )
        tx = escrow_contract.functions.\
            finishEscrow(*args). \
            buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def get_latest_escrow_id(contract_address: str):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow",
            contract_address=contract_address
        )
        return escrow_contract.functions.latestEscrowId().call()
