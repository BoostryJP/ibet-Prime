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

import base64
import json
import logging
from unittest.mock import patch

import pytest
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.model.blockchain import IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    Account,
    IDXPersonalInfo,
    IDXPersonalInfoBlockNumber,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import AsyncContractUtils, ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from batch.indexer_personal_info import LOG, Processor, main
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="function")
def main_func():
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.fixture(scope="function")
def processor(async_db, caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor()
    LOG.propagate = False
    LOG.setLevel(default_log_level)


async def deploy_bond_token_contract(
    address,
    private_key,
    personal_info_contract_address,
    tradable_exchange_contract_address=None,
    transfer_approval_required=None,
):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        "JPY",
        "token.redemption_date",
        30,
        "JPY",
        "token.return_date",
        "token.return_amount",
        "token.purpose",
    ]
    bond_contrat = IbetStraightBondContract()
    token_address, _, _ = await bond_contrat.create(arguments, address, private_key)
    await bond_contrat.update(
        data=IbetStraightBondUpdateParams(
            transferable=True,
            personal_info_contract_address=personal_info_contract_address,
            tradable_exchange_contract_address=tradable_exchange_contract_address,
            transfer_approval_required=transfer_approval_required,
        ),
        tx_from=address,
        private_key=private_key,
    )

    return ContractUtils.get_contract("IbetStraightBond", token_address)


