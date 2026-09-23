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
from typing import Any, Sequence, cast
from unittest.mock import MagicMock, patch

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.types import TxReceipt

import batch.indexer_issue_redeem as indexer_issue_redeem
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    Account,
    AccountRsaStatus,
    IDXIssueRedeem,
    IDXIssueRedeemBlockNumber,
    IDXIssueRedeemEventType,
    Token,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch.indexer_issue_redeem import LOG, Processor, main
from config import ZERO_ADDRESS
from tests.account_config import default_eth_account

BOND_TOKEN_ADDRESS = to_checksum_address("0x0000000000000000000000000000000000000301")
SHARE_TOKEN_ADDRESS = to_checksum_address("0x0000000000000000000000000000000000000302")
PERSONAL_INFO_CONTRACT_ADDRESS = to_checksum_address(
    "0x0000000000000000000000000000000000000303"
)
EVENT_BLOCK_NUMBER = 10
ISSUE_TX_HASH_1 = "0x" + "11" * 32
ISSUE_TX_HASH_2 = "0x" + "12" * 32
REDEEM_TX_HASH = "0x" + "13" * 32


def get_fake_contract(contract_name: str, contract_address: str) -> MagicMock:
    contract = MagicMock()
    contract.address = contract_address
    contract.abi = {}
    contract.events = MagicMock()
    return contract


class FakeAsyncEth:
    @property
    def block_number(self):
        return self._get_block_number()

    async def _get_block_number(self) -> int:
        return 100

    def contract(self, address: str, abi: Any) -> MagicMock:
        return get_fake_contract("IbetSecurityTokenInterface", address)

    async def get_block(self, block_number: int) -> dict[str, int]:
        return {"timestamp": 1_700_000_000 + block_number}


class FakeAsyncWeb3:
    eth = FakeAsyncEth()


class FakeSyncEth:
    @property
    def block_number(self):
        return self._get_block_number()

    async def _get_block_number(self) -> int:
        return 100

    def get_block(self, block_number: int) -> dict[str, int]:
        return {"timestamp": 1_700_000_000 + block_number}


class FakeSyncWeb3:
    eth = FakeSyncEth()


