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
from web3.middleware import ExtraDataToPOAMiddleware

from app.model.ibet import IbetExchangeInterface, IbetStraightBondContract
from app.utils.ibet_contract_utils import ContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER, ZERO_ADDRESS
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


def deploy_escrow_contract():
    deployer = default_eth_account("user1")
    private_key = decode_keyfile_json(
        raw_keyfile_json=deployer["keyfile_json"],
        password=deployer["password"].encode("utf-8"),
    )

    # deploy
    escrow_storage_address, _, _ = ContractUtils.deploy_contract(
        contract_name="EscrowStorage",
        args=[],
        deployer=deployer["address"],
        private_key=private_key,
    )

    escrow_contract_address, _, _ = ContractUtils.deploy_contract(
        contract_name="IbetEscrow",
        args=[escrow_storage_address],
        deployer=deployer["address"],
        private_key=private_key,
    )
    escrow_contract = ContractUtils.get_contract(
        contract_name="IbetEscrow", contract_address=escrow_contract_address
    )

    # update storage
    storage_contract = ContractUtils.get_contract(
        contract_name="EscrowStorage", contract_address=escrow_storage_address
    )
    tx = storage_contract.functions.upgradeVersion(
        escrow_contract_address
    ).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": deployer["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    return escrow_contract


async def issue_bond_token(issuer: dict, exchange_address: str):
    issuer_address = issuer["address"]
    issuer_pk = decode_keyfile_json(
        raw_keyfile_json=issuer.get("keyfile_json"),
        password=issuer.get("password").encode("utf-8"),
    )

    # deploy token
    arguments = [
        "テスト債券",
        "TEST",
        2**256 - 1,
        10000,
        "JPY",
        "20211231",
        10000,
        "JPY",
        "20211231",
        "リターン内容",
        "発行目的",
    ]
    token_contract_address, _, _ = await IbetStraightBondContract().create(
        args=arguments, tx_sender=issuer_address, tx_sender_key=issuer_pk
    )
    token_contract = ContractUtils.get_contract(
        contract_name="IbetStraightBond", contract_address=token_contract_address
    )
    tx = token_contract.functions.setTransferable(True).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=issuer_pk)

    # set tradable exchange address
    tx = token_contract.functions.setTradableExchange(
        exchange_address
    ).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=issuer_pk)

    return token_contract


class TestGetAccountBalance:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # balance = 0, commitment = 0
    # Default value
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        user1_account = default_eth_account("user1")

        # deploy contract
        exchange_contract = deploy_escrow_contract()
        token_contract = await issue_bond_token(
            issuer=user1_account, exchange_address=exchange_contract.address
        )

        # test IbetExchangeInterface.get_account_balance
        exchange_interface = IbetExchangeInterface(exchange_contract.address)
        exchange_balance = await exchange_interface.get_account_balance(
            account_address=user1_account["address"],
            token_address=token_contract.address,
        )

        # assertion
        assert exchange_balance["balance"] == 0
        assert exchange_balance["commitment"] == 0

    # <Normal_2>
    @pytest.mark.asyncio
    async def test_normal_2(self, async_db):
        user1_account = default_eth_account("user1")
        user1_account_pk = decode_keyfile_json(
            raw_keyfile_json=user1_account["keyfile_json"],
            password=user1_account["password"].encode("utf-8"),
        )
        user2_account = default_eth_account("user2")

        # deploy contract
        exchange_contract = deploy_escrow_contract()
        token_contract = await issue_bond_token(
            issuer=user1_account, exchange_address=exchange_contract.address
        )

        # transfer -> create balance
        tx = token_contract.functions.transfer(
            exchange_contract.address, 100
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user1_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user1_account_pk)

        # create commitment
        tx = exchange_contract.functions.createEscrow(
            token_contract.address,
            user2_account["address"],
            30,
            user1_account["address"],
            "test_data",
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user1_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user1_account_pk)

        # test IbetExchangeInterface.get_account_balance
        exchange_interface = IbetExchangeInterface(exchange_contract.address)
        exchange_balance = await exchange_interface.get_account_balance(
            account_address=user1_account["address"],
            token_address=token_contract.address,
        )

        # assertion
        assert exchange_balance["balance"] == 70
        assert exchange_balance["commitment"] == 30

    # <Normal_3>
    # Not deployed contract
    @pytest.mark.asyncio
    async def test_normal_3(self, async_db):
        user1_account = default_eth_account("user1")

        # test IbetExchangeInterface.get_account_balance
        exchange_interface = IbetExchangeInterface(ZERO_ADDRESS)
        exchange_balance = await exchange_interface.get_account_balance(
            account_address=user1_account["address"], token_address=ZERO_ADDRESS
        )

        # assertion
        assert exchange_balance["balance"] == 0
        assert exchange_balance["commitment"] == 0
