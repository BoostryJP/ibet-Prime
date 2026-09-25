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
from typing import Any, Iterator, cast
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.types import TxReceipt

import batch.indexer_transfer as indexer_transfer
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    Account,
    AccountRsaStatus,
    IDXTransfer,
    IDXTransferBlockNumber,
    IDXTransferSourceEventType,
    Token,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch.indexer_transfer import LOG, Processor, main
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
_TRANSACTIONS: dict[str, HexBytes] = {}
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
    log_index: int = 0,
) -> None:
    _EVENTS.setdefault((contract_address, event_name), []).append(
        {
            "event": event_name,
            "transactionHash": HexBytes(transaction_hash),
            "blockNumber": block_number,
            "logIndex": log_index,
            "args": args,
        }
    )


def _record_event_transaction(transaction_input: str = "") -> tuple[str, TxReceipt]:
    block_number = _CHAIN.mine()
    transaction_hash = f"0x{_CHAIN.transaction_index:064x}"
    _TRANSACTIONS[transaction_hash] = HexBytes("0x" + transaction_input)
    return transaction_hash, cast(TxReceipt, {"blockNumber": block_number})


def record_transfer_event(
    token_address: str,
    event_name: str,
    args: dict[str, Any],
    transaction_input: str = "",
    log_index: int = 0,
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction(transaction_input)
    add_event(
        token_address,
        event_name,
        transaction_hash,
        int(receipt["blockNumber"]),
        args,
        log_index,
    )
    return transaction_hash, receipt


def record_bulk_transfer_event(
    token_address: str,
    sender: str,
    recipient_list: list[str],
    amount_list: list[int],
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction()
    for log_index, (recipient, amount) in enumerate(
        zip(recipient_list, amount_list, strict=True)
    ):
        add_event(
            token_address,
            "Transfer",
            transaction_hash,
            int(receipt["blockNumber"]),
            {"from": sender, "to": recipient, "value": amount},
            log_index,
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
def processor(
    async_db: AsyncSession, caplog: pytest.LogCaptureFixture
) -> Iterator[Processor]:
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
    Fixture to mock blockchain interactions for testing.
    """
    global _token_counter
    _CHAIN.latest_block = 100
    _CHAIN.transaction_index = 0
    _token_counter = 0
    _EVENTS.clear()
    _TRANSACTIONS.clear()

    monkeypatch.setattr(indexer_transfer, "web3", FakeAsyncWeb3(_CHAIN))

    async def get_event_logs(
        contract: Any,
        event: str,
        block_from: int,
        block_to: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return get_events(contract.address, event, block_from, block_to)

    async def get_transaction(transaction_hash: str) -> dict[str, HexBytes]:
        return {"input": _TRANSACTIONS[transaction_hash]}

    monkeypatch.setattr(AsyncContractUtils, "get_event_logs", get_event_logs)
    monkeypatch.setattr(AsyncContractUtils, "get_transaction", get_transaction)


async def create_fake_bond_token_contract() -> FakeContract:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x700 + _token_counter:040x}")
    return FakeContract(token_address)


async def create_fake_share_token_contract() -> FakeContract:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x700 + _token_counter:040x}")
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
    # Single Token
    # No event logs
    # not issue token
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
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
        assert len(_transfer_list) == 0
        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # Single Token
    # No event logs
    # issued token
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
        _idx_transfer_block_number = IDXTransferBlockNumber()
        _idx_transfer_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_block_number)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
        assert len(_transfer_list) == 0

        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Single Token
    # Single event logs
    # - Transfer
    # - Unlock
    # - ForceUnlock
    # - ForceChangeLockedAccount
    # - Reallocation
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

        await async_db.commit()

        tx_hash_1, tx_receipt_1 = record_transfer_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
        )

        tx_hash_3, tx_receipt_3 = record_transfer_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"message": "garnishment"}),
            },
        )
        tx_hash_4, tx_receipt_4 = record_transfer_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 5,
                "data": json.dumps({"message": "force_unlock"}),
            },
        )
        tx_hash_5, tx_receipt_5 = record_transfer_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 5,
                "data": json.dumps({"message": "ibet_wst_bridge"}),
            },
        )

        tx_hash_6, tx_receipt_6 = record_transfer_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "beforeAccountAddress": issuer_address,
                "afterAccountAddress": user_address_1,
                "value": 5,
                "data": json.dumps({"message": "ibet_wst_bridge"}),
            },
        )

        marker = b"\xc0\xff\xee\x00"
        annotation_data = json.dumps(
            {"purpose": "Reallocation"}, separators=(",", ":")
        ).encode("utf-8")
        tx_hash_7, tx_receipt_7 = record_transfer_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 10},
            transaction_input=marker.hex() + annotation_data.hex(),
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
        assert len(_transfer_list) == 6

        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_1)

        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_7
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.REALLOCATION.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_7)

        _transfer = _transfer_list[2]
        assert _transfer.id == 3
        assert _transfer.transaction_hash == tx_hash_3
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert _transfer.data == {"message": "garnishment"}
        assert _transfer.message == "garnishment"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_3)

        _transfer = _transfer_list[3]
        assert _transfer.id == 4
        assert _transfer.transaction_hash == tx_hash_4
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 5
        assert _transfer.source_event == IDXTransferSourceEventType.FORCE_UNLOCK.value
        assert _transfer.data == {"message": "force_unlock"}
        assert _transfer.message == "force_unlock"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_4)

        _transfer = _transfer_list[4]
        assert _transfer.id == 5
        assert _transfer.transaction_hash == tx_hash_5
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 5
        assert _transfer.source_event == IDXTransferSourceEventType.FORCE_UNLOCK.value
        assert _transfer.data == {"message": "ibet_wst_bridge"}
        assert _transfer.message == "ibet_wst_bridge"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_5)

        _transfer = _transfer_list[5]
        assert _transfer.id == 6
        assert _transfer.transaction_hash == tx_hash_6
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 5
        assert (
            _transfer.source_event
            == IDXTransferSourceEventType.FORCE_CHANGE_LOCKED_ACCOUNT.value
        )
        assert _transfer.data == {"message": "ibet_wst_bridge"}
        assert _transfer.message == "ibet_wst_bridge"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_6)

        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_2_2>
    # Single Token
    # Single event logs
    # - Unlock: Transfer record is not registered because "from" and "to" are the same
    # - ForceUnlock: Transfer record is not registered because "from" and "to" are the same
    @pytest.mark.asyncio
    async def test_normal_2_2(
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

        await async_db.commit()

        record_transfer_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": issuer_address,
                "value": 10,
                "data": json.dumps({"message": "unlock"}),
            },
        )
        record_transfer_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": issuer_address,
                "value": 10,
                "data": json.dumps({"message": "force_unlock"}),
            },
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
        assert len(_transfer_list) == 0

        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_2_3>
    # Single Token
    # Single event logs
    # - Unlock: Transfer record is registered but the data attribute is set null because of invalid data schema
    # - ForceUnlock: Transfer record is registered but the data attribute is set null because of invalid data schema
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

        await async_db.commit()

        tx_hash_1, tx_receipt_1 = record_transfer_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
        )

        tx_hash_3, tx_receipt_3 = record_transfer_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 10,
                "data": "null",
            },
        )
        tx_hash_4, tx_receipt_4 = record_transfer_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"invalid_message": "invalid_value"}),
            },
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
        assert len(_transfer_list) == 3

        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_1)

        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_3
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert _transfer.data == {}
        assert _transfer.message is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_3)

        _transfer = _transfer_list[2]
        assert _transfer.id == 3
        assert _transfer.transaction_hash == tx_hash_4
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.FORCE_UNLOCK.value
        assert _transfer.data == {}
        assert _transfer.message is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_4)

        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_3_1>
    # Single Token
    # Multi event logs
    # - Transfer(twice)
    # - Unlock(twice)
    # - ForceUnlock(twice)
    # - ForceChangeLockedAccount(twice)
    @pytest.mark.asyncio
    async def test_normal_3_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
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

        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = TokenStatus.PENDING
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        await async_db.commit()

        tx_hash_1, tx_receipt_1 = record_transfer_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
        )
        tx_hash_2, tx_receipt_2 = record_transfer_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 20},
        )
        tx_hash_3, tx_receipt_3 = record_transfer_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"message": "garnishment"}),
            },
        )
        tx_hash_4, tx_receipt_4 = record_transfer_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"message": "inheritance"}),
            },
        )
        tx_hash_5, tx_receipt_5 = record_transfer_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"message": "force_unlock"}),
            },
        )
        tx_hash_6, tx_receipt_6 = record_transfer_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": issuer_address,
                "recipientAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"message": "force_unlock"}),
            },
        )
        tx_hash_7, tx_receipt_7 = record_transfer_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "beforeAccountAddress": issuer_address,
                "afterAccountAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"message": "ibet_wst_bridge"}),
            },
        )
        tx_hash_8, tx_receipt_8 = record_transfer_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "beforeAccountAddress": issuer_address,
                "afterAccountAddress": user_address_1,
                "value": 10,
                "data": json.dumps({"message": "ibet_wst_bridge"}),
            },
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
        assert len(_transfer_list) == 8

        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_1)

        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_2
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_2
        assert _transfer.amount == 20
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_2)

        _transfer = _transfer_list[2]
        assert _transfer.id == 3
        assert _transfer.transaction_hash == tx_hash_3
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert _transfer.data == {"message": "garnishment"}
        assert _transfer.message == "garnishment"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_3)

        _transfer = _transfer_list[3]
        assert _transfer.id == 4
        assert _transfer.transaction_hash == tx_hash_4
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.UNLOCK.value
        assert _transfer.data == {}
        assert _transfer.message is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_4)

        _transfer = _transfer_list[4]
        assert _transfer.id == 5
        assert _transfer.transaction_hash == tx_hash_5
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.FORCE_UNLOCK.value
        assert _transfer.data == {"message": "force_unlock"}
        assert _transfer.message == "force_unlock"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_5)

        _transfer = _transfer_list[5]
        assert _transfer.id == 6
        assert _transfer.transaction_hash == tx_hash_6
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert _transfer.source_event == IDXTransferSourceEventType.FORCE_UNLOCK.value
        assert _transfer.data == {"message": "force_unlock"}
        assert _transfer.message == "force_unlock"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_6)

        _transfer = _transfer_list[6]
        assert _transfer.id == 7
        assert _transfer.transaction_hash == tx_hash_7
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert (
            _transfer.source_event
            == IDXTransferSourceEventType.FORCE_CHANGE_LOCKED_ACCOUNT.value
        )
        assert _transfer.data == {"message": "ibet_wst_bridge"}
        assert _transfer.message == "ibet_wst_bridge"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_7)

        _transfer = _transfer_list[7]
        assert _transfer.id == 8
        assert _transfer.transaction_hash == tx_hash_8
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 10
        assert (
            _transfer.source_event
            == IDXTransferSourceEventType.FORCE_CHANGE_LOCKED_ACCOUNT.value
        )
        assert _transfer.data == {"message": "ibet_wst_bridge"}
        assert _transfer.message == "ibet_wst_bridge"
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_8)

        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_3_2>
    # Single Token
    # Multi event logs
    # - Transfer(BulkTransfer)
    @pytest.mark.asyncio
    async def test_normal_3_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        user_4 = default_eth_account("user3")
        user_address_3 = user_4["address"]

        user_5 = default_eth_account("user3")
        user_address_4 = user_5["address"]

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

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        # Record bulk transfer events
        address_list1 = [user_address_1, user_address_2, user_address_3]
        value_list1 = [10, 20, 30]
        tx_hash_1, tx_receipt_1 = record_bulk_transfer_event(
            token_address_1, issuer_address, address_list1, value_list1
        )

        address_list2 = [user_address_1, user_address_2, user_address_3, user_address_4]
        value_list2 = [1, 2, 3, 4]
        tx_hash_2, tx_receipt_2 = record_bulk_transfer_event(
            token_address_1, issuer_address, address_list2, value_list2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
        assert len(_transfer_list) == 7

        block_timestamp_1 = _get_block_timestamp(tx_receipt_1)
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
            assert _transfer.block_timestamp == block_timestamp_1

        block_timestamp_2 = _get_block_timestamp(tx_receipt_2)
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
            assert _transfer.block_timestamp == block_timestamp_2

        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_4>
    # Multi Token
    @pytest.mark.asyncio
    async def test_normal_4(
        self,
        processor: Processor,
        async_db: AsyncSession,
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

        # Prepare data : Token1
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

        # Prepare data : Token2
        token_contract_2 = await create_fake_bond_token_contract()

        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        await async_db.commit()

        tx_hash_1, tx_receipt_1 = record_transfer_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
        )
        tx_hash_2, tx_receipt_2 = record_transfer_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 30},
        )
        tx_hash_3, tx_receipt_3 = record_transfer_event(
            token_address_2,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
        )
        tx_hash_4, tx_receipt_4 = record_transfer_event(
            token_address_2,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 30},
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_list = (await async_db.scalars(select(IDXTransfer))).all()
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
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_1)
        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_2
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_2
        assert _transfer.amount == 30
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_2)

        _transfer = _transfer_list[2]
        assert _transfer.id == 3
        assert _transfer.transaction_hash == tx_hash_3
        assert _transfer.token_address == token_address_2
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_3)

        _transfer = _transfer_list[3]
        assert _transfer.id == 4
        assert _transfer.transaction_hash == tx_hash_4
        assert _transfer.token_address == token_address_2
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_2
        assert _transfer.amount == 30
        assert _transfer.source_event == IDXTransferSourceEventType.TRANSFER.value
        assert _transfer.data is None
        assert _transfer.block_timestamp == _get_block_timestamp(tx_receipt_4)

        _idx_transfer_block_number = (
            await async_db.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_block_number is not None
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_5>
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip process".
    @pytest.mark.asyncio
    @mock.patch("web3.eth.Eth.block_number", 100)
    async def test_normal_5(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        _idx_position_bond_block_number = IDXTransferBlockNumber()
        _idx_position_bond_block_number.id = 1
        _idx_position_bond_block_number.latest_block_number = 1000
        async_db.add(_idx_position_bond_block_number)
        await async_db.commit()

        await processor.sync_new_logs()
        async_db.expire_all()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "skip process")
        )

    # <Normal_6>
    # Newly tokens added
    @pytest.mark.asyncio
    async def test_normal_6(
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

        # Issuer issues bond token.
        token_contract1 = await create_fake_bond_token_contract()
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
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
        token_contract2 = await create_fake_share_token_contract()
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract2.abi
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
            patch("batch.indexer_transfer.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                indexer_transfer.web3.eth,
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
            patch("batch.indexer_transfer.INDEXER_SYNC_INTERVAL", None),
            patch.object(AsyncSession, "scalars", side_effect=InvalidRequestError()),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()
