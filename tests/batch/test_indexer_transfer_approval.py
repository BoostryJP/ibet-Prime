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
from typing import Any, cast
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import Contract
from web3.types import TxReceipt

import batch.indexer_transfer_approval as indexer_transfer_approval
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    Account,
    AccountRsaStatus,
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber,
    Notification,
    NotificationType,
    Token,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch.indexer_transfer_approval import LOG, Processor, main
from config import ZERO_ADDRESS
from tests.account_config import default_eth_account


class FakeChain:
    def __init__(self) -> None:
        self.latest_block = 100
        self.transaction_index = 0

    def mine(self) -> int:
        self.latest_block += 1
        self.transaction_index += 1
        return self.latest_block


class FakeContract:
    def __init__(self, address: str) -> None:
        self.address = address
        self.abi: dict[str, Any] = {}
        self.events = MagicMock()


class FakeAsyncEth:
    def __init__(self, chain: FakeChain) -> None:
        self.chain = chain

    @property
    def block_number(self):
        return self._get_block_number()

    async def _get_block_number(self) -> int:
        return self.chain.latest_block

    def contract(self, address: str, abi: Any) -> FakeContract:
        return FakeContract(address)

    async def get_block(self, block_number: int) -> dict[str, int]:
        return {"timestamp": 1_700_000_000 + block_number}

    async def get_transaction(self, transaction_hash: str) -> dict[str, str]:
        return {"from": _TRANSACTIONS[str(transaction_hash)]}


class FakeAsyncWeb3:
    def __init__(self, chain: FakeChain) -> None:
        self.eth = FakeAsyncEth(chain)


class FakeSyncEth:
    def __init__(self, chain: FakeChain) -> None:
        self.chain = chain

    @property
    def block_number(self) -> int:
        return self.chain.latest_block

    def get_block(self, block_number: int) -> dict[str, int]:
        return {"timestamp": 1_700_000_000 + block_number}


class FakeSyncWeb3:
    def __init__(self, chain: FakeChain) -> None:
        self.eth = FakeSyncEth(chain)


_CHAIN = FakeChain()
web3 = FakeSyncWeb3(_CHAIN)
_EVENTS: dict[tuple[str, str], list[dict[str, Any]]] = {}
_TRANSACTIONS: dict[str, str] = {}
_TOKEN_EXCHANGES: dict[str, str] = {}
_token_counter = 0


def get_events(
    contract_address: str,
    event_name: str,
    block_from: int,
    block_to: int,
) -> list[dict[str, Any]]:
    return [
        event
        for event in _EVENTS.get((contract_address, event_name), [])
        if block_from <= event["blockNumber"] <= block_to
    ]


def add_event(
    contract_address: str,
    event_name: str,
    transaction_hash: str,
    block_number: int,
    args: dict[str, Any],
) -> None:
    _EVENTS.setdefault((contract_address, event_name), []).append(
        {
            "event": event_name,
            "transactionHash": HexBytes(transaction_hash),
            "blockNumber": block_number,
            "args": args,
        }
    )


def _record_event_transaction(sender: str) -> tuple[str, TxReceipt]:
    block_number = _CHAIN.mine()
    transaction_hash = f"0x{_CHAIN.transaction_index:064x}"
    _TRANSACTIONS[transaction_hash] = sender
    return transaction_hash, cast(TxReceipt, {"blockNumber": block_number})


