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
import uuid
from collections.abc import Generator, Sequence
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import Contract
from web3.types import TxReceipt

import batch.indexer_token_holders as indexer_token_holders
from app.model.db import (
    Token,
    TokenHolder,
    TokenHolderBatchStatus,
    TokenHoldersList,
    TokenType,
    TokenVersion,
)
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch.indexer_token_holders import LOG, Processor, main
from config import ZERO_ADDRESS
from tests.account_config import default_eth_account

PERSONAL_INFO_ADDRESS = to_checksum_address("0x" + "08" * 20)
EXCHANGE_ADDRESS = to_checksum_address("0x" + "09" * 20)
ESCROW_ADDRESS = to_checksum_address("0x" + "0a" * 20)


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

    async def get_code(self, address: str) -> HexBytes:
        if address in _CONTRACT_ADDRESSES:
            return HexBytes("0xdeadbeef")
        return HexBytes("0x")


class FakeAsyncWeb3:
    def __init__(self, chain: FakeChain) -> None:
        self.eth = FakeAsyncEth(chain)


class FakeSyncEth:
    def __init__(self, chain: FakeChain) -> None:
        self.chain = chain

    @property
    def block_number(self) -> int:
        return self.chain.latest_block


class FakeSyncWeb3:
    def __init__(self, chain: FakeChain) -> None:
        self.eth = FakeSyncEth(chain)


_CHAIN = FakeChain()
web3 = FakeSyncWeb3(_CHAIN)
_EVENTS: dict[tuple[str, str], list[dict[str, Any]]] = {}
_TOKEN_EXCHANGES: dict[str, str] = {}
_CONTRACT_ADDRESSES = {EXCHANGE_ADDRESS, ESCROW_ADDRESS}
_token_counter = 0


def get_events(
    contract_address: str,
    event_name: str,
    block_from: int,
    block_to: int,
    argument_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    events = [
        event
        for event in _EVENTS.get((contract_address, event_name), [])
        if block_from <= event["blockNumber"] <= block_to
    ]
    if not argument_filters:
        return events
    return [
        event
        for event in events
        if all(
            event["args"].get(key) == value for key, value in argument_filters.items()
        )
    ]


def add_event(
    contract_address: str,
    event_name: str,
    args: dict[str, Any],
    log_index: int = 0,
) -> tuple[str, TxReceipt]:
    block_number = _CHAIN.mine()
    transaction_hash = f"0x{_CHAIN.transaction_index:064x}"
    _EVENTS.setdefault((contract_address, event_name), []).append(
        {
            "event": event_name,
            "transactionHash": HexBytes(transaction_hash),
            "blockNumber": block_number,
            "logIndex": log_index,
            "args": args,
        }
    )
    return transaction_hash, cast(TxReceipt, {"blockNumber": block_number})


def record_token_event(
    token_address: str,
    event_name: str,
    args: dict[str, Any],
    log_index: int = 0,
) -> tuple[str, TxReceipt]:
    return add_event(token_address, event_name, args, log_index)


def record_exchange_event(
    exchange_address: str,
    event_name: str,
    token_address: str,
    from_address: str,
    to_address: str,
    amount: int,
    log_index: int = 0,
) -> tuple[str, TxReceipt]:
    return add_event(
        exchange_address,
        event_name,
        {
            "token": token_address,
            "from": from_address,
            "to": to_address,
            "value": amount,
        },
        log_index,
    )


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
def processor(async_db: AsyncSession) -> Generator[Processor, None, None]:
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
    _TOKEN_EXCHANGES.clear()
    _CONTRACT_ADDRESSES.clear()
    _CONTRACT_ADDRESSES.update({EXCHANGE_ADDRESS, ESCROW_ADDRESS})

    monkeypatch.setattr(indexer_token_holders, "web3", FakeAsyncWeb3(_CHAIN))

    async def get_event_logs(
        contract: FakeContract,
        event: str,
        block_from: int,
        block_to: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return get_events(
            contract.address,
            event,
            block_from,
            block_to,
            kwargs.get("argument_filters"),
        )

    async def get_token(self: Any):
        self.tradable_exchange_contract_address = _TOKEN_EXCHANGES.get(
            self.token_address, ZERO_ADDRESS
        )
        return self

    def get_contract(contract_name: str, contract_address: str) -> FakeContract:
        return FakeContract(to_checksum_address(contract_address))

    monkeypatch.setattr(AsyncContractUtils, "get_event_logs", get_event_logs)
    monkeypatch.setattr(AsyncContractUtils, "get_contract", get_contract)
    monkeypatch.setattr(IbetStraightBondContract, "get", get_token)
    monkeypatch.setattr(IbetShareContract, "get", get_token)


@pytest.fixture(scope="function")
def ibet_exchange_contract() -> FakeContract:
    return FakeContract(EXCHANGE_ADDRESS)


@pytest.fixture(scope="function")
def ibet_security_token_escrow_contract() -> FakeContract:
    return FakeContract(ESCROW_ADDRESS)


async def create_fake_bond_token_contract(
    tradable_exchange_contract_address: str | None = None,
) -> FakeContract:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x700 + _token_counter:040x}")
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    return FakeContract(token_address)


async def create_fake_share_token_contract(
    tradable_exchange_contract_address: str | None = None,
) -> FakeContract:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x800 + _token_counter:040x}")
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    return FakeContract(token_address)


