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
from typing import List
import json
from decimal import Decimal
from datetime import (
    datetime,
    timedelta
)

from web3.exceptions import TimeExhausted

from config import (
    TOKEN_CACHE,
    TOKEN_CACHE_TTL,
    CHAIN_ID,
    TX_GAS_LIMIT,
    ZERO_ADDRESS
)
from app.model.schema import (
    IbetStraightBondUpdate,
    IbetStraightBondTransfer,
    IbetStraightBondAdd,
    IbetShareUpdate,
    IbetShareTransfer,
    IbetShareAdd,
    IbetSecurityTokenApproveTransfer,
    IbetSecurityTokenCancelTransfer
)
from app.model.blockchain import IbetExchangeInterface
from app.exceptions import SendTransactionError
from app import log
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from app.utils.cache_utils import DictCache

LOG = log.get_logger()

web3 = Web3Wrapper()


class IbetStandardTokenInterface:
    issuer_address: str
    token_address: str
    name: str
    symbol: str
    total_supply: int
    contact_information: str
    privacy_policy: str
    tradable_exchange_contract_address: str
    status: bool

    @staticmethod
    def get_account_balance(contract_address: str, account_address: str):
        """Get account balance

        :param contract_address: contract address
        :param account_address: account address
        :return: account balance
        """
        token_contract = ContractUtils.get_contract(
            contract_name="IbetStandardTokenInterface",
            contract_address=contract_address
        )
        balance = ContractUtils.call_function(
            contract=token_contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0
        )
        tradable_exchange_address = ContractUtils.call_function(
            contract=token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS
        )
        if tradable_exchange_address != ZERO_ADDRESS:
            exchange_contract = IbetExchangeInterface(tradable_exchange_address)
            exchange_balance = exchange_contract.get_account_balance(
                account_address=account_address,
                token_address=contract_address
            )
            balance = balance + exchange_balance["balance"] + exchange_balance["commitment"]

        return balance


