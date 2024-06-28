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

import json
import logging
from datetime import UTC, datetime
from unittest import mock
from unittest.mock import patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    Account,
    IDXTransfer,
    IDXTransferBlockNumber,
    IDXTransferSourceEventType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper, Web3Wrapper
from batch.indexer_transfer import LOG, Processor, main
from config import CHAIN_ID, TX_GAS_LIMIT
from tests.account_config import config_eth_account
from tests.contract_utils import PersonalInfoContractTestUtils

web3 = Web3Wrapper()
async_web3 = AsyncWeb3Wrapper()


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
def processor(db, caplog: pytest.LogCaptureFixture):
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


async def deploy_share_token_contract(
    address,
    private_key,
    personal_info_contract_address,
    tradable_exchange_contract_address=None,
    transfer_approval_required=None,
):
    arguments = [
        "token.name",
        "token.symbol",
        20,
        100,
        3,
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        30,
    ]
    share_contract = IbetShareContract()
    token_address, _, _ = await share_contract.create(arguments, address, private_key)
    await share_contract.update(
        data=IbetShareUpdateParams(
            transferable=True,
            personal_info_contract_address=personal_info_contract_address,
            tradable_exchange_contract_address=tradable_exchange_contract_address,
            transfer_approval_required=transfer_approval_required,
        ),
        tx_from=address,
        private_key=private_key,
    )

    return ContractUtils.get_contract("IbetShare", token_address)


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Single Token
    # No event logs
    # not issue token
    @pytest.mark.asyncio
    async def test_normal_1_1(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Token(processing token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = "abi"
        token_1.tx_hash = "tx_hash"
        token_1.token_status = 0
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _transfer_list = db.scalars(select(IDXTransfer)).all()
        assert len(_transfer_list) == 0
        _idx_transfer_block_number = db.scalars(
            select(IDXTransferBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # Single Token
    # No event logs
    # issued token
    @pytest.mark.asyncio
    async def test_normal_1_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_06
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_block_number = IDXTransferBlockNumber()
        _idx_transfer_block_number.latest_block_number = 0
        db.add(_idx_transfer_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _transfer_list = db.scalars(select(IDXTransfer)).all()
        assert len(_transfer_list) == 0
        _idx_transfer_block_number = db.scalars(
            select(IDXTransferBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Single Token
    # Single event logs
    # - Transfer
    # - Unlock
    @pytest.mark.asyncio
    async def test_normal_2_1(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        lock_account = config_eth_account("user3")
        lock_account_pk = decode_keyfile_json(
            raw_keyfile_json=lock_account["keyfile_json"],
            password=lock_account["password"].encode("utf-8"),
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_06
        db.add(token_2)

        db.commit()

        # Transfer
        tx_1 = token_contract_1.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(
            tx_1, issuer_private_key
        )

        # Unlock (lock -> unlock)
        tx_2_1 = token_contract_1.functions.lock(
            lock_account["address"], 10, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, _ = ContractUtils.send_transaction(tx_2_1, issuer_private_key)

        tx_2_2 = token_contract_1.functions.unlock(
            issuer_address, user_address_1, 10, json.dumps({"message": "unlock"})
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": lock_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(
            tx_2_2, lock_account_pk
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _transfer_list = db.scalars(select(IDXTransfer)).all()
        assert len(_transfer_list) == 2

        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_2
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert _transfer.data == {"message": "unlock"}
        block = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _idx_transfer_block_number = db.scalars(
            select(IDXTransferBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_2_2>
    # Single Token
    # Single event logs
    # - Unlock: Data is not registered because "from" and "to" are the same
    @pytest.mark.asyncio
    async def test_normal_2_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        lock_account = config_eth_account("user3")
        lock_account_pk = decode_keyfile_json(
            raw_keyfile_json=lock_account["keyfile_json"],
            password=lock_account["password"].encode("utf-8"),
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_06
        db.add(token_2)

        db.commit()

        # Unlock (lock -> unlock)
        tx_1_1 = token_contract_1.functions.lock(
            lock_account["address"], 10, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, _ = ContractUtils.send_transaction(tx_1_1, issuer_private_key)

        tx_1_2 = token_contract_1.functions.unlock(
            issuer_address, issuer_address, 10, json.dumps({"message": "unlock"})
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": lock_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, _ = ContractUtils.send_transaction(tx_1_2, lock_account_pk)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _transfer_list = db.scalars(select(IDXTransfer)).all()
        assert len(_transfer_list) == 0

        _idx_transfer_block_number = db.scalars(
            select(IDXTransferBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_3_1>
    # Single Token
    # Multi event logs
    # - Transfer(twice)
    # - Unlock(twice)
    @pytest.mark.asyncio
    async def test_normal_3_1(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        lock_account = config_eth_account("user4")
        lock_account_pk = decode_keyfile_json(
            raw_keyfile_json=lock_account["keyfile_json"],
            password=lock_account["password"].encode("utf-8"),
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_06
        db.add(token_2)

        db.commit()

        # Transfer
        tx_1 = token_contract_1.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(
            tx_1, issuer_private_key
        )

        tx_2 = token_contract_1.functions.transferFrom(
            issuer_address, user_address_2, 30
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(
            tx_2, issuer_private_key
        )

        # Unlock (lock -> unlock)
        tx_3_1 = token_contract_1.functions.lock(
            lock_account["address"], 10, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, _ = ContractUtils.send_transaction(tx_3_1, issuer_private_key)

        tx_3_2 = token_contract_1.functions.unlock(
            issuer_address, user_address_1, 10, json.dumps({"message": "unlock"})
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": lock_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_3, tx_receipt_3 = ContractUtils.send_transaction(
            tx_3_2, lock_account_pk
        )

        tx_4_1 = token_contract_1.functions.lock(
            lock_account["address"], 10, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, _ = ContractUtils.send_transaction(tx_4_1, issuer_private_key)

        tx_4_2 = token_contract_1.functions.unlock(
            issuer_address, user_address_1, 10, json.dumps({"message": "unlock"})
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": lock_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_4, tx_receipt_4 = ContractUtils.send_transaction(
            tx_4_2, lock_account_pk
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _transfer_list = db.scalars(select(IDXTransfer)).all()
        assert len(_transfer_list) == 4

        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_2
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_2
        assert _transfer.amount == 30
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        block = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _transfer = _transfer_list[2]
        assert _transfer.id == 3
        assert _transfer.transaction_hash == tx_hash_3
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert _transfer.data == {"message": "unlock"}
        block = web3.eth.get_block(tx_receipt_3["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _transfer = _transfer_list[3]
        assert _transfer.id == 4
        assert _transfer.transaction_hash == tx_hash_4
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert _transfer.data == {"message": "unlock"}
        block = web3.eth.get_block(tx_receipt_4["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _idx_transfer_block_number = db.scalars(
            select(IDXTransferBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_3_2>
    # Single Token
    # Multi event logs
    # - Transfer(BulkTransfer)
    @pytest.mark.asyncio
    async def test_normal_3_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )
        user_4 = config_eth_account("user3")
        user_address_3 = user_4["address"]
        user_pk_3 = decode_keyfile_json(
            raw_keyfile_json=user_4["keyfile_json"], password="password".encode("utf-8")
        )
        user_5 = config_eth_account("user3")
        user_address_4 = user_5["address"]
        user_pk_4 = decode_keyfile_json(
            raw_keyfile_json=user_5["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_3,
            user_pk_3,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_4,
            user_pk_4,
            [issuer_address, ""],
        )

        # Bulk Transfer
        address_list1 = [user_address_1, user_address_2, user_address_3]
        value_list1 = [10, 20, 30]
        tx = token_contract_1.functions.bulkTransfer(
            address_list1, value_list1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        # BulkTransfer: 2nd
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)
        address_list2 = [user_address_1, user_address_2, user_address_3, user_address_4]
        value_list2 = [1, 2, 3, 4]
        tx = token_contract_1.functions.bulkTransfer(
            address_list2, value_list2
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _transfer_list = db.scalars(select(IDXTransfer)).all()
        assert len(_transfer_list) == 7

        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        for i in range(0, 3):
            _transfer = _transfer_list[i]
            assert _transfer.id == i + 1
            assert _transfer.transaction_hash == tx_hash_1
            assert _transfer.token_address == token_address_1
            assert _transfer.from_address == issuer_address
            assert _transfer.to_address == address_list1[i]
            assert _transfer.amount == value_list1[i]
            assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
            assert _transfer.data is None
            assert _transfer.block_timestamp == datetime.fromtimestamp(
                block["timestamp"], UTC
            ).replace(tzinfo=None)

        block = web3.eth.get_block(tx_receipt_2["blockNumber"])
        for i in range(0, 4):
            _transfer = _transfer_list[i + 3]
            assert _transfer.id == i + 1 + 3
            assert _transfer.transaction_hash == tx_hash_2
            assert _transfer.token_address == token_address_1
            assert _transfer.from_address == issuer_address
            assert _transfer.to_address == address_list2[i]
            assert _transfer.amount == value_list2[i]
            assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
            assert _transfer.data is None
            assert _transfer.block_timestamp == datetime.fromtimestamp(
                block["timestamp"], UTC
            ).replace(tzinfo=None)

        _idx_transfer_block_number = db.scalars(
            select(IDXTransferBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_4>
    # Multi Token
    @pytest.mark.asyncio
    async def test_normal_4(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token1
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        # Prepare data : Token2
        token_contract_2 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )

        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_24_06
        db.add(token_2)

        db.commit()

        # Transfer(Token1)
        tx = token_contract_1.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)
        tx = token_contract_1.functions.transferFrom(
            issuer_address, user_address_2, 30
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Transfer(Token2)
        tx = token_contract_2.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_3, tx_receipt_3 = ContractUtils.send_transaction(tx, issuer_private_key)
        tx = token_contract_2.functions.transferFrom(
            issuer_address, user_address_2, 30
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_4, tx_receipt_4 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _transfer_list = db.scalars(select(IDXTransfer)).all()
        assert len(_transfer_list) == 4
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_2
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_2
        assert _transfer.amount == 30
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        block = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _transfer = _transfer_list[2]
        assert _transfer.id == 3
        assert _transfer.transaction_hash == tx_hash_3
        assert _transfer.token_address == token_address_2
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        block = web3.eth.get_block(tx_receipt_3["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _transfer = _transfer_list[3]
        assert _transfer.id == 4
        assert _transfer.transaction_hash == tx_hash_4
        assert _transfer.token_address == token_address_2
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_2
        assert _transfer.amount == 30
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        block = web3.eth.get_block(tx_receipt_4["blockNumber"])
        assert _transfer.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        _idx_transfer_block_number = db.scalars(
            select(IDXTransferBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_5>
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip process".
    @pytest.mark.asyncio
    @mock.patch("web3.eth.Eth.block_number", 100)
    async def test_normal_5(
        self, processor: Processor, db: Session, caplog: pytest.LogCaptureFixture
    ):
        _idx_position_bond_block_number = IDXTransferBlockNumber()
        _idx_position_bond_block_number.id = 1
        _idx_position_bond_block_number.latest_block_number = 1000
        db.add(_idx_position_bond_block_number)
        db.commit()

        await processor.sync_new_logs()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "skip process")
        )

    # <Normal_6>
    # Newly tokens added
    @pytest.mark.asyncio
    async def test_normal_6(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Issuer issues bond token.
        token_contract1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        db.commit()

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        assert len(processor.token_list.keys()) == 1

        # Prepare additional token
        token_contract2 = await deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_24_06
        db.add(token_2)

        db.commit()

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        # newly issued token is loaded properly
        assert len(processor.token_list.keys()) == 2

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # If each error occurs, batch will output logs and continue next sync.
    @pytest.mark.asyncio
    async def test_error_1(
        self,
        main_func,
        db: Session,
        personal_info_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_06
        db.add(token_1)

        db.commit()

        # Run mainloop once and fail with web3 utils error
        with patch("batch.indexer_transfer.INDEXER_SYNC_INTERVAL", None), patch.object(
            AsyncWeb3Wrapper().eth, "contract", side_effect=ServiceUnavailableError()
        ), pytest.raises(TypeError):
            await main_func()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()

        # Run mainloop once and fail with sqlalchemy InvalidRequestError
        with patch("batch.indexer_transfer.INDEXER_SYNC_INTERVAL", None), patch.object(
            AsyncSession, "scalars", side_effect=InvalidRequestError()
        ), pytest.raises(TypeError):
            await main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()