def token_holders_list(
    token_address: str,
    block_number: int,
    list_id: str,
    status: TokenHolderBatchStatus = TokenHolderBatchStatus.PENDING,
) -> TokenHoldersList:
    target_token_holders_list = TokenHoldersList()
    target_token_holders_list.list_id = list_id
    target_token_holders_list.token_address = token_address
    target_token_holders_list.batch_status = status
    target_token_holders_list.block_number = block_number
    return target_token_holders_list


async def _get_token_holder(
    async_db: AsyncSession, holder_list_id: int | None, account_address: str
) -> TokenHolder | None:
    return (
        await async_db.scalars(
            select(TokenHolder)
            .where(
                and_(
                    TokenHolder.holder_list_id == holder_list_id,
                    TokenHolder.account_address == account_address,
                )
            )
            .limit(1)
        )
    ).first()


async def _get_token_holders(
    async_db: AsyncSession, holder_list_id: int | None
) -> Sequence[TokenHolder]:
    return (
        await async_db.scalars(
            select(TokenHolder).where(TokenHolder.holder_list_id == holder_list_id)
        )
    ).all()


async def _get_token_holders_list_record(
    async_db: AsyncSession, holder_list_id: int | None
) -> TokenHoldersList | None:
    return (
        await async_db.scalars(
            select(TokenHoldersList)
            .where(TokenHoldersList.id == holder_list_id)
            .limit(1)
        )
    ).first()


async def _get_failed_token_holders_lists(
    async_db: AsyncSession,
) -> Sequence[TokenHoldersList]:
    return (
        await async_db.scalars(
            select(TokenHoldersList).where(
                TokenHoldersList.batch_status == TokenHolderBatchStatus.FAILED.value
            )
        )
    ).all()