def encrypt_personal_info(personal_info, rsa_public_key, passphrase):
    rsa_key = RSA.importKey(rsa_public_key, passphrase=passphrase)
    cipher = PKCS1_OAEP.new(rsa_key)
    ciphertext = base64.encodebytes(
        cipher.encrypt(json.dumps(personal_info).encode("utf-8"))
    )
    return ciphertext


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Single Token
    # No event logs
    # not issue token
    @pytest.mark.asyncio
    async def test_normal_1_1(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = user_1["rsa_private_key"]
        account.rsa_public_key = user_1["rsa_public_key"]
        account.rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_status = 3
        async_db.add(account)

        # Prepare data : Token(processing token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = {}
        token_1.tx_hash = "tx_hash"
        token_1.token_status = 0
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Assertion
        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 0

        _idx_personal_info_block_number = (
            await async_db.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

        _personal_info_history_list = (
            await async_db.scalars(select(IDXPersonalInfoHistory))
        ).all()
        assert len(_personal_info_history_list) == 0

    # <Normal_1_2>
    # Single Token
    # No event logs
    # issued token
    @pytest.mark.asyncio
    async def test_normal_1_2(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)

        # Prepare data : BlockNumber
        _idx_personal_info_block_number = IDXPersonalInfoBlockNumber()
        _idx_personal_info_block_number.latest_block_number = 0
        async_db.add(_idx_personal_info_block_number)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Assertion
        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 0

        _idx_personal_info_block_number = (
            await async_db.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

        _personal_info_history_list = (
            await async_db.scalars(select(IDXPersonalInfoHistory))
        ).all()
        assert len(_personal_info_history_list) == 0

    # <Normal_2_1>
    # Single Token
    # Single event logs
    # - Register
    @pytest.mark.asyncio
    async def test_normal_2_1(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)

        await async_db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        ciphertext = encrypt_personal_info(
            personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase
        )
        tx = personal_info_contract.functions.register(
            issuer_address, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Assertion
        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_1
        assert _personal_info.data_source == PersonalInfoDataSource.ON_CHAIN

        _personal_info_history_list = (
            await async_db.scalars(select(IDXPersonalInfoHistory))
        ).all()
        assert len(_personal_info_history_list) == 1
        _personal_info_history = _personal_info_history_list[0]
        assert _personal_info_history.id == 1
        assert _personal_info_history.account_address == user_address_1
        assert _personal_info_history.event_type == PersonalInfoEventType.REGISTER
        assert _personal_info_history.issuer_address == issuer_address
        assert _personal_info_history.personal_info == personal_info_1

        _idx_personal_info_block_number = (
            await async_db.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_2_2>
    # Single Token
    # Single event logs
    # - Modify
    @pytest.mark.asyncio
    async def test_normal_2_2(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)

        await async_db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        ciphertext = encrypt_personal_info(
            personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase
        )
        tx = personal_info_contract.functions.register(
            issuer_address, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Before run(consume accumulated events)
        await processor.process()
        async_db.expire_all()

        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_1
        assert _personal_info.data_source == PersonalInfoDataSource.ON_CHAIN

        # Modify
        personal_info_2 = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": True,
            "tax_category": 20,
        }
        ciphertext = encrypt_personal_info(
            personal_info_2, issuer_rsa_public_key, issuer_rsa_passphrase
        )
        tx = personal_info_contract.functions.modify(
            user_address_1, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest async_db session.
        async_db.expire_all()

        # Assertion
        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_2
        assert _personal_info.data_source == PersonalInfoDataSource.ON_CHAIN

        _personal_info_history_list = (
            await async_db.scalars(select(IDXPersonalInfoHistory))
        ).all()
        assert len(_personal_info_history_list) == 2
        _personal_info_history_1 = _personal_info_history_list[0]
        assert _personal_info_history_1.id == 1
        assert _personal_info_history_1.account_address == user_address_1
        assert _personal_info_history_1.event_type == PersonalInfoEventType.REGISTER
        assert _personal_info_history_1.issuer_address == issuer_address
        assert _personal_info_history_1.personal_info == personal_info_1
        _personal_info_history_2 = _personal_info_history_list[1]
        assert _personal_info_history_2.id == 2
        assert _personal_info_history_2.account_address == user_address_1
        assert _personal_info_history_2.event_type == PersonalInfoEventType.MODIFY
        assert _personal_info_history_2.issuer_address == issuer_address
        assert _personal_info_history_2.personal_info == personal_info_2

        _idx_personal_info_block_number = (
            await async_db.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_3>
    # Single Token
    # Multi event logs
    # - Modify(twice)
    @pytest.mark.asyncio
    async def test_normal_3(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)

        await async_db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        ciphertext = encrypt_personal_info(
            personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase
        )
        tx = personal_info_contract.functions.register(
            issuer_address, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Before run(consume accumulated events)
        await processor.process()
        async_db.expire_all()

        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_1
        assert _personal_info.data_source == PersonalInfoDataSource.ON_CHAIN

        # Modify
        personal_info_2 = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": True,
            "tax_category": 20,
        }
        ciphertext = encrypt_personal_info(
            personal_info_2, issuer_rsa_public_key, issuer_rsa_passphrase
        )
        tx = personal_info_contract.functions.modify(
            user_address_1, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Assertion
        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_2
        assert _personal_info.data_source == PersonalInfoDataSource.ON_CHAIN

        _personal_info_history_list = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory).order_by(IDXPersonalInfoHistory.id)
            )
        ).all()
        assert len(_personal_info_history_list) == 2
        _personal_info_history_1 = _personal_info_history_list[0]
        assert _personal_info_history_1.id == 1
        assert _personal_info_history_1.account_address == user_address_1
        assert _personal_info_history_1.event_type == PersonalInfoEventType.REGISTER
        assert _personal_info_history_1.issuer_address == issuer_address
        assert _personal_info_history_1.personal_info == personal_info_1
        _personal_info_history_2 = _personal_info_history_list[1]
        assert _personal_info_history_2.id == 2
        assert _personal_info_history_2.account_address == user_address_1
        assert _personal_info_history_2.event_type == PersonalInfoEventType.MODIFY
        assert _personal_info_history_2.issuer_address == issuer_address
        assert _personal_info_history_2.personal_info == personal_info_2

        _idx_personal_info_block_number = (
            await async_db.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

        # Modify
        personal_info_3 = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 30,
        }
        ciphertext = encrypt_personal_info(
            personal_info_3, issuer_rsa_public_key, issuer_rsa_passphrase
        )
        tx = personal_info_contract.functions.modify(
            user_address_1, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Assertion
        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_3
        assert _personal_info.data_source == PersonalInfoDataSource.ON_CHAIN

        _personal_info_history_list = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory).order_by(IDXPersonalInfoHistory.id)
            )
        ).all()
        assert len(_personal_info_history_list) == 3
        _personal_info_history = _personal_info_history_list[2]
        assert _personal_info_history.id == 3
        assert _personal_info_history.account_address == user_address_1
        assert _personal_info_history.event_type == PersonalInfoEventType.MODIFY
        assert _personal_info_history.issuer_address == issuer_address
        assert _personal_info_history.personal_info == personal_info_3

        _idx_personal_info_block_number = (
            await async_db.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_4>
    # Multi Token
    @pytest.mark.asyncio
    async def test_normal_4(self, processor, async_db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        issuer_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        issuer_rsa_private_key_1 = user_1["rsa_private_key"]
        issuer_rsa_public_key_1 = user_1["rsa_public_key"]
        issuer_rsa_passphrase_1 = "password"

        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]
        issuer_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        issuer_rsa_private_key_2 = user_2["rsa_private_key"]
        issuer_rsa_passphrase_2 = "password"
        issuer_rsa_public_key_2 = user_2["rsa_public_key"]

        # Prepare data : Account(Issuer1)
        account = Account()
        account.issuer_address = issuer_address_1
        account.rsa_private_key = issuer_rsa_private_key_1
        account.rsa_public_key = issuer_rsa_public_key_1
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase_1)
        account.rsa_status = 3
        async_db.add(account)

        # Prepare data : Account(Issuer2)
        account = Account()
        account.issuer_address = issuer_address_2
        account.rsa_private_key = issuer_rsa_private_key_2
        account.rsa_public_key = issuer_rsa_public_key_2
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase_2)
        account.rsa_status = 3
        async_db.add(account)

        # Deploy personal info contract
        contract_address_1, _, _ = ContractUtils.deploy_contract(
            "PersonalInfo", [], issuer_address_1, issuer_private_key_1
        )
        personal_info_contract_1 = ContractUtils.get_contract(
            "PersonalInfo", contract_address_1
        )
        contract_address_2, _, _ = ContractUtils.deploy_contract(
            "PersonalInfo", [], issuer_address_2, issuer_private_key_2
        )
        personal_info_contract_2 = ContractUtils.get_contract(
            "PersonalInfo", contract_address_2
        )

        # Issuer1 issues bond token.
        token_contract1 = await deploy_bond_token_contract(
            issuer_address_1,
            issuer_private_key_1,
            personal_info_contract_1.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address_1
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)

        # Issuer2 issues bond token.
        token_contract2 = await deploy_bond_token_contract(
            issuer_address_2,
            issuer_private_key_2,
            personal_info_contract_2.address,
            transfer_approval_required=False,
        )
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address_2
        token_2.abi = token_contract2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)

        await async_db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        ciphertext = encrypt_personal_info(
            personal_info_1, issuer_rsa_public_key_1, issuer_rsa_passphrase_1
        )
        tx = personal_info_contract_1.functions.register(
            issuer_address_1, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key_1)

        personal_info_2 = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": True,
            "tax_category": 20,
        }
        ciphertext = encrypt_personal_info(
            personal_info_2, issuer_rsa_public_key_2, issuer_rsa_passphrase_2
        )
        tx = personal_info_contract_2.functions.register(
            issuer_address_2, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address_2,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key_2)

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Prepare data for assertion
        tmp_list = [
            {
                "issuer_address": issuer_address_1,
                "personal_info_address": personal_info_contract_1.address,
            },
            {
                "issuer_address": issuer_address_2,
                "personal_info_address": personal_info_contract_2.address,
            },
        ]
        personal_info_dict = {
            issuer_address_1: personal_info_1,
            issuer_address_2: personal_info_2,
        }
        unique_list = list(map(json.loads, set(map(json.dumps, tmp_list))))
        stored_address_order = [line["issuer_address"] for line in unique_list]

        # Assertion
        _personal_info_list = (await async_db.scalars(select(IDXPersonalInfo))).all()
        assert len(_personal_info_list) == 2

        for i in range(2):
            _personal_info = _personal_info_list[i]
            assert _personal_info.account_address == stored_address_order[i]
            assert _personal_info.issuer_address == stored_address_order[i]
            assert (
                _personal_info.personal_info
                == personal_info_dict[stored_address_order[i]]
            )
            assert _personal_info.data_source == PersonalInfoDataSource.ON_CHAIN

        _personal_info_history_list = (
            await async_db.scalars(select(IDXPersonalInfoHistory))
        ).all()
        assert len(_personal_info_history_list) == 2

        for i in range(2):
            _personal_info_history = _personal_info_history_list[i]
            assert _personal_info_history.id == i + 1
            assert _personal_info_history.account_address == stored_address_order[i]
            assert _personal_info_history.event_type == PersonalInfoEventType.REGISTER
            assert _personal_info_history.issuer_address == stored_address_order[i]
            assert (
                _personal_info_history.personal_info
                == personal_info_dict[stored_address_order[i]]
            )

        _idx_personal_info_block_number = (
            await async_db.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_5>
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip Process".
    @pytest.mark.asyncio
    async def test_normal_5(
        self, processor: Processor, async_db, caplog: pytest.LogCaptureFixture
    ):
        _idx_personal_info_block_number = IDXPersonalInfoBlockNumber()
        _idx_personal_info_block_number.id = 1
        _idx_personal_info_block_number.latest_block_number = 99999999
        async_db.add(_idx_personal_info_block_number)
        await async_db.commit()

        await processor.process()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "skip process")
        )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # If DB session fails in phase sinking register/modify events, batch logs exception message.
    @pytest.mark.asyncio
    async def test_error_1(
        self,
        main_func,
        async_db,
        personal_info_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        async_db.add(token_1)

        await async_db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        ciphertext = encrypt_personal_info(
            personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase
        )
        tx = personal_info_contract.functions.register(
            issuer_address, ciphertext.decode("utf-8")
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Run mainloop once and fail with sqlalchemy InvalidRequestError
        with (
            patch("batch.indexer_personal_info.INDEXER_SYNC_INTERVAL", None),
            patch.object(AsyncSession, "scalars", side_effect=InvalidRequestError()),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()

        # Run mainloop once and fail with connection to blockchain
        with (
            patch("batch.indexer_personal_info.INDEXER_SYNC_INTERVAL", None),
            patch.object(AsyncContractUtils, "call_function", ConnectionError()),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.ERROR,
                "An exception occurred during event synchronization",
            )
        )
        caplog.clear()
