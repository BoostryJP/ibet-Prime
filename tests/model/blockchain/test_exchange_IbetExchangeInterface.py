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
import pytest
from eth_keyfile import decode_keyfile_json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import BadFunctionCallOutput as Web3BadFunctionCallOutput

from app.model.blockchain import (
    IbetStraightBondContract,
    IbetExchangeInterface
)
from app.utils.contract_utils import ContractUtils
from config import (
    CHAIN_ID,
    TX_GAS_LIMIT,
    WEB3_HTTP_PROVIDER,
    ZERO_ADDRESS
)

from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def deploy_escrow_contract():
    deployer = config_eth_account("user1")
    private_key = decode_keyfile_json(
        raw_keyfile_json=deployer["keyfile_json"],
        password=deployer["password"].encode("utf-8")
    )

    # deploy
    escrow_storage_address, _, _ = ContractUtils.deploy_contract(
        contract_name="EscrowStorage",
        args=[],
        deployer=deployer["address"],
        private_key=private_key
    )

    escrow_contract_address, _, _ = ContractUtils.deploy_contract(
        contract_name="IbetEscrow",
        args=[escrow_storage_address],
        deployer=deployer["address"],
        private_key=private_key
    )
    escrow_contract = ContractUtils.get_contract(
        contract_name="IbetEscrow",
        contract_address=escrow_contract_address
    )

    # update storage
    storage_contract = ContractUtils.get_contract(
        contract_name="EscrowStorage",
        contract_address=escrow_storage_address
    )
    tx = storage_contract.functions.upgradeVersion(
        escrow_contract_address
    ).buildTransaction({
        "chainId": CHAIN_ID,
        "from": deployer["address"],
        "gas": TX_GAS_LIMIT,
        "gasPrice": 0
    })
    ContractUtils.send_transaction(
        transaction=tx,
        private_key=private_key
    )

    return escrow_contract


def issue_bond_token(issuer: dict, exchange_address: str):
    issuer_address = issuer["address"]
    issuer_pk = decode_keyfile_json(
        raw_keyfile_json=issuer.get("keyfile_json"),
        password=issuer.get("password").encode("utf-8")
    )

    # deploy token
    arguments = [
        "テスト債券",
        "TEST",
        2 ** 256 - 1,
        10000,
        "20211231",
        10000,
        "20211231",
        "リターン内容",
        "発行目的"
    ]
    token_contract_address, abi, tx_hash = IbetStraightBondContract.create(
        args=arguments,
        tx_from=issuer_address,
        private_key=issuer_pk
    )
    token_contract = ContractUtils.get_contract(
        contract_name="IbetStraightBond",
        contract_address=token_contract_address
    )
    tx = token_contract.functions.setTransferable(
        True
    ).buildTransaction({
        "chainId": CHAIN_ID,
        "from": issuer_address,
        "gas": TX_GAS_LIMIT,
        "gasPrice": 0
    })
    ContractUtils.send_transaction(
        transaction=tx,
        private_key=issuer_pk
    )

    # set tradable exchange address
    tx = token_contract.functions.setTradableExchange(
        exchange_address
    ).buildTransaction({
        "chainId": CHAIN_ID,
        "from": issuer_address,
        "gas": TX_GAS_LIMIT,
        "gasPrice": 0
    })
    ContractUtils.send_transaction(
        transaction=tx,
        private_key=issuer_pk
    )

    return token_contract


class TestGetAccountBalance:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # balance = 0, commitment = 0
    # Default value
    def test_normal_1(self, db):
        user1_account = config_eth_account("user1")

        # deploy contract
        exchange_contract = deploy_escrow_contract()
        token_contract = issue_bond_token(
            issuer=user1_account,
            exchange_address=exchange_contract.address
        )

        # test IbetExchangeInterface.get_account_balance
        exchange_interface = IbetExchangeInterface(exchange_contract.address)
        exchange_balance = exchange_interface.get_account_balance(
            account_address=user1_account["address"],
            token_address=token_contract.address
        )

        # assertion
        assert exchange_balance["balance"] == 0
        assert exchange_balance["commitment"] == 0

    # <Normal_2>
    def test_normal_2(self, db):
        user1_account = config_eth_account("user1")
        user1_account_pk = decode_keyfile_json(
            raw_keyfile_json=user1_account["keyfile_json"],
            password=user1_account["password"].encode("utf-8")
        )
        user2_account = config_eth_account("user2")

        # deploy contract
        exchange_contract = deploy_escrow_contract()
        token_contract = issue_bond_token(
            issuer=user1_account,
            exchange_address=exchange_contract.address
        )

        # transfer -> create balance
        tx = token_contract.functions.transfer(
            exchange_contract.address,
            100
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user1_account["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(
            transaction=tx,
            private_key=user1_account_pk
        )

        # create commitment
        tx = exchange_contract.functions.createEscrow(
            token_contract.address,
            user2_account["address"],
            30,
            user1_account["address"],
            "test_data"
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user1_account["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(
            transaction=tx,
            private_key=user1_account_pk
        )

        # test IbetExchangeInterface.get_account_balance
        exchange_interface = IbetExchangeInterface(exchange_contract.address)
        exchange_balance = exchange_interface.get_account_balance(
            account_address=user1_account["address"],
            token_address=token_contract.address
        )

        # assertion
        assert exchange_balance["balance"] == 70
        assert exchange_balance["commitment"] == 30

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Web3BadFunctionCallOutput
    # Not deployed contract
    def test_error_1(self, db):
        user1_account = config_eth_account("user1")

        # test IbetExchangeInterface.get_account_balance
        with pytest.raises(Web3BadFunctionCallOutput):
            exchange_interface = IbetExchangeInterface(ZERO_ADDRESS)
            exchange_interface.get_account_balance(
                account_address=user1_account["address"],
                token_address=ZERO_ADDRESS
            )
