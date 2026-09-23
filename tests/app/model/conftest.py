"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from typing import cast

import pytest
from eth_keyfile.keyfile import decode_keyfile_json
from web3.contract import Contract
from web3.types import TxParams

from app.utils.ibet_contract_utils import ContractUtils as IbetContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT
from tests.account_config import default_eth_account


def _build_tx_params(from_address: str) -> TxParams:
    return cast(
        TxParams,
        {
            "chainId": CHAIN_ID,
            "from": from_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        },
    )


@pytest.fixture(scope="function")
def ibet_personal_info_contract() -> Contract:
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "PersonalInfo", [], deployer_address, deployer_private_key
    )
    return IbetContractUtils.get_contract("PersonalInfo", contract_address)


@pytest.fixture(scope="function")
def ibet_exchange_contract() -> Contract:
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    payment_gateway_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "PaymentGateway", [], deployer_address, deployer_private_key
    )
    payment_gateway_contract = IbetContractUtils.get_contract(
        "PaymentGateway", payment_gateway_contract_address
    )
    tx = payment_gateway_contract.functions.addAgent(
        deployer_address
    ).build_transaction(_build_tx_params(deployer_address))
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "ExchangeStorage", [], deployer_address, deployer_private_key
    )
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetExchange",
        [payment_gateway_contract_address, storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    storage_contract = IbetContractUtils.get_contract(
        "ExchangeStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        _build_tx_params(deployer_address)
    )
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetExchange", contract_address)


@pytest.fixture(scope="function")
def ibet_escrow_contract() -> Contract:
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "EscrowStorage", [], deployer_address, deployer_private_key
    )
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetEscrow", [storage_contract_address], deployer_address, deployer_private_key
    )

    storage_contract = IbetContractUtils.get_contract(
        "EscrowStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        _build_tx_params(deployer_address)
    )
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetEscrow", contract_address)


@pytest.fixture(scope="function")
def ibet_security_token_escrow_contract() -> Contract:
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "EscrowStorage", [], deployer_address, deployer_private_key
    )
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetSecurityTokenEscrow",
        [storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    storage_contract = IbetContractUtils.get_contract(
        "EscrowStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        _build_tx_params(deployer_address)
    )
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetSecurityTokenEscrow", contract_address)


@pytest.fixture(scope="function")
def ibet_security_token_dvp_contract() -> Contract:
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "DVPStorage", [], deployer_address, deployer_private_key
    )
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetSecurityTokenDVP",
        [storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    storage_contract = IbetContractUtils.get_contract(
        "DVPStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        _build_tx_params(deployer_address)
    )
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetSecurityTokenDVP", contract_address)


@pytest.fixture(scope="function")
def ibet_e2e_messaging_contract() -> Contract:
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "E2EMessaging", [], deployer_address, deployer_private_key
    )
    return IbetContractUtils.get_contract("E2EMessaging", contract_address)


@pytest.fixture(scope="function")
def ibet_freeze_log_contract() -> Contract:
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "FreezeLog", [], deployer_address, deployer_private_key
    )
    return IbetContractUtils.get_contract("FreezeLog", contract_address)
