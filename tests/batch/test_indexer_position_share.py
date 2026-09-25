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
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable, Generator, cast
from unittest.mock import MagicMock, patch

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import and_, select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import Contract
from web3.types import TxReceipt

import batch.indexer_position_share as indexer_position_share
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    Account,
    AccountRsaStatus,
    IDXLock,
    IDXLockedPosition,
    IDXPosition,
    IDXPositionShareBlockNumber,
    IDXUnlock,
    Notification,
    NotificationType,
    Token,
    TokenCache,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from app.model.ibet import (
    IbetExchangeInterface,
    IbetShareContract,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch.indexer_position_share import LOG, Processor, main
from config import (
    TOKEN_CACHE_TTL,
    ZERO_ADDRESS,
)
from tests.account_config import default_eth_account

PERSONAL_INFO_ADDRESS = to_checksum_address("0x" + "08" * 20)
EXCHANGE_ADDRESS = to_checksum_address("0x" + "09" * 20)
ESCROW_ADDRESS = to_checksum_address("0x" + "0a" * 20)
DVP_ADDRESS = to_checksum_address("0x" + "0b" * 20)


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

    async def get_code(self, address: str) -> HexBytes:
        return HexBytes("0xdeadbeef" if address in _CONTRACT_ADDRESSES else "0x")

    async def get_block(self, block_number: int) -> dict[str, int]:
        return {"timestamp": 1_700_000_000 + block_number}

    async def get_transaction(self, transaction_hash: HexBytes) -> dict[str, str]:
        transaction_key = HexBytes(transaction_hash).to_0x_hex()
        return {"from": _TRANSACTION_SENDERS[transaction_key]}


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
_TRANSACTION_SENDERS: dict[str, str] = {}
_CONTRACT_ADDRESSES = {EXCHANGE_ADDRESS, ESCROW_ADDRESS, DVP_ADDRESS}
_TOKEN_EXCHANGES: dict[str, str] = {}
_TOKEN_ISSUERS: dict[str, str] = {}
_BALANCES: dict[tuple[str, str], int] = {}
_PENDING_TRANSFERS: dict[tuple[str, str], int] = {}
_LOCKED_BALANCES: dict[tuple[str, str, str], int] = {}
_EXCHANGE_BALANCES: dict[tuple[str, str, str], int] = {}
_EXCHANGE_COMMITMENTS: dict[tuple[str, str, str], int] = {}
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


def _record_event_transaction(sender: str) -> tuple[str, TxReceipt]:
    block_number = _CHAIN.mine()
    transaction_hash = f"0x{_CHAIN.transaction_index:064x}"
    _TRANSACTION_SENDERS[transaction_hash] = sender
    return transaction_hash, cast(TxReceipt, {"blockNumber": block_number})


def _balance_key(token_address: str, account_address: str) -> tuple[str, str]:
    return token_address, account_address


def _exchange_key(
    exchange_address: str, token_address: str, account_address: str
) -> tuple[str, str, str]:
    return exchange_address, token_address, account_address


def _set_exchange_state(
    exchange_address: str,
    token_address: str,
    account_address: str,
    balance: int | None = None,
    commitment: int | None = None,
) -> None:
    key = _exchange_key(exchange_address, token_address, account_address)
    if balance is not None:
        _EXCHANGE_BALANCES[key] = balance
    if commitment is not None:
        _EXCHANGE_COMMITMENTS[key] = commitment


def _apply_token_event(
    token_address: str, event_name: str, args: dict[str, Any]
) -> None:
    if event_name == "Issue":
        key = _balance_key(token_address, args["targetAddress"])
        _BALANCES[key] = _BALANCES.get(key, 0) + args["amount"]
    elif event_name == "Redeem":
        key = _balance_key(token_address, args["targetAddress"])
        _BALANCES[key] = _BALANCES.get(key, 0) - args["amount"]
    elif event_name == "Transfer":
        from_address = args["from"]
        to_address = args["to"]
        amount = args["value"]
        _BALANCES[_balance_key(token_address, from_address)] = (
            _BALANCES.get(_balance_key(token_address, from_address), 0) - amount
        )
        _BALANCES[_balance_key(token_address, to_address)] = (
            _BALANCES.get(_balance_key(token_address, to_address), 0) + amount
        )
        exchange_address = _TOKEN_EXCHANGES.get(token_address, ZERO_ADDRESS)
        if to_address == exchange_address:
            _set_exchange_state(
                exchange_address,
                token_address,
                from_address,
                balance=_EXCHANGE_BALANCES.get(
                    _exchange_key(exchange_address, token_address, from_address), 0
                )
                + amount,
            )
    elif event_name in {"Lock", "ForceLock"}:
        account = args["accountAddress"]
        lock_address = args["lockAddress"]
        amount = args["value"]
        _BALANCES[_balance_key(token_address, account)] = (
            _BALANCES.get(_balance_key(token_address, account), 0) - amount
        )
        key = (token_address, lock_address, account)
        _LOCKED_BALANCES[key] = _LOCKED_BALANCES.get(key, 0) + amount
    elif event_name in {"Unlock", "ForceUnlock"}:
        account = args["accountAddress"]
        lock_address = args["lockAddress"]
        recipient = args["recipientAddress"]
        amount = args["value"]
        _BALANCES[_balance_key(token_address, recipient)] = (
            _BALANCES.get(_balance_key(token_address, recipient), 0) + amount
        )
        key = (token_address, lock_address, account)
        _LOCKED_BALANCES[key] = _LOCKED_BALANCES.get(key, 0) - amount
    elif event_name == "ForceChangeLockedAccount":
        lock_address = args["lockAddress"]
        before_account = args["beforeAccountAddress"]
        after_account = args["afterAccountAddress"]
        amount = args["value"]
        before_key = (token_address, lock_address, before_account)
        after_key = (token_address, lock_address, after_account)
        _LOCKED_BALANCES[before_key] = _LOCKED_BALANCES.get(before_key, 0) - amount
        _LOCKED_BALANCES[after_key] = _LOCKED_BALANCES.get(after_key, 0) + amount
    elif event_name == "ApplyForTransfer":
        account = args["from"]
        amount = args["value"]
        _BALANCES[_balance_key(token_address, account)] = (
            _BALANCES.get(_balance_key(token_address, account), 0) - amount
        )
        key = _balance_key(token_address, account)
        _PENDING_TRANSFERS[key] = _PENDING_TRANSFERS.get(key, 0) + amount
    elif event_name == "CancelTransfer":
        account = args["from"]
        amount = args["value"]
        _BALANCES[_balance_key(token_address, account)] = (
            _BALANCES.get(_balance_key(token_address, account), 0) + amount
        )
        key = _balance_key(token_address, account)
        _PENDING_TRANSFERS[key] = _PENDING_TRANSFERS.get(key, 0) - amount
    elif event_name == "ApproveTransfer":
        from_account = args["from"]
        to_account = args["to"]
        amount = args["value"]
        _BALANCES[_balance_key(token_address, to_account)] = (
            _BALANCES.get(_balance_key(token_address, to_account), 0) + amount
        )
        key = _balance_key(token_address, from_account)
        _PENDING_TRANSFERS[key] = _PENDING_TRANSFERS.get(key, 0) - amount


def record_token_event(
    token_address: str,
    event_name: str,
    args: dict[str, Any],
    sender: str,
    log_index: int = 0,
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction(sender)
    _apply_token_event(token_address, event_name, args)
    _EVENTS.setdefault((token_address, event_name), []).append(
        {
            "event": event_name,
            "transactionHash": HexBytes(transaction_hash),
            "blockNumber": int(receipt["blockNumber"]),
            "logIndex": log_index,
            "args": args,
        }
    )
    return transaction_hash, receipt


def record_exchange_event(
    exchange_address: str,
    event_name: str,
    args: dict[str, Any],
    sender: str,
    log_index: int = 0,
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction(sender)
    token_address = args.get("tokenAddress", args.get("token", ZERO_ADDRESS))
    account = args.get("accountAddress")
    amount = args.get("amount", 0)

    if event_name == "NewOrder" and account is not None:
        key = _exchange_key(exchange_address, token_address, account)
        _EXCHANGE_BALANCES[key] = _EXCHANGE_BALANCES.get(key, 0) - amount
        _EXCHANGE_COMMITMENTS[key] = _EXCHANGE_COMMITMENTS.get(key, 0) + amount
    elif event_name in {"CancelOrder", "ForceCancelOrder"} and account is not None:
        key = _exchange_key(exchange_address, token_address, account)
        _EXCHANGE_BALANCES[key] = 0
        _EXCHANGE_COMMITMENTS[key] = _EXCHANGE_COMMITMENTS.get(key, 0) - amount
    elif event_name in {"EscrowCreated", "DeliveryCreated"}:
        account = args["sender"] if event_name == "EscrowCreated" else args["seller"]
        key = _exchange_key(exchange_address, token_address, account)
        _EXCHANGE_BALANCES[key] = _EXCHANGE_BALANCES.get(key, 0) - amount
        _EXCHANGE_COMMITMENTS[key] = _EXCHANGE_COMMITMENTS.get(key, 0) + amount
    elif event_name in {"EscrowCanceled", "DeliveryCanceled", "DeliveryAborted"}:
        account = args["sender"] if event_name == "EscrowCanceled" else args["seller"]
        key = _exchange_key(exchange_address, token_address, account)
        _EXCHANGE_BALANCES[key] = _EXCHANGE_BALANCES.get(key, 0) + amount
        _EXCHANGE_COMMITMENTS[key] = _EXCHANGE_COMMITMENTS.get(key, 0) - amount
    elif event_name == "HolderChanged":
        from_account = args["from"]
        to_account = args["to"]
        from_key = _exchange_key(exchange_address, token_address, from_account)
        if _EXCHANGE_COMMITMENTS.get(from_key, 0) > 0:
            _EXCHANGE_COMMITMENTS[from_key] = max(
                0, _EXCHANGE_COMMITMENTS.get(from_key, 0) - args["value"]
            )
        else:
            _set_exchange_state(
                exchange_address,
                token_address,
                from_account,
                balance=_EXCHANGE_BALANCES.get(from_key, 0) - args["value"],
            )
        _set_exchange_state(
            exchange_address,
            token_address,
            to_account,
            balance=_EXCHANGE_BALANCES.get(
                _exchange_key(exchange_address, token_address, to_account), 0
            )
            + args["value"],
        )
    elif event_name == "SettlementOK":
        for account in (args["buyAddress"], args["sellAddress"]):
            _set_exchange_state(
                exchange_address,
                token_address,
                account,
                balance=0,
                commitment=0,
            )
    _EVENTS.setdefault((exchange_address, event_name), []).append(
        {
            "event": event_name,
            "transactionHash": HexBytes(transaction_hash),
            "blockNumber": int(receipt["blockNumber"]),
            "logIndex": log_index,
            "args": args,
        }
    )
    return transaction_hash, receipt


def record_bulk_transfer_event(
    token_address: str,
    sender: str,
    recipients: list[str],
    amounts: list[int],
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction(sender)
    for log_index, (recipient, amount) in enumerate(
        zip(recipients, amounts, strict=True)
    ):
        args = {"from": sender, "to": recipient, "value": amount}
        _apply_token_event(token_address, "Transfer", args)
        _EVENTS.setdefault((token_address, "Transfer"), []).append(
            {
                "event": "Transfer",
                "transactionHash": HexBytes(transaction_hash),
                "blockNumber": int(receipt["blockNumber"]),
                "logIndex": log_index,
                "args": args,
            }
        )
    return transaction_hash, receipt


@pytest.fixture(scope="function", autouse=True)
def blockchain_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    global _token_counter
    _CHAIN.latest_block = 100
    _CHAIN.transaction_index = 0
    _token_counter = 0
    _EVENTS.clear()
    _TRANSACTION_SENDERS.clear()
    _TOKEN_EXCHANGES.clear()
    _TOKEN_ISSUERS.clear()
    _BALANCES.clear()
    _PENDING_TRANSFERS.clear()
    _LOCKED_BALANCES.clear()
    _EXCHANGE_BALANCES.clear()
    _EXCHANGE_COMMITMENTS.clear()
    monkeypatch.setattr(indexer_position_share, "web3", FakeAsyncWeb3(_CHAIN))

    async def get_event_logs(
        contract: FakeContract,
        event: str,
        block_from: int,
        block_to: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return get_events(contract.address, event, block_from, block_to)

    async def get_token(self: Any):
        self.issuer_address = _TOKEN_ISSUERS.get(self.token_address, "")
        self.tradable_exchange_contract_address = _TOKEN_EXCHANGES.get(
            self.token_address, ZERO_ADDRESS
        )
        return self

    async def call_function(
        contract: FakeContract,
        function_name: str,
        args: tuple[Any, ...],
        default_returns: Any = 0,
    ) -> Any:
        if function_name == "balanceOf":
            return _BALANCES.get(_balance_key(contract.address, args[0]), 0)
        if function_name == "pendingTransfer":
            return _PENDING_TRANSFERS.get(_balance_key(contract.address, args[0]), 0)
        if function_name == "lockedOf":
            return _LOCKED_BALANCES.get((contract.address, args[0], args[1]), 0)
        return default_returns

    async def get_exchange_balance(
        self: Any, account_address: str, token_address: str
    ) -> dict[str, int]:
        key = _exchange_key(
            self.exchange_contract.address, token_address, account_address
        )
        return {
            "balance": _EXCHANGE_BALANCES.get(key, 0),
            "commitment": _EXCHANGE_COMMITMENTS.get(key, 0),
        }

    def get_contract(contract_name: str, contract_address: str) -> FakeContract:
        return FakeContract(to_checksum_address(contract_address))

    monkeypatch.setattr(AsyncContractUtils, "get_event_logs", get_event_logs)
    monkeypatch.setattr(AsyncContractUtils, "call_function", call_function)
    monkeypatch.setattr(AsyncContractUtils, "get_contract", get_contract)
    monkeypatch.setattr(IbetShareContract, "get", get_token)
    monkeypatch.setattr(
        IbetExchangeInterface, "get_account_balance", get_exchange_balance
    )


@pytest.fixture(scope="function")
def main_func() -> Generator[Callable[[], Awaitable[None]], None, None]:
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


@pytest.fixture(scope="function")
def ibet_exchange_contract() -> FakeContract:
    return FakeContract(EXCHANGE_ADDRESS)


@pytest.fixture(scope="function")
def ibet_escrow_contract() -> FakeContract:
    return FakeContract(ESCROW_ADDRESS)


@pytest.fixture(scope="function")
def ibet_security_token_escrow_contract() -> FakeContract:
    return FakeContract(ESCROW_ADDRESS)


@pytest.fixture(scope="function")
def ibet_security_token_dvp_contract() -> FakeContract:
    return FakeContract(DVP_ADDRESS)


async def create_fake_share_token_contract(
    address: str,
    tradable_exchange_contract_address: str | None = None,
):
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x700 + _token_counter:040x}")
    _TOKEN_ISSUERS[token_address] = address
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    _BALANCES[_balance_key(token_address, address)] = 100
    _PENDING_TRANSFERS[_balance_key(token_address, address)] = 0
    return FakeContract(token_address)


async def create_fake_bond_token_contract(
    address: str,
    tradable_exchange_contract_address: str | None = None,
):
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x800 + _token_counter:040x}")
    _TOKEN_ISSUERS[token_address] = address
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    return FakeContract(token_address)


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

        # Prepare data : Token(share token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = {}
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = TokenStatus.PENDING
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

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

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        # Prepare data : BlockNumber
        _idx_position_share_block_number = IDXPositionShareBlockNumber()
        _idx_position_share_block_number.latest_block_number = 0
        async_db.add(_idx_position_share_block_number)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Single Token
    # Single event logs
    # - Issue
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Issue",
            {
                "from": issuer_address,
                "targetAddress": user_address_1,
                "lockAddress": ZERO_ADDRESS,
                "amount": 40,
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 2

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_2_1>
    # Single Token
    # Single event logs
    # - Transfer(to account)
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 2

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_2_2>
    # Single Token
    # Single event logs
    # - Transfer(to DEX)
    @pytest.mark.asyncio
    async def test_normal_2_2_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_escrow_contract: Contract,
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
        token_contract_1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": issuer_address,
                "to": ibet_escrow_contract.address,
                "value": 40,
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_2_3>
    # Single Token
    # Single event logs
    # - Transfer(HolderChanged in DEX)
    @pytest.mark.asyncio
    async def test_normal_2_2_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_escrow_contract: Contract,
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
        token_contract_1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": issuer_address,
                "to": ibet_escrow_contract.address,
                "value": 40,
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        record_exchange_event(
            ibet_escrow_contract.address,
            "HolderChanged",
            {
                "token": token_address_1,
                "from": issuer_address,
                "to": user_address_1,
                "value": 30,
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest async_db session.
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 2

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_3_1>
    # Single Token
    # Single event logs
    # - Lock
    @pytest.mark.asyncio
    async def test_normal_2_3_1(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "value": 20,
                "data": '{"message": "garnishment"}',
            },
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "value": 20,
                "data": '{"message": "ibet_wst_bridge"}',
            },
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "value": 20,
                "data": '{"message": "inheritance"}',
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 60
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _locked_position = (
            await async_db.scalars(
                select(IDXLockedPosition)
                .where(
                    and_(
                        IDXLockedPosition.token_address == token_address_1,
                        IDXLockedPosition.account_address == issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _locked_position is not None
        assert _locked_position.token_address == token_address_1
        assert _locked_position.lock_address == issuer_address
        assert _locked_position.account_address == issuer_address
        assert _locked_position.value == 60

        _lock_list = (
            await async_db.scalars(select(IDXLock).order_by(IDXLock.id))
        ).all()
        assert len(_lock_list) == 3

        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token_address_1
        assert _lock1.msg_sender == issuer_address
        assert _lock1.lock_address == issuer_address
        assert _lock1.account_address == issuer_address
        assert _lock1.value == 20
        assert _lock1.data == {"message": "garnishment"}
        assert _lock1.is_forced is False

        _lock2 = _lock_list[1]
        assert _lock2.id == 2
        assert _lock2.token_address == token_address_1
        assert _lock2.msg_sender == issuer_address
        assert _lock2.lock_address == issuer_address
        assert _lock2.account_address == issuer_address
        assert _lock2.value == 20
        assert _lock2.data == {"message": "ibet_wst_bridge"}
        assert _lock2.is_forced is False

        _lock3 = _lock_list[2]
        assert _lock3.id == 3
        assert _lock3.token_address == token_address_1
        assert _lock3.msg_sender == issuer_address
        assert _lock3.lock_address == issuer_address
        assert _lock3.account_address == issuer_address
        assert _lock3.value == 20
        assert _lock3.data == {}
        assert _lock3.is_forced is False

        _notification_list = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notification_list) == 3

        _notification1 = _notification_list[0]
        assert _notification1.id == 1
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.LOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 20,
            "data": {"message": "garnishment"},
        }

        _notification2 = _notification_list[1]
        assert _notification2.id == 2
        assert _notification2.issuer_address == issuer_address
        assert _notification2.priority == 0
        assert _notification2.type == NotificationType.LOCK_INFO
        assert _notification2.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 20,
            "data": {"message": "ibet_wst_bridge"},
        }

        _notification3 = _notification_list[2]
        assert _notification3.id == 3
        assert _notification3.issuer_address == issuer_address
        assert _notification3.priority == 0
        assert _notification3.type == NotificationType.LOCK_INFO
        assert _notification3.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 20,
            "data": {},
        }

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_3_2>
    # Single Token
    # Single event logs
    # - ForceLock
    @pytest.mark.asyncio
    async def test_normal_2_3_2(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "ForceLock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "value": 40,
                "data": '{"message": "force_lock"}',
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _locked_position = (
            await async_db.scalars(
                select(IDXLockedPosition)
                .where(
                    and_(
                        IDXLockedPosition.token_address == token_address_1,
                        IDXLockedPosition.account_address == issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _locked_position is not None
        assert _locked_position.token_address == token_address_1
        assert _locked_position.lock_address == issuer_address
        assert _locked_position.account_address == issuer_address
        assert _locked_position.value == 40

        _lock_list = (
            await async_db.scalars(select(IDXLock).order_by(IDXLock.id))
        ).all()
        assert len(_lock_list) == 1

        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token_address_1
        assert _lock1.msg_sender == issuer_address
        assert _lock1.lock_address == issuer_address
        assert _lock1.account_address == issuer_address
        assert _lock1.value == 40
        assert _lock1.data == {"message": "force_lock"}
        assert _lock1.is_forced is True

        _notification_list = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notification_list) == 1

        _notification1 = _notification_list[0]
        assert _notification1.id == 1
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.LOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 40,
            "data": {"message": "force_lock"},
        }

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_4_1>
    # Single Token
    # Single event logs
    # - Unlock
    @pytest.mark.asyncio
    async def test_normal_2_4_1(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "value": 40,
                "data": '{"message": "garnishment"}',
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        record_token_event(
            token_address_1,
            "Unlock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "recipientAddress": issuer_address,
                "value": 30,
                "data": '{"message": "garnishment"}',
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40 + 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _locked_position = (
            await async_db.scalars(
                select(IDXLockedPosition)
                .where(
                    and_(
                        IDXLockedPosition.token_address == token_address_1,
                        IDXLockedPosition.account_address == issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _locked_position is not None
        assert _locked_position.token_address == token_address_1
        assert _locked_position.lock_address == issuer_address
        assert _locked_position.account_address == issuer_address
        assert _locked_position.value == 40 - 30

        _lock_list = (
            await async_db.scalars(select(IDXLock).order_by(IDXLock.id))
        ).all()
        assert len(_lock_list) == 1

        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token_address_1
        assert _lock1.msg_sender == issuer_address
        assert _lock1.lock_address == issuer_address
        assert _lock1.account_address == issuer_address
        assert _lock1.value == 40
        assert _lock1.data == {"message": "garnishment"}

        _unlock_list = (
            await async_db.scalars(select(IDXUnlock).order_by(IDXUnlock.id))
        ).all()
        assert len(_unlock_list) == 1

        _unlock1 = _unlock_list[0]
        assert _unlock1.id == 1
        assert _unlock1.token_address == token_address_1
        assert _unlock1.msg_sender == issuer_address
        assert _unlock1.lock_address == issuer_address
        assert _unlock1.account_address == issuer_address
        assert _unlock1.recipient_address == issuer_address
        assert _unlock1.value == 30
        assert _unlock1.data == {"message": "garnishment"}
        assert _unlock1.is_forced is False

        _notification_list = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notification_list) == 2

        _notification1 = _notification_list[0]
        assert _notification1.id == 1
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.LOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 40,
            "data": {"message": "garnishment"},
        }

        _notification1 = _notification_list[1]
        assert _notification1.id == 2
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.UNLOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 30,
            "data": {"message": "garnishment"},
        }

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_4_2>
    # Single Token
    # Single event logs
    # - ForceUnlock
    @pytest.mark.asyncio
    async def test_normal_2_4_2(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "value": 40,
                "data": '{"message": "garnishment"}',
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        record_token_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": issuer_address,
                "lockAddress": issuer_address,
                "recipientAddress": issuer_address,
                "value": 30,
                "data": '{"message": "garnishment"}',
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40 + 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _locked_position = (
            await async_db.scalars(
                select(IDXLockedPosition)
                .where(
                    and_(
                        IDXLockedPosition.token_address == token_address_1,
                        IDXLockedPosition.account_address == issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _locked_position is not None
        assert _locked_position.token_address == token_address_1
        assert _locked_position.lock_address == issuer_address
        assert _locked_position.account_address == issuer_address
        assert _locked_position.value == 40 - 30

        _lock_list = (
            await async_db.scalars(select(IDXLock).order_by(IDXLock.id))
        ).all()
        assert len(_lock_list) == 1

        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token_address_1
        assert _lock1.msg_sender == issuer_address
        assert _lock1.lock_address == issuer_address
        assert _lock1.account_address == issuer_address
        assert _lock1.value == 40
        assert _lock1.data == {"message": "garnishment"}

        _unlock_list = (
            await async_db.scalars(select(IDXUnlock).order_by(IDXUnlock.id))
        ).all()
        assert len(_unlock_list) == 1

        _unlock1 = _unlock_list[0]
        assert _unlock1.id == 1
        assert _unlock1.token_address == token_address_1
        assert _unlock1.msg_sender == issuer_address
        assert _unlock1.lock_address == issuer_address
        assert _unlock1.account_address == issuer_address
        assert _unlock1.recipient_address == issuer_address
        assert _unlock1.value == 30
        assert _unlock1.data == {"message": "garnishment"}
        assert _unlock1.is_forced is True

        _notification_list = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notification_list) == 2

        _notification1 = _notification_list[0]
        assert _notification1.id == 1
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.LOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 40,
            "data": {"message": "garnishment"},
        }

        _notification1 = _notification_list[1]
        assert _notification1.id == 2
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.UNLOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 30,
            "data": {"message": "garnishment"},
        }

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_5>
    # Single Token
    # Single event logs
    # - Redeem
    @pytest.mark.asyncio
    async def test_normal_2_5(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Redeem",
            {
                "from": issuer_address,
                "targetAddress": issuer_address,
                "lockAddress": ZERO_ADDRESS,
                "amount": 40,
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_6>
    # Single Token
    # Single event logs
    # - ApplyForTransfer
    @pytest.mark.asyncio
    async def test_normal_2_6(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "ApplyForTransfer",
            {
                "index": 0,
                "from": issuer_address,
                "to": user_address_1,
                "value": 40,
                "data": "",
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_7>
    # Single Token
    # Single event logs
    # - CancelTransfer
    @pytest.mark.asyncio
    async def test_normal_2_7(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "ApplyForTransfer",
            {
                "index": 0,
                "from": issuer_address,
                "to": user_address_1,
                "value": 40,
                "data": "",
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40

        record_token_event(
            token_address_1,
            "CancelTransfer",
            {
                "index": 0,
                "from": issuer_address,
                "to": user_address_1,
                "value": 40,
                "data": "",
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_8>
    # Single Token
    # Single event logs
    # - ApproveTransfer
    @pytest.mark.asyncio
    async def test_normal_2_8(
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "ApplyForTransfer",
            {
                "index": 0,
                "from": issuer_address,
                "to": user_address_1,
                "value": 40,
                "data": "",
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40

        record_token_event(
            token_address_1,
            "ApproveTransfer",
            {
                "index": 0,
                "from": issuer_address,
                "to": user_address_1,
                "value": 40,
                "data": "",
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 2
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_1>
    # Single Token
    # Single event logs
    # - IbetExchange: NewOrder
    @pytest.mark.asyncio
    async def test_normal_2_9_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_exchange_contract: Contract,
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
        token_contract_1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_exchange_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(bond token)
        token_contract_2 = await create_fake_bond_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_exchange_contract.address,
        )
        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": issuer_address,
                "to": ibet_exchange_contract.address,
                "value": 40,
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        record_exchange_event(
            ibet_exchange_contract.address,
            "NewOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": issuer_address,
                "isBuy": False,
                "price": 10000,
                "amount": 30,
                "agentAddress": issuer_address,
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 30
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_2>
    # Single Token
    # Single event logs
    # - IbetExchange: CancelOrder
    @pytest.mark.asyncio
    async def test_normal_2_9_2(
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

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": exchange_contract.address,
                "value": 10,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "NewOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": user_address_1,
                "isBuy": False,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "CancelOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": user_address_1,
                "isBuy": False,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            user_address_1,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": exchange_contract.address,
                "to": user_address_1,
                "value": 10,
            },
            exchange_contract.address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_3>
    # Single Token
    # Single event logs
    # - IbetExchange: ForceCancelOrder
    @pytest.mark.asyncio
    async def test_normal_2_9_3(
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

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": exchange_contract.address,
                "value": 10,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "NewOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": user_address_1,
                "isBuy": False,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "ForceCancelOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": user_address_1,
                "isBuy": False,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": exchange_contract.address,
                "to": user_address_1,
                "value": 10,
            },
            exchange_contract.address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_4>
    # Single Token
    # Single event logs
    # - IbetExchange: Agree
    @pytest.mark.asyncio
    async def test_normal_2_9_4(
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

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": exchange_contract.address,
                "value": 10,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "NewOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": user_address_1,
                "isBuy": False,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "Agree",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "agreementId": 1,
                "buyAddress": user_address_2,
                "sellAddress": user_address_1,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            user_address_2,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 10
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_5>
    # Single Token
    # Single event logs
    # - IbetExchange: SettlementOK
    @pytest.mark.asyncio
    async def test_normal_2_9_5(
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

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": exchange_contract.address,
                "value": 10,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "NewOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": user_address_1,
                "isBuy": False,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "SettlementOK",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "agreementId": 1,
                "buyAddress": user_address_2,
                "sellAddress": user_address_1,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": exchange_contract.address,
                "to": user_address_2,
                "value": 10,
            },
            exchange_contract.address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_6>
    # Single Token
    # Single event logs
    # - IbetExchange: SettlementNG
    @pytest.mark.asyncio
    async def test_normal_2_9_6(
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

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": exchange_contract.address,
                "value": 10,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "NewOrder",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "accountAddress": user_address_1,
                "isBuy": False,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            user_address_1,
        )
        record_exchange_event(
            exchange_contract.address,
            "SettlementNG",
            {
                "tokenAddress": token_address_1,
                "orderId": 1,
                "agreementId": 1,
                "buyAddress": user_address_2,
                "sellAddress": user_address_1,
                "price": 100,
                "amount": 10,
                "agentAddress": issuer_address,
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 10
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_10_1>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowCreated
    @pytest.mark.asyncio
    async def test_normal_2_10_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
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
        token_contract_1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(bond token)
        token_contract_2 = await create_fake_bond_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": issuer_address,
                "to": ibet_security_token_escrow_contract.address,
                "value": 40,
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        record_exchange_event(
            ibet_security_token_escrow_contract.address,
            "EscrowCreated",
            {
                "escrowId": 1,
                "token": token_address_1,
                "sender": issuer_address,
                "recipient": user_address_1,
                "amount": 30,
                "agent": issuer_address,
                "data": "",
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 30
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_10_2>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowCanceled
    @pytest.mark.asyncio
    async def test_normal_2_10_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
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

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": user_address_1, "to": escrow_contract.address, "value": 30},
            user_address_1,
        )
        record_exchange_event(
            escrow_contract.address,
            "EscrowCreated",
            {
                "escrowId": 1,
                "token": token_address_1,
                "sender": user_address_1,
                "recipient": user_address_2,
                "amount": 10,
                "agent": issuer_address,
                "data": "",
            },
            user_address_1,
        )
        record_exchange_event(
            escrow_contract.address,
            "EscrowCanceled",
            {
                "escrowId": 1,
                "token": token_address_1,
                "sender": user_address_1,
                "recipient": user_address_2,
                "amount": 10,
                "agent": issuer_address,
            },
            user_address_1,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_10_3>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowFinished
    @pytest.mark.asyncio
    async def test_normal_2_10_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
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

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": user_address_1, "to": escrow_contract.address, "value": 30},
            user_address_1,
        )
        record_exchange_event(
            escrow_contract.address,
            "EscrowCreated",
            {
                "escrowId": 1,
                "token": token_address_1,
                "sender": user_address_1,
                "recipient": user_address_2,
                "amount": 10,
                "agent": issuer_address,
                "data": "",
            },
            user_address_1,
        )
        record_exchange_event(
            escrow_contract.address,
            "HolderChanged",
            {
                "token": token_address_1,
                "from": user_address_1,
                "to": user_address_2,
                "value": 10,
            },
            issuer_address,
        )
        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 20
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 10
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_11_1>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenDVP: DeliveryCreated
    @pytest.mark.asyncio
    async def test_normal_2_11_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
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
        token_contract_1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(bond token)
        token_contract_2 = await create_fake_bond_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": issuer_address,
                "to": ibet_security_token_dvp_contract.address,
                "value": 40,
            },
            issuer_address,
        )

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        record_exchange_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            {
                "deliveryId": 1,
                "token": token_address_1,
                "seller": issuer_address,
                "buyer": user_address_1,
                "amount": 30,
                "agent": issuer_address,
                "data": "",
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 1

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 30
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_11_2>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenDVP: DeliveryCanceled
    @pytest.mark.asyncio
    async def test_normal_2_11_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
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

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": ibet_security_token_dvp_contract.address,
                "value": 30,
            },
            user_address_1,
        )
        record_exchange_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            {
                "deliveryId": 1,
                "token": token_address_1,
                "seller": user_address_1,
                "buyer": user_address_2,
                "amount": 10,
                "agent": issuer_address,
                "data": "",
            },
            user_address_1,
        )
        record_exchange_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCanceled",
            {
                "deliveryId": 1,
                "token": token_address_1,
                "seller": user_address_1,
                "buyer": user_address_2,
                "amount": 10,
                "agent": issuer_address,
            },
            user_address_1,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_11_3>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenDVP: DeliveryFinished
    @pytest.mark.asyncio
    async def test_normal_2_11_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
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

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": ibet_security_token_dvp_contract.address,
                "value": 30,
            },
            user_address_1,
        )
        record_exchange_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            {
                "deliveryId": 1,
                "token": token_address_1,
                "seller": user_address_1,
                "buyer": user_address_2,
                "amount": 10,
                "agent": issuer_address,
                "data": "",
            },
            user_address_1,
        )
        record_exchange_event(
            ibet_security_token_dvp_contract.address,
            "HolderChanged",
            {
                "token": token_address_1,
                "from": user_address_1,
                "to": user_address_2,
                "value": 10,
            },
            issuer_address,
        )
        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 20
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 10
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_11_4>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenDVP: DeliveryAborted
    @pytest.mark.asyncio
    async def test_normal_2_11_4(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
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

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": ibet_security_token_dvp_contract.address,
                "value": 30,
            },
            user_address_1,
        )
        record_exchange_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            {
                "deliveryId": 1,
                "token": token_address_1,
                "seller": user_address_1,
                "buyer": user_address_2,
                "amount": 10,
                "agent": issuer_address,
                "data": "",
            },
            user_address_1,
        )
        record_exchange_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryAborted",
            {
                "deliveryId": 1,
                "token": token_address_1,
                "seller": user_address_1,
                "buyer": user_address_2,
                "amount": 10,
                "agent": issuer_address,
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_12>
    # Single Token
    # Single event logs
    # - ForceChangeLockedAccount
    @pytest.mark.asyncio
    async def test_normal_2_12(
        self,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        lock_account = default_eth_account("user2")
        after_locked_account = default_eth_account("user3")

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        record_token_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": issuer_address,
                "lockAddress": lock_account["address"],
                "value": 40,
                "data": '{"message": "garnishment"}',
            },
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "lockAddress": lock_account["address"],
                "beforeAccountAddress": issuer_address,
                "afterAccountAddress": after_locked_account["address"],
                "value": 30,
                "data": '{"message": "ibet_wst_bridge"}',
            },
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        position_before_account = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert position_before_account is not None
        assert position_before_account.token_address == token_address_1
        assert position_before_account.account_address == issuer_address
        assert position_before_account.balance == 100 - 40
        assert position_before_account.exchange_balance == 0
        assert position_before_account.exchange_commitment == 0
        assert position_before_account.pending_transfer == 0

        locked_position_before_account = (
            await async_db.scalars(
                select(IDXLockedPosition)
                .where(
                    and_(
                        IDXLockedPosition.token_address == token_address_1,
                        IDXLockedPosition.account_address == issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
        assert locked_position_before_account is not None
        assert locked_position_before_account.token_address == token_address_1
        assert locked_position_before_account.lock_address == lock_account["address"]
        assert locked_position_before_account.account_address == issuer_address
        assert locked_position_before_account.value == 40 - 30

        position_after_account = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == after_locked_account["address"])
                .limit(1)
            )
        ).first()
        assert position_after_account is not None
        assert position_after_account.token_address == token_address_1
        assert position_after_account.account_address == after_locked_account["address"]
        assert position_after_account.balance == 0
        assert position_after_account.exchange_balance == 0
        assert position_after_account.exchange_commitment == 0
        assert position_after_account.pending_transfer == 0

        locked_position_after_account = (
            await async_db.scalars(
                select(IDXLockedPosition)
                .where(
                    and_(
                        IDXLockedPosition.token_address == token_address_1,
                        IDXLockedPosition.account_address
                        == after_locked_account["address"],
                    )
                )
                .limit(1)
            )
        ).first()
        assert locked_position_after_account is not None
        assert locked_position_after_account.token_address == token_address_1
        assert locked_position_after_account.lock_address == lock_account["address"]
        assert (
            locked_position_after_account.account_address
            == after_locked_account["address"]
        )
        assert locked_position_after_account.value == 30

        lock_idx_list = (
            await async_db.scalars(select(IDXLock).order_by(IDXLock.id))
        ).all()
        assert len(lock_idx_list) == 2

        assert lock_idx_list[0].id == 1
        assert lock_idx_list[0].token_address == token_address_1
        assert lock_idx_list[0].msg_sender == issuer_address
        assert lock_idx_list[0].lock_address == lock_account["address"]
        assert lock_idx_list[0].account_address == issuer_address
        assert lock_idx_list[0].value == 40
        assert lock_idx_list[0].data == {"message": "garnishment"}
        assert lock_idx_list[0].is_forced is False

        assert lock_idx_list[1].id == 2
        assert lock_idx_list[1].token_address == token_address_1
        assert lock_idx_list[1].msg_sender == issuer_address
        assert lock_idx_list[1].lock_address == lock_account["address"]
        assert lock_idx_list[1].account_address == after_locked_account["address"]
        assert lock_idx_list[1].value == 30
        assert lock_idx_list[1].data == {"message": "ibet_wst_bridge"}
        assert lock_idx_list[1].is_forced is True

        unlock_idx_list = (
            await async_db.scalars(select(IDXUnlock).order_by(IDXUnlock.id))
        ).all()
        assert len(unlock_idx_list) == 1

        assert unlock_idx_list[0].id == 1
        assert unlock_idx_list[0].token_address == token_address_1
        assert unlock_idx_list[0].msg_sender == issuer_address
        assert unlock_idx_list[0].lock_address == lock_account["address"]
        assert unlock_idx_list[0].account_address == issuer_address
        assert unlock_idx_list[0].recipient_address == after_locked_account["address"]
        assert unlock_idx_list[0].value == 30
        assert unlock_idx_list[0].data == {"message": "ibet_wst_bridge"}
        assert unlock_idx_list[0].is_forced is True

        notification_list = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(notification_list) == 3

        assert notification_list[0].id == 1
        assert notification_list[0].issuer_address == issuer_address
        assert notification_list[0].priority == 0
        assert notification_list[0].type == NotificationType.LOCK_INFO
        assert notification_list[0].metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": lock_account["address"],
            "value": 40,
            "data": {"message": "garnishment"},
        }

        assert notification_list[1].id == 2
        assert notification_list[1].issuer_address == issuer_address
        assert notification_list[1].priority == 0
        assert notification_list[1].type == NotificationType.UNLOCK_INFO
        assert notification_list[1].metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": lock_account["address"],
            "recipient_address": after_locked_account["address"],
            "value": 30,
            "data": {"message": "ibet_wst_bridge"},
        }

        assert notification_list[2].id == 3
        assert notification_list[2].issuer_address == issuer_address
        assert notification_list[2].priority == 0
        assert notification_list[2].type == NotificationType.LOCK_INFO
        assert notification_list[2].metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": after_locked_account["address"],
            "lock_address": lock_account["address"],
            "value": 30,
            "data": {"message": "ibet_wst_bridge"},
        }

        idx_position_bond_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert idx_position_bond_block_number is not None
        assert idx_position_bond_block_number.id == 1
        assert idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_3_1>
    # Single Token
    # Multi event logs
    # - Transfer(twice)
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = {}
        token_3.tx_hash = "tx_hash"
        token_3.token_status = TokenStatus.PENDING
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": user_address_1, "to": user_address_2, "value": 10},
            user_address_1,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

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
        user_4 = default_eth_account("user4")
        user_address_3 = user_4["address"]
        user_5 = default_eth_account("user5")
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        address_list1 = [user_address_1, user_address_2, user_address_3]
        value_list1 = [10, 20, 30]
        record_bulk_transfer_event(
            token_address_1, issuer_address, address_list1, value_list1
        )
        address_list2 = [user_address_1, user_address_2, user_address_3, user_address_4]
        value_list2 = [1, 2, 3, 4]
        record_bulk_transfer_event(
            token_address_1, issuer_address, address_list2, value_list2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 5

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 60 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 11
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 22
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_3)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_3
        assert _position.balance == 33
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_4)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_4
        assert _position.balance == 4
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_3_3>
    # Single Token
    # Multi event logs
    # - IbetExchange: NewOrder
    # - IbetExchange: CancelOrder
    @pytest.mark.asyncio
    async def test_normal_3_3(
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

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": user_address_1,
                "to": exchange_contract.address,
                "value": 10,
            },
            user_address_1,
        )
        for order_id, is_buy in ((1, False), (2, True)):
            record_exchange_event(
                exchange_contract.address,
                "NewOrder",
                {
                    "tokenAddress": token_address_1,
                    "orderId": order_id,
                    "accountAddress": user_address_1,
                    "isBuy": is_buy,
                    "price": 100,
                    "amount": 10,
                    "agentAddress": issuer_address,
                },
                user_address_1,
            )
            record_exchange_event(
                exchange_contract.address,
                "CancelOrder",
                {
                    "tokenAddress": token_address_1,
                    "orderId": order_id,
                    "accountAddress": user_address_1,
                    "isBuy": is_buy,
                    "price": 100,
                    "amount": 10,
                    "agentAddress": issuer_address,
                },
                user_address_1,
            )
        record_token_event(
            token_address_1,
            "Transfer",
            {
                "from": exchange_contract.address,
                "to": user_address_1,
                "value": 10,
            },
            exchange_contract.address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_3_4>
    # Single Token
    # Multi event logs
    # - IbetSecurityTokenEscrow: EscrowCreated
    # - IbetSecurityTokenEscrow: EscrowCanceled
    @pytest.mark.asyncio
    async def test_normal_3_4(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
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

        # Issuer issues bond token.
        token_contract = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
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

        await async_db.commit()

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": user_address_1, "to": escrow_contract.address, "value": 30},
            user_address_1,
        )
        for _ in range(3):
            record_exchange_event(
                escrow_contract.address,
                "EscrowCreated",
                {
                    "escrowId": _ + 1,
                    "token": token_address_1,
                    "sender": user_address_1,
                    "recipient": user_address_2,
                    "amount": 10,
                    "agent": issuer_address,
                    "data": "",
                },
                user_address_1,
            )
            record_exchange_event(
                escrow_contract.address,
                "EscrowCanceled",
                {
                    "escrowId": _ + 1,
                    "token": token_address_1,
                    "sender": user_address_1,
                    "recipient": user_address_2,
                    "amount": 10,
                    "agent": issuer_address,
                },
                user_address_1,
            )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 3
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == issuer_address)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(IDXPosition.account_address == user_address_2)
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_4>
    # Multi Token
    @pytest.mark.asyncio
    async def test_normal_4(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
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

        # Issuer issues bond token.
        token_contract1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        # Issuer issues bond token.
        token_contract2 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
        )
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

        # Before run(consume accumulated events)
        await processor.sync_new_logs()
        async_db.expire_all()

        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 30},
            issuer_address,
        )
        record_token_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_token_event(
            token_address_2,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
            issuer_address,
        )
        record_token_event(
            token_address_2,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 60},
            issuer_address,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _position_list = (await async_db.scalars(select(IDXPosition))).all()
        assert len(_position_list) == 6
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(
                    and_(
                        IDXPosition.account_address == issuer_address,
                        IDXPosition.token_address == token_address_1,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(
                    and_(
                        IDXPosition.account_address == user_address_1,
                        IDXPosition.token_address == token_address_1,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(
                    and_(
                        IDXPosition.account_address == user_address_2,
                        IDXPosition.token_address == token_address_1,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(
                    and_(
                        IDXPosition.account_address == issuer_address,
                        IDXPosition.token_address == token_address_2,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_2
        assert _position.account_address == issuer_address
        assert _position.balance == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(
                    and_(
                        IDXPosition.account_address == user_address_1,
                        IDXPosition.token_address == token_address_2,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_2
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            await async_db.scalars(
                select(IDXPosition)
                .where(
                    and_(
                        IDXPosition.account_address == user_address_2,
                        IDXPosition.token_address == token_address_2,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _position is not None
        assert _position.token_address == token_address_2
        assert _position.account_address == user_address_2
        assert _position.balance == 60
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = (
            await async_db.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        assert _idx_position_share_block_number is not None
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_5>
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip process".
    @pytest.mark.asyncio
    async def test_normal_5(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        _idx_position_share_block_number = IDXPositionShareBlockNumber()
        _idx_position_share_block_number.id = 1
        _idx_position_share_block_number.latest_block_number = 99999999
        async_db.add(_idx_position_share_block_number)
        await async_db.commit()

        await processor.sync_new_logs()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "skip process")
        )

    # <Normal_6_1>
    # Newly tokens added
    # -> Sync issuer position
    @pytest.mark.asyncio
    async def test_normal_6_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
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
        token_contract1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
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
        async_db.expire_all()

        assert len(processor.token_list.keys()) == 1
        assert len(processor.exchange_address_list) == 1

        positions = (await async_db.scalars(select(IDXPosition))).all()
        assert len(positions) == 1
        issuer_position = positions[0]
        assert issuer_position.json() == {
            "account_address": issuer_address,
            "balance": 100,
            "exchange_balance": 0,
            "exchange_commitment": 0,
            "pending_transfer": 0,
        }

        token_af = (await async_db.scalars(select(Token).limit(1))).first()
        assert token_af is not None
        assert token_af.initial_position_synced is True

        # Prepare additional token
        token_contract2 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
        )
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
        assert len(processor.exchange_address_list) == 1

    # <Normal_6_2>
    # Already init synced
    # -> Skip issuer position sync
    @pytest.mark.asyncio
    async def test_normal_6_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
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
        token_contract1 = await create_fake_share_token_contract(
            issuer_address,
            tradable_exchange_contract_address=escrow_contract.address,
        )
        token_address_1 = token_contract1.address

        # Prepare data: Token (Already init synced)
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        token_1.initial_position_synced = True  # already synced
        async_db.add(token_1)

        await async_db.commit()

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        assert len(processor.token_list.keys()) == 1
        assert len(processor.exchange_address_list) == 1

        positions = (await async_db.scalars(select(IDXPosition))).all()
        assert len(positions) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # If exception occurs out of Processor except-catch, batch outputs logs in mainloop.
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
        token_contract_1 = await create_fake_share_token_contract(issuer_address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        token_attr = {
            "issuer_address": issuer_address,
            "token_address": token_address_1,
            "name": "テスト債券-test",
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_cache = TokenCache()
        token_cache.token_address = token_address_1
        token_cache.attributes = token_attr
        token_cache.cached_datetime = datetime.now(UTC).replace(tzinfo=None)
        token_cache.expiration_datetime = datetime.now(UTC).replace(
            tzinfo=None
        ) + timedelta(seconds=TOKEN_CACHE_TTL)
        async_db.add(token_cache)

        await async_db.commit()

        # Run mainloop once and fail with web3 utils error
        with (
            patch("batch.indexer_position_share.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                indexer_position_share.web3.eth,
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
            patch("batch.indexer_position_share.INDEXER_SYNC_INTERVAL", None),
            patch.object(AsyncSession, "scalars", side_effect=InvalidRequestError()),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()