class IbetSecurityTokenInterface(IbetStandardTokenInterface):
    personal_info_contract_address: str
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool

    @staticmethod
    def approve_transfer(contract_address: str,
                         data: IbetSecurityTokenApproveTransfer,
                         tx_from: str,
                         private_key: str):
        """Approve Transfer"""
        try:
            security_contract = ContractUtils.get_contract(
                contract_name="IbetSecurityTokenInterface",
                contract_address=contract_address
            )
            tx = security_contract.functions.approveTransfer(
                data.application_id, data.data
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            tx_hash, tx_receipt = ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            return tx_hash, tx_receipt
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    @staticmethod
    def cancel_transfer(contract_address: str,
                        data: IbetSecurityTokenCancelTransfer,
                        tx_from: str,
                        private_key: str):
        """Cancel Transfer"""
        try:
            security_contract = ContractUtils.get_contract(
                contract_name="IbetSecurityTokenInterface",
                contract_address=contract_address
            )
            tx = security_contract.functions.cancelTransfer(
                data.application_id, data.data
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)


class IbetStraightBondContract(IbetSecurityTokenInterface):
    face_value: int
    interest_rate: float
    interest_payment_date: List[str]
    redemption_date: str
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    memo: str
    is_redeemed: bool

    # Cache
    cache = DictCache("bond_tokens")

    @staticmethod
    def create(args: list, tx_from: str, private_key: str):
        """Deploy token

        :param args: deploy arguments
        :param tx_from: contract deployer
        :param private_key: deployer's private key
        :return: contract address, ABI, transaction hash
        """
        contract_address, abi, tx_hash = ContractUtils.deploy_contract(
            contract_name="IbetStraightBond",
            args=args,
            deployer=tx_from,
            private_key=private_key
        )
        return contract_address, abi, tx_hash

    @staticmethod
    def get(contract_address: str):
        """Get token data

        :param contract_address: contract address
        :return: IbetStraightBond
        """
        bond_contract = ContractUtils.get_contract(
            contract_name="IbetStraightBond",
            contract_address=contract_address
        )

        # When using the cache
        if TOKEN_CACHE:
            if contract_address in IbetStraightBondContract.cache:
                token_cache = IbetStraightBondContract.cache[contract_address]
                is_updated = ContractUtils.is_token_attr_update(contract_address, token_cache.get("cached_datetime"))
                if is_updated is False and token_cache.get("expiration_datetime") > datetime.utcnow():
                    # Get data from cache
                    bond_token = IbetStraightBondContract()
                    for k, v in token_cache["token"].items():
                        setattr(bond_token, k, v)
                    return bond_token

        # When cache is not used
        # Or, if there is no data in the cache
        # Or, if the cache has expired

        # Get data from contract
        bond_token = IbetStraightBondContract()

        bond_token.issuer_address = ContractUtils.call_function(
            bond_contract, "owner", (), ZERO_ADDRESS
        )
        bond_token.token_address = contract_address

        # Set IbetStandardTokenInterface attribute
        bond_token.name = ContractUtils.call_function(
            bond_contract, "name", (), ""
        )
        bond_token.symbol = ContractUtils.call_function(
            bond_contract, "symbol", (), ""
        )
        bond_token.total_supply = ContractUtils.call_function(
            bond_contract, "totalSupply", (), 0
        )
        bond_token.tradable_exchange_contract_address = ContractUtils.call_function(
            bond_contract, "tradableExchange", (), ZERO_ADDRESS
        )
        bond_token.contact_information = ContractUtils.call_function(
            bond_contract, "contactInformation", (), ""
        )
        bond_token.privacy_policy = ContractUtils.call_function(
            bond_contract, "privacyPolicy", (), ""
        )
        bond_token.status = ContractUtils.call_function(
            bond_contract, "status", (), True
        )

        # Set IbetSecurityTokenInterface attribute
        bond_token.personal_info_contract_address = ContractUtils.call_function(
            bond_contract, "personalInfoAddress", (), ZERO_ADDRESS
        )
        bond_token.transferable = ContractUtils.call_function(
            bond_contract, "transferable", (), False
        )
        bond_token.is_offering = ContractUtils.call_function(
            bond_contract, "isOffering", (), False
        )
        bond_token.transfer_approval_required = ContractUtils.call_function(
            bond_contract, "transferApprovalRequired", (), False
        )

        # Set IbetStraightBondToken attribute
        bond_token.face_value = ContractUtils.call_function(
            bond_contract, "faceValue", (), 0
        )
        bond_token.interest_rate = float(
            Decimal(str(
                ContractUtils.call_function(bond_contract, "interestRate", (), 0)
            )) * Decimal("0.0001")
        )
        bond_token.redemption_date = ContractUtils.call_function(
            bond_contract, "redemptionDate", (), ""
        )
        bond_token.redemption_value = ContractUtils.call_function(
            bond_contract, "redemptionValue", (), 0
        )
        bond_token.return_date = ContractUtils.call_function(
            bond_contract, "returnDate", (), ""
        )
        bond_token.return_amount = ContractUtils.call_function(
            bond_contract, "returnAmount", (), ""
        )
        bond_token.purpose = ContractUtils.call_function(
            bond_contract, "purpose", (), ""
        )
        bond_token.memo = ContractUtils.call_function(
            bond_contract, "memo", (), ""
        )
        bond_token.is_redeemed = ContractUtils.call_function(
            bond_contract, "isRedeemed", (), False
        )

        interest_payment_date_list = []
        interest_payment_date_string = ContractUtils.call_function(
            bond_contract, "interestPaymentDate", (), ""
        ).replace("'", '"')
        interest_payment_date = {}
        try:
            if interest_payment_date_string != "":
                interest_payment_date = json.loads(interest_payment_date_string)
        except Exception as err:
            LOG.warning("Failed to load interestPaymentDate: ", err)
        for i in range(1, 13):
            interest_payment_date_list.append(
                interest_payment_date.get(f"interestPaymentDate{str(i)}", "")
            )
        bond_token.interest_payment_date = interest_payment_date_list

        if TOKEN_CACHE:
            IbetStraightBondContract.cache[contract_address] = {
                "cached_datetime": datetime.utcnow(),
                "expiration_datetime": datetime.utcnow() + timedelta(seconds=TOKEN_CACHE_TTL),
                "token": bond_token.__dict__
            }

        return bond_token

    @staticmethod
    def update(contract_address: str,
               data: IbetStraightBondUpdate,
               tx_from: str,
               private_key: str):
        """Update token"""
        bond_contract = ContractUtils.get_contract(
            contract_name="IbetStraightBond",
            contract_address=contract_address
        )

        if data.face_value is not None:
            tx = bond_contract.functions.setFaceValue(
                data.face_value
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.interest_rate is not None:
            _interest_rate = int(data.interest_rate * 10000)
            tx = bond_contract.functions.setInterestRate(
                _interest_rate
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.interest_payment_date is not None:
            _interest_payment_date = {}
            for i, item in enumerate(data.interest_payment_date):
                _interest_payment_date[f"interestPaymentDate{i + 1}"] = item
            _interest_payment_date_string = json.dumps(_interest_payment_date)
            tx = bond_contract.functions.setInterestPaymentDate(
                _interest_payment_date_string
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.redemption_value is not None:
            tx = bond_contract.functions.setRedemptionValue(
                data.redemption_value
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transferable is not None:
            tx = bond_contract.functions.setTransferable(
                data.transferable
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.status is not None:
            tx = bond_contract.functions.setStatus(
                data.status
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_offering is not None:
            tx = bond_contract.functions.changeOfferingStatus(
                data.is_offering
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_redeemed is not None and data.is_redeemed:
            tx = bond_contract.functions.changeToRedeemed().buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.tradable_exchange_contract_address is not None:
            tx = bond_contract.functions.setTradableExchange(
                data.tradable_exchange_contract_address
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.personal_info_contract_address is not None:
            tx = bond_contract.functions.setPersonalInfoAddress(
                data.personal_info_contract_address
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.contact_information is not None:
            tx = bond_contract.functions.setContactInformation(
                data.contact_information
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.privacy_policy is not None:
            tx = bond_contract.functions.setPrivacyPolicy(
                data.privacy_policy
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transfer_approval_required is not None:
            tx = bond_contract.functions.setTransferApprovalRequired(
                data.transfer_approval_required
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.memo is not None:
            tx = bond_contract.functions.setMemo(
                data.memo
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        # Delete Cache
        ContractUtils.set_token_attr_update(contract_address)
        IbetStraightBondContract.cache.pop(contract_address)

    @staticmethod
    def transfer(data: IbetStraightBondTransfer,
                 tx_from: str,
                 private_key: str):
        """Transfer ownership"""
        try:
            bond_contract = ContractUtils.get_contract(
                contract_name="IbetStraightBond",
                contract_address=data.token_address
            )
            _from = data.from_address
            _to = data.to_address
            _amount = data.amount
            tx = bond_contract.functions.transferFrom(
                _from, _to, _amount
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    @staticmethod
    def add_supply(contract_address: str,
                   data: IbetStraightBondAdd,
                   tx_from: str,
                   private_key: str):
        """Add token supply"""
        try:
            bond_contract = ContractUtils.get_contract(
                contract_name="IbetStraightBond",
                contract_address=contract_address
            )
            _target_address = data.account_address
            _amount = data.amount
            tx = bond_contract.functions.issueFrom(
                _target_address, ZERO_ADDRESS, _amount
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)

            # Delete Cache
            ContractUtils.set_token_attr_update(contract_address)
            IbetStraightBondContract.cache.pop(contract_address)
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)


class IbetShareContract(IbetSecurityTokenInterface):
    issue_price: int
    cancellation_date: str
    memo: str
    principal_value: int
    is_canceled: bool
    dividends: float
    dividend_record_date: str
    dividend_payment_date: str

    # Cache
    cache = DictCache("share_tokens")

    @staticmethod
    def create(args: list, tx_from: str, private_key: str):
        """Deploy token

        :param args: deploy arguments
        :param tx_from: contract deployer
        :param private_key: deployer's private key
        :return: contract address, ABI, transaction hash
        """
        contract_address, abi, tx_hash = ContractUtils.deploy_contract(
            contract_name="IbetShare",
            args=args,
            deployer=tx_from,
            private_key=private_key
        )
        return contract_address, abi, tx_hash

    @staticmethod
    def get(contract_address: str):
        """Get token data

        :param contract_address: contract address
        :return: IbetShare
        """
        share_contract = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=contract_address
        )

        # When using the cache
        if TOKEN_CACHE:
            if contract_address in IbetShareContract.cache:
                token_cache = IbetShareContract.cache[contract_address]
                is_updated = ContractUtils.is_token_attr_update(contract_address, token_cache.get("cached_datetime"))
                if is_updated is False and token_cache.get("expiration_datetime") > datetime.utcnow():
                    # Get data from cache
                    share_token = IbetShareContract()
                    for k, v in token_cache["token"].items():
                        setattr(share_token, k, v)
                    return share_token

        # When cache is not used
        # Or, if there is no data in the cache
        # Or, if the cache has expired

        # Get data from contract
        share_token = IbetShareContract()

        share_token.issuer_address = ContractUtils.call_function(
            share_contract, "owner", (), ZERO_ADDRESS
        )
        share_token.token_address = contract_address

        # Set IbetStandardTokenInterface attribute
        share_token.name = ContractUtils.call_function(
            share_contract, "name", (), ""
        )
        share_token.symbol = ContractUtils.call_function(
            share_contract, "symbol", (), ""
        )
        share_token.total_supply = ContractUtils.call_function(
            share_contract, "totalSupply", (), 0
        )
        share_token.tradable_exchange_contract_address = ContractUtils.call_function(
            share_contract, "tradableExchange", (), ZERO_ADDRESS
        )
        share_token.contact_information = ContractUtils.call_function(
            share_contract, "contactInformation", (), ""
        )
        share_token.privacy_policy = ContractUtils.call_function(
            share_contract, "privacyPolicy", (), ""
        )
        share_token.status = ContractUtils.call_function(
            share_contract, "status", (), True
        )

        # Set IbetSecurityTokenInterface attribute
        share_token.personal_info_contract_address = ContractUtils.call_function(
            share_contract, "personalInfoAddress", (), ZERO_ADDRESS
        )
        share_token.transferable = ContractUtils.call_function(
            share_contract, "transferable", (), False
        )
        share_token.is_offering = ContractUtils.call_function(
            share_contract, "isOffering", (), False
        )
        share_token.transfer_approval_required = ContractUtils.call_function(
            share_contract, "transferApprovalRequired", (), False
        )

        # Set IbetShareToken attribute
        share_token.issue_price = ContractUtils.call_function(
            share_contract, "issuePrice", (), 0
        )
        share_token.cancellation_date = ContractUtils.call_function(
            share_contract, "cancellationDate", (), ""
        )
        share_token.memo = ContractUtils.call_function(
            share_contract, "memo", (), ""
        )
        share_token.principal_value = ContractUtils.call_function(
            share_contract, "principalValue", (), 0
        )
        share_token.is_canceled = ContractUtils.call_function(
            share_contract, "isCanceled", (), False
        )
        _dividend_info = ContractUtils.call_function(
            share_contract, "dividendInformation", (), (0, "", "")
        )
        share_token.dividends = float(Decimal(str(_dividend_info[0])) * Decimal("0.01"))
        share_token.dividend_record_date = _dividend_info[1]
        share_token.dividend_payment_date = _dividend_info[2]

        if TOKEN_CACHE:
            IbetShareContract.cache[contract_address] = {
                "cached_datetime": datetime.utcnow(),
                "expiration_datetime": datetime.utcnow() + timedelta(seconds=TOKEN_CACHE_TTL),
                "token": share_token.__dict__
            }

        return share_token

    @staticmethod
    def update(contract_address: str,
               data: IbetShareUpdate,
               tx_from: str,
               private_key: str):
        """Update token"""
        share_contract = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=contract_address
        )

        if data.tradable_exchange_contract_address is not None:
            tx = share_contract.functions.setTradableExchange(
                data.tradable_exchange_contract_address
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.personal_info_contract_address is not None:
            tx = share_contract.functions.setPersonalInfoAddress(
                data.personal_info_contract_address
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.dividends is not None:
            _dividends = int(data.dividends * 100)
            tx = share_contract.functions.setDividendInformation(
                _dividends,
                data.dividend_record_date,
                data.dividend_payment_date
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.cancellation_date is not None:
            tx = share_contract.functions.setCancellationDate(
                data.cancellation_date
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.contact_information is not None:
            tx = share_contract.functions.setContactInformation(
                data.contact_information
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.privacy_policy is not None:
            tx = share_contract.functions.setPrivacyPolicy(
                data.privacy_policy
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.status is not None:
            tx = share_contract.functions.setStatus(
                data.status
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transferable is not None:
            tx = share_contract.functions.setTransferable(
                data.transferable
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_offering is not None:
            tx = share_contract.functions.changeOfferingStatus(
                data.is_offering
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transfer_approval_required is not None:
            tx = share_contract.functions.setTransferApprovalRequired(
                data.transfer_approval_required
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.principal_value is not None:
            tx = share_contract.functions.setPrincipalValue(
                data.principal_value
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_canceled is not None and data.is_canceled:
            tx = share_contract.functions.changeToCanceled().buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.memo is not None:
            tx = share_contract.functions.setMemo(
                data.memo
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        # Delete Cache
        ContractUtils.set_token_attr_update(contract_address)
        IbetShareContract.cache.pop(contract_address)

    @staticmethod
    def transfer(data: IbetShareTransfer,
                 tx_from: str,
                 private_key: str):
        """Transfer ownership"""
        try:
            share_contract = ContractUtils.get_contract(
                contract_name="IbetShare",
                contract_address=data.token_address
            )
            _from = data.from_address
            _to = data.to_address
            _amount = data.amount
            tx = share_contract.functions.transferFrom(
                _from, _to, _amount
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    @staticmethod
    def add_supply(contract_address: str,
                   data: IbetShareAdd,
                   tx_from: str,
                   private_key: str):
        """Add token supply"""
        try:
            share_contract = ContractUtils.get_contract(
                contract_name="IbetShare",
                contract_address=contract_address
            )
            _target_address = data.account_address
            _amount = data.amount
            tx = share_contract.functions.issueFrom(
                _target_address, ZERO_ADDRESS, _amount
            ).buildTransaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)

            # Delete Cache
            ContractUtils.set_token_attr_update(contract_address)
            IbetShareContract.cache.pop(contract_address)
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)
