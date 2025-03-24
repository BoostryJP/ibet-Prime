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

import logging
from datetime import UTC, datetime
from unittest import mock
from unittest.mock import patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

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
    IDXIssueRedeem,
    IDXIssueRedeemBlockNumber,
    IDXIssueRedeemEventType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch.indexer_issue_redeem import LOG, Processor, main
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER, ZERO_ADDRESS
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

    # Normal_1
    # No token issued
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

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
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list = (await async_db.scalars(select(IDXIssueRedeem))).all()
        assert len(event_list) == 0

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_2
    # No events emitted
    @pytest.mark.asyncio
    async def test_normal_2(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list = (await async_db.scalars(select(IDXIssueRedeem))).all()
        assert len(event_list) == 0

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_3_1
    # "Issue" event has been emitted
    # Bond
    @pytest.mark.asyncio
    async def test_normal_3_1(self, processor, async_db, personal_info_contract):
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
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # issueFrom
        tx = token_contract_1.functions.issueFrom(
            issuer_address, ZERO_ADDRESS, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: list[IDXIssueRedeem] = (
            await async_db.scalars(select(IDXIssueRedeem))
        ).all()
        assert len(event_list) == 1
        event_0 = event_list[0]
        assert event_0.id == 1
        assert event_0.event_type == IDXIssueRedeemEventType.ISSUE
        assert event_0.transaction_hash == tx_hash_1
        assert event_0.token_address == token_address_1
        assert event_0.locked_address == ZERO_ADDRESS
        assert event_0.target_address == issuer_address
        assert event_0.amount == 40
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert event_0.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_3_2
    # "Issue" event has been emitted
    # Share
    @pytest.mark.asyncio
    async def test_normal_3_2(self, processor, async_db, personal_info_contract):
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
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_share_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # issueFrom
        tx = token_contract_1.functions.issueFrom(
            issuer_address, ZERO_ADDRESS, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: list[IDXIssueRedeem] = (
            await async_db.scalars(select(IDXIssueRedeem))
        ).all()
        assert len(event_list) == 1
        event_0 = event_list[0]
        assert event_0.id == 1
        assert event_0.event_type == IDXIssueRedeemEventType.ISSUE
        assert event_0.transaction_hash == tx_hash_1
        assert event_0.token_address == token_address_1
        assert event_0.locked_address == ZERO_ADDRESS
        assert event_0.target_address == issuer_address
        assert event_0.amount == 40
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert event_0.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_4_1
    # "Redeem" event has been emitted
    # Bond
    @pytest.mark.asyncio
    async def test_normal_4_1(self, processor, async_db, personal_info_contract):
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
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # redeemFrom
        tx = token_contract_1.functions.redeemFrom(
            issuer_address, ZERO_ADDRESS, 10
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: list[IDXIssueRedeem] = (
            await async_db.scalars(select(IDXIssueRedeem))
        ).all()
        assert len(event_list) == 1
        event_0 = event_list[0]
        assert event_0.id == 1
        assert event_0.event_type == IDXIssueRedeemEventType.REDEEM
        assert event_0.transaction_hash == tx_hash_1
        assert event_0.token_address == token_address_1
        assert event_0.locked_address == ZERO_ADDRESS
        assert event_0.target_address == issuer_address
        assert event_0.amount == 10
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert event_0.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_4_2
    # "Redeem" event has been emitted
    # Share
    @pytest.mark.asyncio
    async def test_normal_4_2(self, processor, async_db, personal_info_contract):
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
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_share_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # redeemFrom
        tx = token_contract_1.functions.redeemFrom(
            issuer_address, ZERO_ADDRESS, 10
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: list[IDXIssueRedeem] = (
            await async_db.scalars(select(IDXIssueRedeem))
        ).all()
        assert len(event_list) == 1
        event_0 = event_list[0]
        assert event_0.id == 1
        assert event_0.event_type == IDXIssueRedeemEventType.REDEEM
        assert event_0.transaction_hash == tx_hash_1
        assert event_0.token_address == token_address_1
        assert event_0.locked_address == ZERO_ADDRESS
        assert event_0.target_address == issuer_address
        assert event_0.amount == 10
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert event_0.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_5
    # Multiple events have been emitted
    @pytest.mark.asyncio
    async def test_normal_5(self, processor, async_db, personal_info_contract):
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
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # issueFrom * 2
        tx = token_contract_1.functions.issueFrom(
            issuer_address, ZERO_ADDRESS, 10
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        tx = token_contract_1.functions.issueFrom(
            issuer_address, ZERO_ADDRESS, 20
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
        async_db.expire_all()

        # Assertion
        event_list: list[IDXIssueRedeem] = (
            await async_db.scalars(select(IDXIssueRedeem))
        ).all()
        assert len(event_list) == 2

        event_0 = event_list[0]
        assert event_0.id == 1
        assert event_0.event_type == IDXIssueRedeemEventType.ISSUE
        assert event_0.transaction_hash == tx_hash_1
        assert event_0.token_address == token_address_1
        assert event_0.locked_address == ZERO_ADDRESS
        assert event_0.target_address == issuer_address
        assert event_0.amount == 10
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert event_0.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        event_1 = event_list[1]
        assert event_1.id == 2
        assert event_1.event_type == IDXIssueRedeemEventType.ISSUE
        assert event_1.transaction_hash == tx_hash_2
        assert event_1.token_address == token_address_1
        assert event_1.locked_address == ZERO_ADDRESS
        assert event_1.target_address == issuer_address
        assert event_1.amount == 20
        block = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert event_1.block_timestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_6
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip process".
    @pytest.mark.asyncio
    @mock.patch("web3.eth.Eth.block_number", 100)
    async def test_normal_6(
        self, processor: Processor, async_db, caplog: pytest.LogCaptureFixture
    ):
        _idx_position_bond_block_number = IDXIssueRedeemBlockNumber()
        _idx_position_bond_block_number.id = 1
        _idx_position_bond_block_number.latest_block_number = 1000
        async_db.add(_idx_position_bond_block_number)
        await async_db.commit()

        await processor.sync_new_logs()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "skip process")
        )

    # Normal_7
    # Newly tokens added
    @pytest.mark.asyncio
    async def test_normal_7(
        self, processor: Processor, async_db, personal_info_contract
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
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        assert len(processor.token_list.keys()) == 1

        # Prepare additional token
        token_contract_2 = await deploy_share_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
        )

        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_24_09
        async_db.add(token_2)

        await async_db.commit()

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        # newly issued token is loaded properly
        assert len(processor.token_list.keys()) == 2

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # If each error occurs, batch will output logs and continue next sync.
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

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            address=issuer_address,
            private_key=issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
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

        # Run mainloop once and fail with web3 utils error
        with (
            patch("batch.indexer_issue_redeem.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                AsyncWeb3Wrapper().eth,
                "contract",
                side_effect=ServiceUnavailableError(),
            ),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()

        # Run mainloop once and fail with sqlalchemy InvalidRequestError
        with (
            patch("batch.indexer_issue_redeem.INDEXER_SYNC_INTERVAL", None),
            patch.object(AsyncSession, "execute", side_effect=InvalidRequestError()),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()