def record_token_approval_event(
    token_address: str,
    event_name: str,
    sender: str,
    application_id: int,
    from_address: str,
    to_address: str,
    amount: int | None = None,
    data: str | None = None,
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction(sender)
    args: dict[str, Any] = {
        "index": application_id,
        "from": from_address,
        "to": to_address,
    }
    if amount is not None:
        args["value"] = amount
    if data is not None:
        args["data"] = data
    add_event(
        token_address,
        event_name,
        transaction_hash,
        int(receipt["blockNumber"]),
        args,
    )
    return transaction_hash, receipt


def record_escrow_approval_event(
    exchange_address: str,
    event_name: str,
    sender: str,
    escrow_id: int,
    token_address: str,
    from_address: str,
    to_address: str,
    amount: int,
    data: str = "",
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction(sender)
    args: dict[str, Any] = {
        "escrowId": escrow_id,
        "token": token_address,
        "from": from_address,
        "to": to_address,
        "value": amount,
        "data": data,
    }
    if event_name == "EscrowFinished":
        args = {
            "escrowId": escrow_id,
            "token": token_address,
            "sender": from_address,
            "recipient": to_address,
        }
    add_event(
        exchange_address,
        event_name,
        transaction_hash,
        int(receipt["blockNumber"]),
        args,
    )
    return transaction_hash, receipt


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
    global _token_counter
    _CHAIN.latest_block = 100
    _CHAIN.transaction_index = 0
    _token_counter = 0
    _EVENTS.clear()
    _TRANSACTIONS.clear()
    _TOKEN_EXCHANGES.clear()

    monkeypatch.setattr(indexer_transfer_approval, "web3", FakeAsyncWeb3(_CHAIN))

    async def get_event_logs(
        contract: Any,
        event: str,
        block_from: int,
        block_to: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return get_events(contract.address, event, block_from, block_to)

    async def get_token(self: Any):
        self.tradable_exchange_contract_address = _TOKEN_EXCHANGES.get(
            self.token_address, ZERO_ADDRESS
        )
        return self

    monkeypatch.setattr(AsyncContractUtils, "get_event_logs", get_event_logs)
    monkeypatch.setattr(IbetStraightBondContract, "get", get_token)
    monkeypatch.setattr(IbetShareContract, "get", get_token)


@pytest.fixture(scope="function")
def ibet_security_token_escrow_contract() -> FakeContract:
    return FakeContract(to_checksum_address("0x" + "0b" * 20))


async def create_fake_bond_token_contract(
    tradable_exchange_contract_address: str | None = None,
):
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x800 + _token_counter:040x}")
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    return FakeContract(token_address)


async def create_fake_share_token_contract(
    tradable_exchange_contract_address: str | None = None,
):
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x800 + _token_counter:040x}")
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    return FakeContract(token_address)


def _get_block_number(tx_receipt: TxReceipt) -> int:
    block_number = tx_receipt.get("blockNumber")
    assert block_number is not None
    return block_number


def _get_block_timestamp(tx_receipt: TxReceipt) -> datetime:
    block = web3.eth.get_block(_get_block_number(tx_receipt))
    timestamp = block.get("timestamp")
    assert timestamp is not None
    return datetime.fromtimestamp(timestamp, UTC).replace(tzinfo=None)


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # No event log
    #   - Token not yet issued
    @pytest.mark.asyncio
    async def test_normal_1_1(
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
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # No event log
    #   - Issued tokens but no events have occurred.
    @pytest.mark.asyncio
    async def test_normal_1_2(
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

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = TokenStatus.PENDING
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Event log
    #   - ibetSecurityToken: ApplyForTransfer
    # -> One notification
    @pytest.mark.asyncio
    async def test_normal_2_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

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

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = TokenStatus.PENDING
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Record token approval event
        _, tx_receipt_1 = record_token_approval_event(
            token_address_1,
            "ApplyForTransfer",
            user_address_1,
            0,
            user_address_1,
            issuer_address,
            30,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_1
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_2_1>
    # Event log
    #   - ibetSecurityToken: CancelTransfer
    # Cancel from issuer
    #   -> No notification
    @pytest.mark.asyncio
    async def test_normal_2_2_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Record token approval events
        _, tx_receipt_2 = record_token_approval_event(
            token_address_1,
            "ApplyForTransfer",
            user_address_1,
            0,
            user_address_1,
            issuer_address,
            30,
        )
        _, tx_receipt_3 = record_token_approval_event(
            token_address_1,
            "CancelTransfer",
            issuer_address,
            0,
            user_address_1,
            issuer_address,
            30,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        await async_db.commit()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_2
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp == _get_block_timestamp(
            tx_receipt_3
        )
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_2_2>
    # Event log
    #   - ibetSecurityToken: CancelTransfer
    # Cancel from applicant
    #   -> One notification
    @pytest.mark.asyncio
    async def test_normal_2_2_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Record token approval events
        _, tx_receipt_2 = record_token_approval_event(
            token_address_1,
            "ApplyForTransfer",
            user_address_1,
            0,
            user_address_1,
            issuer_address,
            30,
        )
        _, tx_receipt_3 = record_token_approval_event(
            token_address_1,
            "CancelTransfer",
            user_address_1,
            0,
            user_address_1,
            issuer_address,
            30,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        await async_db.commit()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_2
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp == _get_block_timestamp(
            tx_receipt_3
        )
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_3>
    # Event log
    #   - ibetSecurityToken: ApproveTransfer (from issuer)
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Record token approval events
        now = datetime.now(UTC).replace(tzinfo=None)
        _, tx_receipt_1 = record_token_approval_event(
            token_address_1,
            "ApplyForTransfer",
            user_address_1,
            0,
            user_address_1,
            issuer_address,
            30,
        )
        _, tx_receipt_2 = record_token_approval_event(
            token_address_1,
            "ApproveTransfer",
            issuer_address,
            0,
            user_address_1,
            issuer_address,
            30,
            str(now.timestamp()),
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_1
        )
        assert _transfer_approval.approval_datetime == now
        assert _transfer_approval.approval_blocktimestamp == _get_block_timestamp(
            tx_receipt_2
        )
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_4>
    # Event log
    #   - Exchange: ApplyForTransfer
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_4(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Record escrow approval event
        now = datetime.now(UTC).replace(tzinfo=None)
        _, tx_receipt_1 = record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "ApplyForTransfer",
            user_address_1,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
            str(now.timestamp()),
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime == now
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_1
        )
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_5>
    # Event log
    #   - Exchange: CancelTransfer
    # Cancel from applicant
    @pytest.mark.asyncio
    async def test_normal_2_5(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = TokenStatus.PENDING
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        checkpoint = IDXTransferApprovalBlockNumber()
        checkpoint.latest_block_number = 0
        async_db.add(checkpoint)
        await async_db.commit()

        # Record escrow approval events
        _, tx_receipt_1 = record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "ApplyForTransfer",
            user_address_1,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
        )
        _, tx_receipt_2 = record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "CancelTransfer",
            user_address_1,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_1
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp == _get_block_timestamp(
            tx_receipt_2
        )
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_6>
    # Single Token
    # Single event logs
    # - Exchange: EscrowFinished
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_6(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        checkpoint = IDXTransferApprovalBlockNumber()
        checkpoint.latest_block_number = 0
        async_db.add(checkpoint)
        await async_db.commit()

        # Record escrow approval events
        _, tx_receipt_1 = record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "ApplyForTransfer",
            user_address_1,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
        )
        record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "EscrowFinished",
            user_address_1,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
        )

        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_1
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 3
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_7>
    # Event logs
    #   - Exchange: ApproveTransfer
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_7(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Record escrow approval events
        _, tx_receipt_1 = record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "ApplyForTransfer",
            user_address_1,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
        )
        record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "EscrowFinished",
            user_address_1,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
        )
        _, tx_receipt_2 = record_escrow_approval_event(
            ibet_security_token_escrow_contract.address,
            "ApproveTransfer",
            issuer_address,
            1,
            token_address_1,
            user_address_1,
            user_address_2,
            30,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == _get_block_timestamp(
            tx_receipt_1
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp == _get_block_timestamp(
            tx_receipt_2
        )
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 3
        _notification = _notification_list[2]
        assert _notification.id == 3
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number is not None
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_3>
    # Newly tokens added
    @pytest.mark.asyncio
    async def test_normal_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address
        )
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_contract_1.address
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)
        await async_db.commit()

        await processor.sync_new_logs()
        async_db.expire_all()
        assert len(processor.token_list) == 1
        assert len(processor.exchange_list) == 1

        token_contract_2 = await create_fake_share_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address
        )
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = token_contract_2.address
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)
        await async_db.commit()

        await processor.sync_new_logs()
        async_db.expire_all()
        assert len(processor.token_list) == 2
        assert len(processor.exchange_list) == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
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
        token_contract = await create_fake_bond_token_contract()
        token_address = token_contract.address
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = token_address
        token.issuer_address = issuer_address
        token.abi = token_contract.abi
        token.tx_hash = "tx_hash"
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # Run mainloop once and fail with web3 utils error
        with (
            patch("batch.indexer_transfer_approval.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                indexer_transfer_approval.web3.eth,
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

        # Run mainloop once and fail with sqlalchemy Error
        with (
            patch("batch.indexer_transfer_approval.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                AsyncSession, "commit", side_effect=SQLAlchemyError(code="dbapi")
            ),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert "A database error has occurred: code=dbapi" in caplog.text
        caplog.clear()
