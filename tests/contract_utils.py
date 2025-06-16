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

from typing import Dict

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.utils.contract_utils import ContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

"""
Helper Methods for Contract Testing

Helper methods to make it easier for test code to handle operations 
on contracts that are not executed by the issuer.
"""


class PersonalInfoContractTestUtils:
    @staticmethod
    def register(contract_address: str, tx_from: str, private_key: str, args: list):
        personal_info_contract = ContractUtils.get_contract(
            contract_name="PersonalInfo", contract_address=contract_address
        )
        tx = personal_info_contract.functions.register(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)


class IbetStandardTokenUtils:
    @staticmethod
    def issue(tx_from: str, private_key: str, args: Dict):
        """issue token

        :param tx_from: transaction sender
        :param private_key: private key
        :param args: deploy args
        :return: Contract
        """
        web3.eth.default_account = tx_from
        arguments = [
            args["name"],
            args["symbol"],
            args["totalSupply"],
            args["tradableExchange"],
            args["contactInformation"],
            args["privacyPolicy"],
        ]
        contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="IbetStandardToken",
            args=arguments,
            deployer=tx_from,
            private_key=private_key,
        )
        contract = ContractUtils.get_contract(
            contract_name="IbetStandardToken", contract_address=contract_address
        )
        return contract

    @staticmethod
    def transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        token_contract = ContractUtils.get_contract(
            contract_name="IbetStandardTokenInterface",
            contract_address=contract_address,
        )
        tx = token_contract.functions.transfer(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        tx_hash, _ = ContractUtils.send_transaction(
            transaction=tx, private_key=private_key
        )

        return tx_hash


class IbetSecurityTokenContractTestUtils:
    @staticmethod
    def balance_of(contract_address: str, account_address: str):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        return security_token_contract.functions.balanceOf(account_address).call()

    @staticmethod
    def transfer(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.transfer(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def bulk_transfer(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.bulkTransfer(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def lock(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.lock(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def force_lock(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.forceLock(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def unlock(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.unlock(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def force_unlock(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.forceUnlock(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def force_change_locked_account(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.forceChangeLockedAccount(
            *args
        ).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def issue_from(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.issueFrom(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def redeem_from(contract_address: str, tx_from: str, private_key: str, args: list):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.redeemFrom(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def set_transfer_approve_required(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.setTransferApprovalRequired(
            *args
        ).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def apply_for_transfer(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.applyForTransfer(
            *args
        ).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def cancel_transfer(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.cancelTransfer(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def approve_transfer(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        security_token_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenInterface",
            contract_address=contract_address,
        )
        tx = security_token_contract.functions.approveTransfer(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)


class IbetExchangeContractTestUtils:
    @staticmethod
    def balance_of(contract_address: str, account_address: str, token_address: str):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        return exchange_contract.functions.balanceOf(
            account_address, token_address
        ).call()

    @staticmethod
    def create_order(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        tx = exchange_contract.functions.createOrder(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def get_latest_order_id(contract_address: str):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        return exchange_contract.functions.latestOrderId().call()

    @staticmethod
    def force_cancel_order(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        tx = exchange_contract.functions.forceCancelOrder(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def cancel_order(contract_address: str, tx_from: str, private_key: str, args: list):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        tx = exchange_contract.functions.cancelOrder(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def execute_order(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        tx = exchange_contract.functions.executeOrder(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def get_latest_agreementid(contract_address: str, order_id: int):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        return exchange_contract.functions.latestAgreementId(order_id).call()

    @staticmethod
    def cancel_agreement(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        tx = exchange_contract.functions.cancelAgreement(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def confirm_agreement(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange", contract_address=contract_address
        )
        tx = exchange_contract.functions.confirmAgreement(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)


class IbetSecurityTokenEscrowContractTestUtils:
    @staticmethod
    def balance_of(contract_address: str, account_address: str, token_address: str):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow", contract_address=contract_address
        )
        return escrow_contract.functions.balanceOf(
            account_address, token_address
        ).call()

    @staticmethod
    def create_escrow(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow", contract_address=contract_address
        )
        tx = escrow_contract.functions.createEscrow(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def cancel_escrow(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow", contract_address=contract_address
        )
        tx = escrow_contract.functions.cancelEscrow(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def approve_transfer(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow", contract_address=contract_address
        )
        tx = escrow_contract.functions.approveTransfer(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def finish_escrow(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow", contract_address=contract_address
        )
        tx = escrow_contract.functions.finishEscrow(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def get_latest_escrow_id(contract_address: str):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenEscrow", contract_address=contract_address
        )
        return escrow_contract.functions.latestEscrowId().call()


class IbetSecurityTokenDVPContractTestUtils:
    @staticmethod
    def balance_of(contract_address: str, account_address: str, token_address: str):
        dvp_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenDVP", contract_address=contract_address
        )
        return dvp_contract.functions.balanceOf(account_address, token_address).call()

    @staticmethod
    def create_delivery(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        dvp_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenDVP", contract_address=contract_address
        )
        tx = dvp_contract.functions.createDelivery(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def cancel_delivery(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        dvp_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenDVP", contract_address=contract_address
        )
        tx = dvp_contract.functions.cancelDelivery(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def confirm_delivery(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        dvp_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenDVP", contract_address=contract_address
        )
        tx = dvp_contract.functions.confirmDelivery(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def finish_delivery(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        dvp_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenDVP", contract_address=contract_address
        )
        tx = dvp_contract.functions.finishDelivery(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def abort_delivery(
        contract_address: str, tx_from: str, private_key: str, args: list
    ):
        dvp_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenDVP", contract_address=contract_address
        )
        tx = dvp_contract.functions.abortDelivery(*args).build_transaction(
            {"chainId": CHAIN_ID, "from": tx_from, "gas": TX_GAS_LIMIT, "gasPrice": 0}
        )
        ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    @staticmethod
    def get_latest_delivery_id(contract_address: str):
        escrow_contract = ContractUtils.get_contract(
            contract_name="IbetSecurityTokenDVP", contract_address=contract_address
        )
        return escrow_contract.functions.latestDeliveryId().call()
