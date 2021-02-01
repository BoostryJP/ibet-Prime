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
from typing import Dict, List
import json
from decimal import Decimal
from datetime import datetime, timedelta

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted

from config import TOKEN_CACHE, TOKEN_CACHE_TTL, \
    WEB3_HTTP_PROVIDER, CHAIN_ID, TX_GAS_LIMIT
from app.model.schema import IbetStraightBondUpdate, IbetStraightBondTransfer
from app.exceptions import SendTransactionError
from app import log
from .utils import ContractUtils

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class IbetStandardTokenInterfaceContract:
    issuer_address: str
    token_address: str
    name: str
    symbol: str
    total_supply: int
    image_url: List[Dict[str, str]]
    contact_information: str
    privacy_policy: str
    tradable_exchange_contract_address: str
    status: bool


class IbetStraightBondContract(IbetStandardTokenInterfaceContract):
    face_value: int
    redemption_date: str
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    interest_rate: float
    interest_payment_date: List[str]
    transferable: bool
    initial_offering_status: bool
    is_redeemed: bool
    personal_info_contract_address: str

    # Cache
    cache = {}

    @staticmethod
    def create(args: list, tx_from: str, private_key: str):
        """Deploy bond contract

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
        """Get bond contract data

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
                if token_cache.get("expiration_datetime") > datetime.utcnow():
                    # get data from cache
                    bond_token = token_cache["token"]
                    bond_token.face_value = bond_contract.functions.faceValue().call()
                    bond_token.interest_rate = float(
                        Decimal(str(bond_contract.functions.interestRate().call())) * Decimal("0.0001")
                    )
                    interest_payment_date_list = []
                    interest_payment_date_string = bond_contract.functions.interestPaymentDate().call().replace("'",
                                                                                                                '"')
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
                    bond_token.redemption_value = bond_contract.functions.redemptionValue().call()
                    bond_token.transferable = bond_contract.functions.transferable().call()
                    bond_token.image_url = [
                        bond_contract.functions.getImageURL(0).call(),
                        bond_contract.functions.getImageURL(1).call(),
                        bond_contract.functions.getImageURL(2).call()
                    ]
                    bond_token.status = bond_contract.functions.status().call()
                    bond_token.initial_offering_status = bond_contract.functions.initialOfferingStatus().call()
                    bond_token.is_redeemed = bond_contract.functions.isRedeemed().call()
                    bond_token.tradable_exchange_contract_address = bond_contract.functions.tradableExchange().call()
                    bond_token.personal_info_contract_address = bond_contract.functions.personalInfoAddress().call()
                    bond_token.contact_information = bond_contract.functions.contactInformation().call()
                    bond_token.privacy_policy = bond_contract.functions.privacyPolicy().call()
                    return bond_token

        # When cache is not used
        # Or, if there is no data in the cache
        # Or, if the cache has expired

        # get data from contract
        bond_token = IbetStraightBondContract()

        bond_token.issuer_address = bond_contract.functions.owner().call()
        bond_token.token_address = contract_address
        bond_token.name = bond_contract.functions.name().call()
        bond_token.symbol = bond_contract.functions.symbol().call()
        bond_token.total_supply = bond_contract.functions.totalSupply().call()
        bond_token.image_url = [
            bond_contract.functions.getImageURL(0).call(),
            bond_contract.functions.getImageURL(1).call(),
            bond_contract.functions.getImageURL(2).call()
        ]
        bond_token.contact_information = bond_contract.functions.contactInformation().call()
        bond_token.privacy_policy = bond_contract.functions.privacyPolicy().call()
        bond_token.tradable_exchange_contract_address = bond_contract.functions.tradableExchange().call()
        bond_token.status = bond_contract.functions.status().call()
        bond_token.face_value = bond_contract.functions.faceValue().call()
        bond_token.redemption_date = bond_contract.functions.redemptionDate().call()
        bond_token.redemption_value = bond_contract.functions.redemptionValue().call()
        bond_token.return_date = bond_contract.functions.returnDate().call()
        bond_token.return_amount = bond_contract.functions.returnAmount().call()
        bond_token.purpose = bond_contract.functions.purpose().call()
        bond_token.interest_rate = float(
            Decimal(str(bond_contract.functions.interestRate().call())) * Decimal("0.0001")
        )
        bond_token.transferable = bond_contract.functions.transferable().call()
        bond_token.initial_offering_status = bond_contract.functions.initialOfferingStatus().call()
        bond_token.is_redeemed = bond_contract.functions.isRedeemed().call()
        bond_token.personal_info_contract_address = bond_contract.functions.personalInfoAddress().call()

        interest_payment_date_list = []
        interest_payment_date_string = bond_contract.functions.interestPaymentDate().call().replace("'", '"')
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
                "expiration_datetime": datetime.utcnow() + timedelta(seconds=TOKEN_CACHE_TTL),
                "token": bond_token
            }

        return bond_token

    @staticmethod
    def update(contract_address: str,
               update_data: IbetStraightBondUpdate,
               tx_from: str,
               private_key: str):
        bond_contract = ContractUtils.get_contract(
            contract_name="IbetStraightBond",
            contract_address=contract_address
        )

        if update_data.face_value:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions.\
                setFaceValue(update_data.face_value).\
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.interest_rate:
            _interest_rate = int(update_data.interest_rate * 10000)
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions.\
                setInterestRate(_interest_rate).\
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.interest_payment_date:
            _interest_payment_date = {}
            for i, item in enumerate(update_data.interest_payment_date):
                _interest_payment_date[f"interestPaymentDate{i + 1}"] = item
            _interest_payment_date_string = json.dumps(_interest_payment_date)
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions.\
                setInterestPaymentDate(_interest_payment_date_string).\
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.redemption_value:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions.\
                setRedemptionValue(update_data.redemption_value).\
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.transferable:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions.\
                setTransferable(update_data.transferable).\
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.image_url:
            for i, _image_url in enumerate(update_data.image_url):
                nonce = web3.eth.getTransactionCount(tx_from)
                tx = bond_contract.functions.\
                    setImageURL(i, _image_url).\
                    buildTransaction({
                        "nonce": nonce,
                        "chainId": CHAIN_ID,
                        "from": tx_from,
                        "gas": TX_GAS_LIMIT,
                        "gasPrice": 0
                    })
                try:
                    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
                except TimeExhausted as timeout_error:
                    raise SendTransactionError(timeout_error)

        if update_data.status:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions. \
                setStatus(update_data.status). \
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.initial_offering_status:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions. \
                setInitialOfferingStatus(update_data.initial_offering_status). \
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.is_redeemed:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions.redeem().buildTransaction({
                "nonce": nonce,
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.tradable_exchange_contract_address:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions. \
                setTradableExchange(update_data.tradable_exchange_contract_address). \
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.personal_info_contract_address:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions. \
                setPersonalInfoAddress(update_data.personal_info_contract_address). \
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.contact_information:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions. \
                setContactInformation(update_data.contact_information). \
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

        if update_data.privacy_policy:
            nonce = web3.eth.getTransactionCount(tx_from)
            tx = bond_contract.functions. \
                setPrivacyPolicy(update_data.privacy_policy). \
                buildTransaction({
                    "nonce": nonce,
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)

    @staticmethod
    def transfer(contract_address: str,
                 transfer_data: IbetStraightBondTransfer,
                 tx_from: str,
                 private_key: str):
        bond_contract = ContractUtils.get_contract(
            contract_name="IbetStraightBond",
            contract_address=contract_address
        )

        _from = transfer_data.transfer_from
        _to = transfer_data.transfer_to
        _amount = transfer_data.amount
        nonce = web3.eth.getTransactionCount(tx_from)
        tx = bond_contract.functions. \
            transferFrom(_from, _to, _amount). \
            buildTransaction({
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "from": tx_from,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        try:
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
