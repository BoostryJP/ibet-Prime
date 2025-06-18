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

from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from eth_keyfile import decode_keyfile_json
from httpx import ASGITransport, AsyncClient
from pytest_asyncio import is_async_test
from sqlalchemy import text
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import RPCEndpoint

from app.database import (
    AsyncSessionLocal,
    async_engine,
    db_async_session,
)
from app.main import app
from app.model.db import Base
from app.utils.ibet_contract_utils import ContractUtils as IbetContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


#####################################################
# Test Client
#####################################################
@pytest_asyncio.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, Any]:
    async_client = AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    )
    async with async_client as s:
        yield s


#####################################################
# DB
#####################################################
@pytest_asyncio.fixture(scope="session")
async def async_db_engine():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_engine

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def async_db(async_db_engine):
    # Create DB session
    _db = AsyncSessionLocal()

    def override_inject_db_session():
        return _db

    # Replace target API's dependency DB session.
    app.dependency_overrides[db_async_session] = override_inject_db_session

    async with _db as session:
        await session.begin()
        yield session
        await session.rollback()

        # Remove DB tables
        await session.begin()
        for table in Base.metadata.sorted_tables:
            await session.execute(
                text(f'ALTER TABLE "{table.name}" DISABLE TRIGGER ALL;')
            )
            await session.execute(text(f'TRUNCATE TABLE "{table.name}";'))
            if table.autoincrement_column is not None:
                await session.execute(
                    text(
                        f"ALTER SEQUENCE {table.name}_{table.autoincrement_column.name}_seq RESTART WITH 1;"
                    )
                )
            await session.execute(
                text(f'ALTER TABLE "{table.name}" ENABLE TRIGGER ALL;')
            )
        await session.commit()

    app.dependency_overrides[db_async_session] = db_async_session


#####################################################
# ibet: Blockchain & Smart Contract
#####################################################
@pytest.fixture(scope="function", autouse=True)
def ibet_block_number(request):
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
def ibet_personal_info_contract():
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy personal info contract
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "PersonalInfo", [], deployer_address, deployer_private_key
    )
    return IbetContractUtils.get_contract("PersonalInfo", contract_address)


@pytest.fixture(scope="function")
def ibet_exchange_contract():
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy payment gateway contract
    payment_gateway_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "PaymentGateway", [], deployer_address, deployer_private_key
    )
    payment_gateway_contract = IbetContractUtils.get_contract(
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
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    # Deploy storage contract
    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "ExchangeStorage", [], deployer_address, deployer_private_key
    )

    # Deploy exchange contract
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetExchange",
        [payment_gateway_contract_address, storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    # Upgrade version
    storage_contract = IbetContractUtils.get_contract(
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
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetExchange", contract_address)


@pytest.fixture(scope="function")
def ibet_escrow_contract():
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy storage contract
    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "EscrowStorage", [], deployer_address, deployer_private_key
    )

    # Deploy escrow contract
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetEscrow", [storage_contract_address], deployer_address, deployer_private_key
    )

    # Upgrade version
    storage_contract = IbetContractUtils.get_contract(
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
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetEscrow", contract_address)


@pytest.fixture(scope="function")
def ibet_security_token_escrow_contract():
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy storage contract
    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "EscrowStorage", [], deployer_address, deployer_private_key
    )

    # Deploy security token escrow contract
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetSecurityTokenEscrow",
        [storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    # Upgrade version
    storage_contract = IbetContractUtils.get_contract(
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
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetSecurityTokenEscrow", contract_address)


@pytest.fixture(scope="function")
def ibet_security_token_dvp_contract():
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy storage contract
    storage_contract_address, _, _ = IbetContractUtils.deploy_contract(
        "DVPStorage", [], deployer_address, deployer_private_key
    )

    # Deploy security token DVP contract
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "IbetSecurityTokenDVP",
        [storage_contract_address],
        deployer_address,
        deployer_private_key,
    )

    # Upgrade version
    storage_contract = IbetContractUtils.get_contract(
        "DVPStorage", storage_contract_address
    )
    tx = storage_contract.functions.upgradeVersion(contract_address).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": deployer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    IbetContractUtils.send_transaction(tx, deployer_private_key)

    return IbetContractUtils.get_contract("IbetSecurityTokenDVP", contract_address)


@pytest.fixture(scope="function")
def ibet_e2e_messaging_contract():
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy e2e messaging contract
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "E2EMessaging", [], deployer_address, deployer_private_key
    )
    return IbetContractUtils.get_contract("E2EMessaging", contract_address)


@pytest.fixture(scope="function")
def ibet_freeze_log_contract():
    user_1 = default_eth_account("user1")
    deployer_address = user_1["address"]
    deployer_private_key = decode_keyfile_json(
        raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
    )

    # Deploy e2e messaging contract
    contract_address, _, _ = IbetContractUtils.deploy_contract(
        "FreezeLog", [], deployer_address, deployer_private_key
    )
    return IbetContractUtils.get_contract("FreezeLog", contract_address)