web3 = FakeSyncWeb3()
_EVENT_LOGS: dict[tuple[str, str], list[dict[str, Any]]] = {}


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
def processor(async_db: AsyncSession, caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor()
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.fixture(scope="function", autouse=True)
def blockchain_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Fixture to mock the blockchain for testing purposes.
    """

    _EVENT_LOGS.clear()
    monkeypatch.setattr(indexer_issue_redeem, "web3", FakeAsyncWeb3())

    async def get_event_logs(
        contract: Any,
        event: str,
        block_from: int,
        block_to: int,
    ) -> list[dict[str, Any]]:
        return _EVENT_LOGS.get((contract.address, event), [])

    monkeypatch.setattr(AsyncContractUtils, "get_event_logs", get_event_logs)


def add_event(
    token_address: str,
    event_name: str,
    transaction_hash: str,
    block_number: int,
    target_address: str,
    amount: int,
) -> TxReceipt:
    _EVENT_LOGS.setdefault((token_address, event_name), []).append(
        {
            "transactionHash": HexBytes(transaction_hash),
            "blockNumber": block_number,
            "args": {
                "lockAddress": ZERO_ADDRESS,
                "targetAddress": target_address,
                "amount": amount,
            },
        }
    )
    return cast(TxReceipt, {"blockNumber": block_number})


async def create_fake_bond_token_contract() -> MagicMock:
    return get_fake_contract("IbetStraightBond", BOND_TOKEN_ADDRESS)


async def create_fake_share_token_contract() -> MagicMock:
    return get_fake_contract("IbetShare", SHARE_TOKEN_ADDRESS)


def _get_block_number(tx_receipt: TxReceipt) -> int:
    block_number = tx_receipt.get("blockNumber")
    assert block_number is not None
    return block_number


async def _get_block_timestamp(tx_receipt: TxReceipt) -> datetime:
    block = web3.eth.get_block(_get_block_number(tx_receipt))
    timestamp = block.get("timestamp")
    assert timestamp is not None
    return datetime.fromtimestamp(timestamp, UTC).replace(tzinfo=None)


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # No token issued
    @pytest.mark.asyncio
    async def test_normal_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Token(processing token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = {}
        token_1.tx_hash = "tx_hash"
        token_1.token_status = TokenStatus.PENDING
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)
        await async_db.commit()

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list = (await async_db.scalars(select(IDXIssueRedeem))).all()
        assert len(event_list) == 0

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number is not None
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_2
    # No events emitted
    @pytest.mark.asyncio
    async def test_normal_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list = (await async_db.scalars(select(IDXIssueRedeem))).all()
        assert len(event_list) == 0

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number is not None
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_3_1
    # "Issue" event has been emitted
    # Bond
    @pytest.mark.asyncio
    async def test_normal_3_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Create "Issue" event
        tx_hash_1 = ISSUE_TX_HASH_1
        tx_receipt_1 = add_event(
            token_address_1,
            "Issue",
            tx_hash_1,
            EVENT_BLOCK_NUMBER,
            issuer_address,
            40,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: Sequence[IDXIssueRedeem] = (
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
        assert event_0.block_timestamp == await _get_block_timestamp(tx_receipt_1)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number is not None
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_3_2
    # "Issue" event has been emitted
    # Share
    @pytest.mark.asyncio
    async def test_normal_3_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_share_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Create "Issue" event
        tx_hash_1 = ISSUE_TX_HASH_1
        tx_receipt_1 = add_event(
            token_address_1,
            "Issue",
            tx_hash_1,
            EVENT_BLOCK_NUMBER,
            issuer_address,
            40,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: Sequence[IDXIssueRedeem] = (
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
        assert event_0.block_timestamp == await _get_block_timestamp(tx_receipt_1)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number is not None
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_4_1
    # "Redeem" event has been emitted
    # Bond
    @pytest.mark.asyncio
    async def test_normal_4_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Create "Redeem" event
        tx_hash_1 = REDEEM_TX_HASH
        tx_receipt_1 = add_event(
            token_address_1,
            "Redeem",
            tx_hash_1,
            EVENT_BLOCK_NUMBER,
            issuer_address,
            10,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: Sequence[IDXIssueRedeem] = (
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
        assert event_0.block_timestamp == await _get_block_timestamp(tx_receipt_1)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number is not None
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_4_2
    # "Redeem" event has been emitted
    # Share
    @pytest.mark.asyncio
    async def test_normal_4_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_share_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Create "Redeem" event
        tx_hash_1 = REDEEM_TX_HASH
        tx_receipt_1 = add_event(
            token_address_1,
            "Redeem",
            tx_hash_1,
            EVENT_BLOCK_NUMBER,
            issuer_address,
            10,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: Sequence[IDXIssueRedeem] = (
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
        assert event_0.block_timestamp == await _get_block_timestamp(tx_receipt_1)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number is not None
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_5
    # Multiple events have been emitted
    @pytest.mark.asyncio
    async def test_normal_5(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Create "Issue" events
        tx_hash_1 = ISSUE_TX_HASH_1
        tx_receipt_1 = add_event(
            token_address_1,
            "Issue",
            tx_hash_1,
            EVENT_BLOCK_NUMBER,
            issuer_address,
            10,
        )
        tx_hash_2 = ISSUE_TX_HASH_2
        tx_receipt_2 = add_event(
            token_address_1,
            "Issue",
            tx_hash_2,
            EVENT_BLOCK_NUMBER + 1,
            issuer_address,
            20,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        event_list: Sequence[IDXIssueRedeem] = (
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
        assert event_0.block_timestamp == await _get_block_timestamp(tx_receipt_1)

        event_1 = event_list[1]
        assert event_1.id == 2
        assert event_1.event_type == IDXIssueRedeemEventType.ISSUE
        assert event_1.transaction_hash == tx_hash_2
        assert event_1.token_address == token_address_1
        assert event_1.locked_address == ZERO_ADDRESS
        assert event_1.target_address == issuer_address
        assert event_1.amount == 20
        assert event_1.block_timestamp == await _get_block_timestamp(tx_receipt_2)

        idx_block_number = (
            await async_db.scalars(select(IDXIssueRedeemBlockNumber).limit(1))
        ).first()
        assert idx_block_number is not None
        assert idx_block_number.id == 1
        assert idx_block_number.latest_block_number == block_number

    # Normal_6
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip process".
    @pytest.mark.asyncio
    async def test_normal_6(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
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
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        assert len(processor.token_list.keys()) == 1

        # Prepare additional token
        token_contract_2 = await create_fake_share_token_contract()

        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
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
        main_func,  # type: ignore
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract()

        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Run mainloop once and fail with web3 utils error
        with (
            patch("batch.indexer_issue_redeem.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                indexer_issue_redeem.web3.eth,
                "contract",
                side_effect=ServiceUnavailableError(),
            ),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.ERROR, "All blockchain nodes are unavailable: ")
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
