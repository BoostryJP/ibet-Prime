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
import os
import sys

import pytest
from eth_keyfile import decode_keyfile_json
from fastapi.testclient import TestClient
from sqlalchemy import text

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)
path = os.path.join(os.path.dirname(__file__), "../batch")
sys.path.append(path)

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import RPCEndpoint

from app.database import SessionLocal, db_session, engine
from app.main import app
from app.utils.contract_utils import ContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def client():
    client = TestClient(app)
    return client


@pytest.fixture(scope="function")
def db():
    # Create DB session
    db = SessionLocal()

    def override_inject_db_session():
        return db

    # Replace target API's dependency DB session.
    app.dependency_overrides[db_session] = override_inject_db_session

    # Create DB tables
    from app.model.db import Base

    Base.metadata.create_all(engine)

    yield db

    # Remove DB tables
    db.rollback()
    db.begin()
    for table in Base.metadata.sorted_tables:
        db.execute(text(f'ALTER TABLE "{table.name}" DISABLE TRIGGER ALL;'))
        db.execute(text(f'TRUNCATE TABLE "{table.name}";'))
        if table.autoincrement_column is not None:
            db.execute(
                text(
                    f"ALTER SEQUENCE {table.name}_{table.autoincrement_column.name}_seq RESTART WITH 1;"
                )
            )
        db.execute(text(f'ALTER TABLE "{table.name}" ENABLE TRIGGER ALL;'))
    db.commit()
    db.close()

    app.dependency_overrides[db_session] = db_session


@pytest.fixture(scope="function", autouse=True)
def block_number(request):
    # save blockchain state before function starts
    evm_snapshot = web3.provider.make_request(RPCEndpoint("evm_snapshot"), [])

    def teardown():
        # revert blockchain state after function starts
        web3.provider.make_request(
            RPCEndpoint("evm_revert"),
            [
                int(evm_snapshot["result"], 16),
            ],
        )

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def personal_info_contract():
    user_1 = config_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy personal info contract
    contract_address, _, _ = ContractUtils.deploy_contract(
        "PersonalInfo", [], deployer_address, deployer_private_key
    )
    return ContractUtils.get_contract("PersonalInfo", contract_address)


@pytest.fixture(scope="function")
def ibet_exchange_contract():
    user_1 = config_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy payment gateway contract
    payment_gateway_contract_address, _, _ = ContractUtils.deploy_contract(
        "PaymentGateway", [], deployer_address, deployer_private_key
    )
    payment_gateway_contract = ContractUtils.get_contract(
        "PaymentGateway", payment_gateway_contract_address
    )
    tx = payment_gateway_contract.functions.addAgent(
        deployer_address
    ).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": deployer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(tx, deployer_private_key)

    # Deploy storage contract
    storage_contract_address, _, _ = ContractUtils.deploy_contract(
        "ExchangeStorage", [], deployer_address, deployer_private_key
    )

    # Deploy exchange contract
    contract_address, _, _ = ContractUtils.deploy_contract(
        "IbetExchange",
        [payment_gateway_contract_address, storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    # Upgrade version
    storage_contract = ContractUtils.get_contract(
        "ExchangeStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": deployer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(tx, deployer_private_key)

    return ContractUtils.get_contract("IbetExchange", contract_address)


@pytest.fixture(scope="function")
def ibet_escrow_contract():
    user_1 = config_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy storage contract
    storage_contract_address, _, _ = ContractUtils.deploy_contract(
        "EscrowStorage", [], deployer_address, deployer_private_key
    )

    # Deploy escrow contract
    contract_address, _, _ = ContractUtils.deploy_contract(
        "IbetEscrow", [storage_contract_address], deployer_address, deployer_private_key
    )

    # Upgrade version
    storage_contract = ContractUtils.get_contract(
        "EscrowStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": deployer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(tx, deployer_private_key)

    return ContractUtils.get_contract("IbetEscrow", contract_address)


@pytest.fixture(scope="function")
def ibet_security_token_escrow_contract():
    user_1 = config_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy storage contract
    storage_contract_address, _, _ = ContractUtils.deploy_contract(
        "EscrowStorage", [], deployer_address, deployer_private_key
    )

    # Deploy security token escrow contract
    contract_address, _, _ = ContractUtils.deploy_contract(
        "IbetSecurityTokenEscrow",
        [storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    # Upgrade version
    storage_contract = ContractUtils.get_contract(
        "EscrowStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": deployer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(tx, deployer_private_key)

    return ContractUtils.get_contract("IbetSecurityTokenEscrow", contract_address)


@pytest.fixture(scope="function")
def e2e_messaging_contract():
    user_1 = config_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy e2e messaging contract
    contract_address, _, _ = ContractUtils.deploy_contract(
        "E2EMessaging", [], deployer_address, deployer_private_key
    )
    return ContractUtils.get_contract("E2EMessaging", contract_address)