class TestProcessor:
    account_list = [
        {
            "address": default_eth_account("user1")["address"],
            "keyfile": default_eth_account("user1")["keyfile_json"],
        },
        {
            "address": default_eth_account("user2")["address"],
            "keyfile": default_eth_account("user2")["keyfile_json"],
        },
        {
            "address": default_eth_account("user3")["address"],
            "keyfile": default_eth_account("user3")["keyfile_json"],
        },
        {
            "address": default_eth_account("user4")["address"],
            "keyfile": default_eth_account("user4")["keyfile_json"],
        },
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # StraightBond
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    # - Lock
    @pytest.mark.asyncio
    async def test_normal_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": exchange_contract.address, "value": 10000},
        )
        # user1: 30000 user2: 10000

        # Record Exchange events
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_1,
            10000,
        )
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_1,
            10000,
        )
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            10000,
        )
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_1,
            4000,
        )
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            4000,
        )

        # Record Issue, Redeem, and Lock events
        record_token_event(
            token_address_1,
            "Issue",
            {
                "targetAddress": issuer_address,
                "lockAddress": ZERO_ADDRESS,
                "amount": 40000,
            },
        )
        record_token_event(
            token_address_1,
            "Redeem",
            {
                "targetAddress": user_address_2,
                "lockAddress": ZERO_ADDRESS,
                "amount": 10000,
            },
        )
        record_token_event(
            token_address_1,
            "Issue",
            {
                "targetAddress": user_address_2,
                "lockAddress": ZERO_ADDRESS,
                "amount": 30000,
            },
        )
        record_token_event(
            token_address_1,
            "Redeem",
            {
                "targetAddress": issuer_address,
                "lockAddress": ZERO_ADDRESS,
                "amount": 10000,
            },
        )
        record_token_event(
            token_address_1,
            "Lock",
            {"accountAddress": user_address_1, "value": 3000},
        )
        # user1: (hold: 13000, locked: 3000) user2: 44000

        # Issuer issues other token to create exchange event
        other_token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            other_token_contract.address,
            user_address_1,
            user_address_2,
            10000,
        )

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.commit()
        token_holders_list_id = _token_holders_list.id

        # Then execute processor.
        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_2
        )
        assert user1_record is not None
        assert user2_record is not None

        assert user1_record.hold_balance == 13000
        assert user1_record.locked_balance == 3000
        assert user2_record.hold_balance == 44000
        assert user2_record.locked_balance == 0

        assert len(await _get_token_holders(async_db, token_holders_list_id)) == 2

    # <Normal_2>
    # StraightBond
    # Events
    # - ApplyForTransfer
    # - CancelForTransfer
    # - ApproveTransfer
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    #   - ApproveTransfer
    # - Lock
    # - ForceLock
    # - Unlock
    # - ForceUnlock
    # - ForceChangeLockedAccount
    @pytest.mark.asyncio
    async def test_normal_2(
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

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": ibet_security_token_escrow_contract.address,
                "value": 10000,
            },
        )
        # user1: 20000 user2: 0

        # Record additional Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        # user1: 20000 user2: 10000

        # Record Exchange events
        record_exchange_event(
            ibet_security_token_escrow_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            7000,
        )
        # user1: 13000 user2: 17000

        # Record Lock, ForceLock, Unlock, ForceUnlock, and ForceChangeLockedAccount events
        record_token_event(
            token_address_1,
            "Lock",
            {"accountAddress": user_address_1, "value": 2000},
        )
        record_token_event(
            token_address_1,
            "ForceLock",
            {"accountAddress": user_address_1, "value": 2000},
        )
        record_token_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": user_address_2,
                "value": 1500,
            },
        )
        record_token_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": user_address_2,
                "value": 1500,
            },
        )
        record_token_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "beforeAccountAddress": user_address_1,
                "afterAccountAddress": user_address_2,
                "value": 500,
            },
        )
        # user1: 13000 user2: 17000

        # user1: 9000 user2: 20000
        # user1(locked): 500, user2(locked): 500

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.commit()
        token_holders_list_id = _token_holders_list.id

        # Then execute processor.
        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_2
        )
        assert user1_record is not None
        assert user2_record is not None

        assert user1_record.hold_balance == 9000
        assert user1_record.locked_balance == 500
        assert user2_record.hold_balance == 20000
        assert user2_record.locked_balance == 500

        assert len(await _get_token_holders(async_db, token_holders_list_id)) == 2

    # <Normal_3>
    # StraightBond
    # Events
    # - ApplyForTransfer - pending
    # - Escrow - pending
    @pytest.mark.asyncio
    async def test_normal_3(
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

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": ibet_security_token_escrow_contract.address,
                "value": 10000,
            },
        )
        # user1: 20000 user2: 10000

        # Pending approval does not change holder balances.
        # user1: 20000 user2: 10000

        # Record Exchange events
        record_exchange_event(
            ibet_security_token_escrow_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            3000,
        )
        # user1: 17000 user2: 13000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.commit()
        token_holders_list_id = _token_holders_list.id

        # Then execute processor.
        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_2
        )
        assert user1_record is not None
        assert user2_record is not None

        assert user1_record.hold_balance == 17000
        assert user1_record.locked_balance == 0
        assert user2_record.hold_balance == 13000
        assert user2_record.locked_balance == 0

        assert len(await _get_token_holders(async_db, token_holders_list_id)) == 2

    # <Normal_4>
    # Share
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    # - Lock
    @pytest.mark.asyncio
    async def test_normal_4(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Issuer issues share token.
        token_contract = await create_fake_share_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": exchange_contract.address, "value": 10000},
        )
        # user1: 20000 user2: 10000

        # Record Exchange events
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_1,
            10000,
        )
        # user1: 20000 user2: 10000

        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_1,
            10000,
        )
        # user1: 20000 user2: 10000

        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            10000,
        )
        # user1: 10000 user2: 20000

        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_1,
            4000,
        )
        # user1: 10000 user2: 20000

        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            4000,
        )
        # user1: 6000 user2: 24000

        # Record Issue and Redeem events
        record_token_event(
            token_address_1,
            "Issue",
            {
                "targetAddress": issuer_address,
                "lockAddress": ZERO_ADDRESS,
                "amount": 40000,
            },
        )
        record_token_event(
            token_address_1,
            "Redeem",
            {
                "targetAddress": user_address_2,
                "lockAddress": ZERO_ADDRESS,
                "amount": 10000,
            },
        )
        # user1: 6000 user2: 14000

        record_token_event(
            token_address_1,
            "Issue",
            {
                "targetAddress": user_address_2,
                "lockAddress": ZERO_ADDRESS,
                "amount": 30000,
            },
        )
        record_token_event(
            token_address_1,
            "Redeem",
            {
                "targetAddress": issuer_address,
                "lockAddress": ZERO_ADDRESS,
                "amount": 10000,
            },
        )
        # user1: 6000 user2: 44000

        # Record Lock event
        record_token_event(
            token_address_1,
            "Lock",
            {"accountAddress": user_address_1, "value": 3000},
        )
        # user1: (hold: 3000, locked: 3000) user2: 44000

        # Issuer issues other token to create exchange event
        other_token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        record_exchange_event(
            exchange_contract.address,
            "HolderChanged",
            other_token_contract.address,
            user_address_1,
            user_address_2,
            10000,
        )

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.commit()
        token_holders_list_id = _token_holders_list.id

        # Then execute processor.
        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_2
        )
        assert user1_record is not None
        assert user2_record is not None

        assert user1_record.hold_balance == 3000
        assert user1_record.locked_balance == 3000
        assert user2_record.hold_balance == 44000
        assert user2_record.locked_balance == 0

        assert len(await _get_token_holders(async_db, token_holders_list_id)) == 2

    # <Normal_5>
    # Share
    # Events
    # - ApplyForTransfer
    # - CancelForTransfer
    # - ApproveTransfer
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    #   - ApproveTransfer
    # - Lock
    # - ForceLock
    # - Unlock
    # - ForceUnlock
    # - ForceChangeLockedAccount
    @pytest.mark.asyncio
    async def test_normal_5(
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

        # Issuer issues share token.
        token_contract = await create_fake_share_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": ibet_security_token_escrow_contract.address,
                "value": 10000,
            },
        )
        # user1: 20000 user2: 0

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        # user1: 20000 user2: 10000

        # Record Exchange events
        record_exchange_event(
            ibet_security_token_escrow_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            7000,
        )
        # user1: 13000 user2: 17000

        # Record Lock, ForceLock, Unlock, ForceUnlock, and ForceChangeLockedAccount events
        record_token_event(
            token_address_1,
            "Lock",
            {"accountAddress": user_address_1, "value": 2000},
        )
        record_token_event(
            token_address_1,
            "ForceLock",
            {"accountAddress": user_address_1, "value": 2000},
        )
        record_token_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": user_address_2,
                "value": 1500,
            },
        )
        record_token_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": user_address_2,
                "value": 1500,
            },
        )
        record_token_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "beforeAccountAddress": user_address_1,
                "afterAccountAddress": user_address_2,
                "value": 500,
            },
        )
        # user1: 13000 user2: 17000

        # user1: 9000, user2: 20000
        # user1(locked): 500, user2(locked): 500

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.commit()
        token_holders_list_id = _token_holders_list.id

        # Then execute processor.
        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_2
        )
        assert user1_record is not None
        assert user2_record is not None

        assert user1_record.hold_balance == 9000
        assert user1_record.locked_balance == 500
        assert user2_record.hold_balance == 20000
        assert user2_record.locked_balance == 500

        assert len(await _get_token_holders(async_db, token_holders_list_id)) == 2

    # <Normal_6>
    # Share
    # Events
    # - ApplyForTransfer - pending
    # - Escrow - pending
    @pytest.mark.asyncio
    async def test_normal_6(
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

        # Issuer issues share token.
        token_contract = await create_fake_share_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": ibet_security_token_escrow_contract.address,
                "value": 10000,
            },
        )
        # user1: 20000 user2: 10000

        # Pending approval does not change holder balances.
        # user1: 20000 user2: 10000

        # Record Exchange events
        record_exchange_event(
            ibet_security_token_escrow_contract.address,
            "HolderChanged",
            token_address_1,
            user_address_1,
            user_address_2,
            3000,
        )
        # user1: 17000 user2: 13000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.commit()
        token_holders_list_id = _token_holders_list.id

        # Then execute processor.
        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_2
        )
        assert user1_record is not None
        assert user2_record is not None

        assert user1_record.hold_balance == 17000
        assert user1_record.locked_balance == 0
        assert user2_record.hold_balance == 13000
        assert user2_record.locked_balance == 0

        assert len(await _get_token_holders(async_db, token_holders_list_id)) == 2

    # <Normal_7>
    # StraightBond
    # Jobs are queued and pending jobs are to be processed one by one.
    @pytest.mark.asyncio
    async def test_normal_7(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        exchange_contract = ibet_exchange_contract
        await processor.collect()
        async_db.expire_all()

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "There are no pending collect batch")
        )

        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list1 = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list1)
        await async_db.commit()
        token_holders_list1_id = _token_holders_list1.list_id

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": exchange_contract.address, "value": 10000},
        )

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list2 = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list2)
        await async_db.commit()

        await processor.collect()
        async_db.expire_all()

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                f"Token holder list({token_holders_list1_id}) status changes to be done.",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "Collect job has been completed")
        )

    # <Normal_8>
    # StraightBond
    # Indexer uses checkpoint if there is stored data.
    @pytest.mark.asyncio
    async def test_normal_8(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        exchange_contract = ibet_exchange_contract

        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": exchange_contract.address, "value": 10000},
        )

        # Record Lock event
        record_token_event(
            token_address_1,
            "Lock",
            {"accountAddress": user_address_1, "value": 10000},
        )

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list1 = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list1)
        await async_db.commit()
        token_holders_list1_id = _token_holders_list1.id

        await processor.collect()
        async_db.expire_all()

        # Record Unlock event
        record_token_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": user_address_2,
                "value": 10000,
            },
        )
        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 20000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": exchange_contract.address, "value": 10000},
        )

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list2 = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list2)
        await async_db.commit()
        token_holders_list2_id = _token_holders_list2.id

        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list2_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list2_id, user_address_2
        )
        assert user1_record is not None
        assert user2_record is not None

        assert user1_record.hold_balance == 30000
        assert user1_record.locked_balance == 0
        assert user2_record.hold_balance == 30000
        assert user2_record.locked_balance == 0

        assert len(await _get_token_holders(async_db, token_holders_list1_id)) == 2
        assert len(await _get_token_holders(async_db, token_holders_list1_id)) == 2

    # <Normal_9>
    # StraightBond
    # Batch does not index former holder who has no balance at the target block number.
    @pytest.mark.asyncio
    async def test_normal_9(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
    ):
        exchange_contract = ibet_exchange_contract
        _user_1 = default_eth_account("user1")
        issuer_address = _user_1["address"]
        _user_2 = default_eth_account("user2")
        user_address_1 = _user_2["address"]
        _user_3 = default_eth_account("user3")
        user_address_2 = _user_3["address"]

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Record Transfer events
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": user_address_1, "to": issuer_address, "value": 30000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 30000},
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": user_address_2, "to": issuer_address, "value": 30000},
        )
        # user1: 0 user2: 0

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.flush()
        token_holders_list_id = _token_holders_list.id

        former_holder = TokenHolder()
        former_holder.holder_list_id = _token_holders_list.id
        former_holder.hold_balance = 0
        former_holder.locked_balance = 0
        former_holder.account_address = "former holder"
        async_db.add(former_holder)

        await async_db.commit()

        # Then execute processor.
        await processor.collect()
        async_db.expire_all()

        user1_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_1
        )
        user2_record = await _get_token_holder(
            async_db, token_holders_list_id, user_address_2
        )

        assert user1_record is None
        assert user2_record is None

        assert len(await _get_token_holders(async_db, token_holders_list_id)) == 0

    # <Normal_10>
    # When stored checkpoint is 9,999,999 and current block number is 19,999,999,
    # then processor should call "__process_all" method 10 times.
    @pytest.mark.asyncio
    async def test_normal_10(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        exchange_contract = ibet_exchange_contract
        current_block_number = 20000000 - 1
        checkpoint_block_number = 10000000 - 1

        _user_1 = default_eth_account("user1")
        issuer_address = _user_1["address"]

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Insert collection record with above token and checkpoint block number
        target_list_id = str(uuid.uuid4())
        target_holders_list = token_holders_list(
            token_contract.address, current_block_number, target_list_id
        )
        async_db.add(target_holders_list)
        completed_list_id = str(uuid.uuid4())
        completed_holders_list = token_holders_list(
            token_contract.address,
            checkpoint_block_number,
            completed_list_id,
            status=TokenHolderBatchStatus.DONE,
        )
        async_db.add(completed_holders_list)
        await async_db.commit()
        target_holders_list_id = target_holders_list.id

        # Setting stored index to 9,999,999
        await processor.collect()
        async_db.expire_all()

        # Then processor call "__process_all" method 10 times.
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=10000000, to=10999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=11000000, to=11999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=12000000, to=12999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=13000000, to=13999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=14000000, to=14999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=15000000, to=15999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=16000000, to=16999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=17000000, to=17999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=18000000, to=18999999")
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "syncing from=19000000, to=19999999")
        )

        processed_list = await _get_token_holders_list_record(
            async_db, target_holders_list_id
        )
        assert processed_list is not None
        assert processed_list.block_number == 19999999
        assert processed_list.batch_status == TokenHolderBatchStatus.DONE.value

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # There is no target token holders list id with batch_status PENDING.
    @pytest.mark.asyncio
    async def test_error_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        await processor.collect()
        async_db.expire_all()

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "There are no pending collect batch")
        )

    # <Error_2>
    # There is target token holders list id with batch_status PENDING.
    # And target token is not contained in "TokenList" contract.
    @pytest.mark.asyncio
    async def test_error_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        # Insert collection definition with token address Zero
        target_token_holders_list_id = str(uuid.uuid4())
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = ZERO_ADDRESS
        target_token_holders_list.list_id = target_token_holders_list_id
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING
        target_token_holders_list.block_number = 1000
        async_db.add(target_token_holders_list)
        await async_db.commit()

        # Debug message should be shown that points out token contract must be listed.
        await processor.collect()
        async_db.expire_all()

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.DEBUG,
                "Token contract must be listed to TokenList contract.",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                f"Token holder list({target_token_holders_list_id}) status changes to be failed.",
            )
        )

        # Batch status of token holders list expects to be "ERROR"
        error_record_num = len(await _get_failed_token_holders_lists(async_db))
        assert error_record_num == 1

    # <Error_3>
    # Failed to get Logs from blockchain.
    @pytest.mark.asyncio
    async def test_error_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Issuer issues bond token.
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=exchange_contract.address,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.block_number
        _token_holders_list = token_holders_list(
            token_contract.address, block_number, list_id
        )
        async_db.add(_token_holders_list)
        await async_db.commit()
        token_holders_list_id = _token_holders_list.id

        mock_lib = MagicMock()
        with patch.object(
            Processor, "_Processor__process_all", return_value=mock_lib
        ) as __sync_all_mock:
            # Then execute processor.
            __sync_all_mock.return_value = None
            await processor.collect()
            async_db.expire_all()

            _records = await _get_token_holders(async_db, token_holders_list_id)
            assert len(_records) == 0
