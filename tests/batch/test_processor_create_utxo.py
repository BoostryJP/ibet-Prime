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

import datetime
import json
from typing import Any, cast
from unittest import mock
from unittest.mock import ANY, MagicMock, call

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3.types import TxReceipt

import batch.processor_create_utxo as processor_create_utxo
from app.model.db import (
    UTXO,
    Account,
    AccountRsaStatus,
    LedgerCreationRequest,
    LedgerCreationRequestData,
    LedgerDataType,
    LedgerDetailsTemplate,
    LedgerTemplate,
    Token,
    TokenType,
    TokenVersion,
    UTXOBlockNumber,
)
from app.model.db.token import TokenStatus
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch.processor_create_utxo import Processor
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

    @property
    def block_number(self):
        return self._get_block_number()

    async def _get_block_number(self) -> int:
        return self.chain.latest_block

    def contract(self, address: str, abi: Any) -> FakeContract:
        return FakeContract(address)

    async def get_block(self, block_number: int) -> dict[str, int]:
        return {"timestamp": 1_700_000_000 + block_number}

    async def get_code(self, address: str) -> HexBytes:
        return HexBytes("0xdeadbeef" if address in _CONTRACT_ADDRESSES else "0x")


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
_TRANSACTION_INPUTS: dict[str, HexBytes] = {}
_TRANSACTION_SENDERS: dict[str, str] = {}
_CONTRACT_ADDRESSES = {EXCHANGE_ADDRESS, ESCROW_ADDRESS}
_TOKEN_EXCHANGES: dict[str, str] = {}
_TOKEN_ISSUERS: dict[str, str] = {}
_token_counter = 0


@pytest.fixture(scope="function")
def processor(async_db: AsyncSession):
    return Processor()


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


def _record_event_transaction(
    sender: str, transaction_input: str = ""
) -> tuple[str, TxReceipt]:
    block_number = _CHAIN.mine()
    transaction_hash = f"0x{_CHAIN.transaction_index:064x}"
    _TRANSACTION_INPUTS[transaction_hash] = HexBytes("0x" + transaction_input)
    _TRANSACTION_SENDERS[transaction_hash] = sender
    return transaction_hash, cast(TxReceipt, {"blockNumber": block_number})


def record_event(
    contract_address: str,
    event_name: str,
    args: dict[str, Any],
    sender: str,
    transaction_input: str = "",
    log_index: int = 0,
) -> tuple[str, TxReceipt]:
    transaction_hash, receipt = _record_event_transaction(sender, transaction_input)
    _EVENTS.setdefault((contract_address, event_name), []).append(
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
        _EVENTS.setdefault((token_address, "Transfer"), []).append(
            {
                "event": "Transfer",
                "transactionHash": HexBytes(transaction_hash),
                "blockNumber": int(receipt["blockNumber"]),
                "logIndex": log_index,
                "args": {"from": sender, "to": recipient, "value": amount},
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
    _TRANSACTION_INPUTS.clear()
    _TRANSACTION_SENDERS.clear()
    _TOKEN_EXCHANGES.clear()
    _TOKEN_ISSUERS.clear()
    monkeypatch.setattr(processor_create_utxo, "web3", FakeAsyncWeb3(_CHAIN))

    async def get_event_logs(
        contract: FakeContract,
        event: str,
        block_from: int,
        block_to: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        events = get_events(contract.address, event, block_from, block_to)
        argument_filters = kwargs.get("argument_filters")
        if argument_filters:
            events = [
                event
                for event in events
                if all(
                    event["args"].get(key) == value
                    for key, value in argument_filters.items()
                )
            ]
        return events

    async def get_transaction(transaction_hash: str) -> dict[str, HexBytes]:
        return {"input": _TRANSACTION_INPUTS[str(transaction_hash)]}

    async def get_token(self: Any):
        self.issuer_address = _TOKEN_ISSUERS.get(self.token_address, "")
        self.tradable_exchange_contract_address = _TOKEN_EXCHANGES.get(
            self.token_address, ZERO_ADDRESS
        )
        self.principal_value = 20
        self.face_value = 20
        return self

    def get_contract(contract_name: str, contract_address: str) -> FakeContract:
        return FakeContract(to_checksum_address(contract_address))

    monkeypatch.setattr(AsyncContractUtils, "get_event_logs", get_event_logs)
    monkeypatch.setattr(AsyncContractUtils, "get_transaction", get_transaction)
    monkeypatch.setattr(AsyncContractUtils, "get_contract", get_contract)
    monkeypatch.setattr(IbetShareContract, "get", get_token)
    monkeypatch.setattr(IbetStraightBondContract, "get", get_token)


async def create_fake_bond_token_contract(
    address: str,
    tradable_exchange_contract_address: str | None = None,
) -> str:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x700 + _token_counter:040x}")
    _TOKEN_ISSUERS[token_address] = address
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    if tradable_exchange_contract_address is not None:
        _CONTRACT_ADDRESSES.add(to_checksum_address(tradable_exchange_contract_address))
    return token_address


async def create_fake_share_token_contract(address: str) -> str:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x800 + _token_counter:040x}")
    _TOKEN_ISSUERS[token_address] = address
    _TOKEN_EXCHANGES[token_address] = ZERO_ADDRESS
    return token_address


@pytest.mark.asyncio
class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Execute Batch Run 1st: No Event
    # Execute Batch Run 2nd: Executed Transfer Event
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_1(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        token_address_2 = await create_fake_share_token_contract(issuer_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        _token_2.version = TokenVersion.V_25_09
        async_db.add(_token_2)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Execute batch(Run 1st)
        # Assume: Skip processing
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO))).all()
        assert len(_utxo_list) == 0
        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

        # Record transfer events
        record_event(
            token_address_2,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 70},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 20},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Transfer",
            {"from": user_address_1, "to": user_address_2, "value": 10},
            user_address_1,
        )

        # Execute batch(Run 2nd)
        # Assume: Create UTXO
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        # 1.Bond token:issuer -> user1 (tx2)
        # 2.Bond token:issuer -> user2 (tx3)
        # 3.Share token:issuer -> user1 (tx1)
        # 4.Share token:user1 -> issuer (tx4)
        assert len(_utxo_list) == 4
        _utxo: Any = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 40
        _utxo_block_number_3: Any = _utxo_list[2].block_number
        _utxo_block_timestamp_3: Any = _utxo_list[2].block_timestamp
        assert _utxo.block_number > _utxo_block_number_3
        assert _utxo.block_timestamp > _utxo_block_timestamp_3
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo_block_number_1: Any = _utxo_list[0].block_number
        _utxo_block_timestamp_1: Any = _utxo_list[0].block_timestamp
        assert _utxo.block_number > _utxo_block_number_1
        assert _utxo.block_timestamp > _utxo_block_timestamp_1
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 60  # spend to user2(70 - 10)
        assert _utxo.block_number is not None
        assert _utxo.block_timestamp is not None
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 10
        _utxo_block_number_2: Any = _utxo_list[1].block_number
        _utxo_block_timestamp_2: Any = _utxo_list[1].block_timestamp
        assert _utxo.block_number > _utxo_block_number_2
        assert _utxo.block_timestamp > _utxo_block_timestamp_2
        _utxo_block_number: Any = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        _utxo_block_number_4: Any = _utxo_list[3].block_number
        assert _utxo_block_number.latest_block_number == _utxo_block_number_4

        mock_func.assert_has_calls(
            [
                call(token_address=token_address_1, db=ANY),
                call(token_address=token_address_2, db=ANY),
            ]
        )

    # <Normal_1_1>
    # request_ledger_creation raises ValueError
    # -> discard request and continue processing
    @mock.patch(
        "batch.processor_create_utxo.request_ledger_creation", side_effect=ValueError
    )
    async def test_normal_1_1(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Execute batch(Run 1st)
        await processor.process()
        async_db.expire_all()

        # Record transfer events
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 40},
            issuer_address,
        )

        # Execute batch(Run 2nd)
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 1
        assert _utxo_list[0].account_address == user_address_1
        assert _utxo_list[0].token_address == token_address_1
        assert _utxo_list[0].amount == 40

        assert len((await async_db.scalars(select(LedgerCreationRequest))).all()) == 0
        assert (
            len((await async_db.scalars(select(LedgerCreationRequestData))).all()) == 0
        )

        mock_func.assert_has_calls([call(token_address=token_address_1, db=ANY)])

    # <Normal_2>
    # Over max block lot
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    @mock.patch("batch.processor_create_utxo.CREATE_UTXO_BLOCK_LOT_MAX_SIZE", 5)
    async def test_normal_2(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        latest_block_number = web3.eth.block_number
        _utxo_block_number = UTXOBlockNumber()
        _utxo_block_number.latest_block_number = latest_block_number
        async_db.add(_utxo_block_number)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record transfer events
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 60},
            issuer_address,
        )
        for _ in range(5):
            record_event(
                token_address_1,
                "Transfer",
                {"from": user_address_1, "to": user_address_2, "value": 10},
                issuer_address,
            )

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block_number + 5
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 5
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        assert _utxo.block_number == latest_block_number + 1
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        assert _utxo.block_number == latest_block_number + 2
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        assert _utxo.block_number == latest_block_number + 3
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        assert _utxo.block_number == latest_block_number + 4
        _utxo = _utxo_list[4]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        assert _utxo.block_number == latest_block_number + 5

    # <Normal_3>
    # bulk transfer(same transaction-hash)
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_3(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record bulk transfer event
        record_bulk_transfer_event(
            token_address_1,
            issuer_address,
            [user_address_1, user_address_2, user_address_1],
            [10, 20, 40],
        )

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 2
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 50
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20

    # <Normal_4>
    # to Exchange transfer only
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_4(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(
            issuer_address,
            tradable_exchange_contract_address=ESCROW_ADDRESS,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record transfer event
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": ESCROW_ADDRESS, "value": 100},
            issuer_address,
        )

        # Execute batch
        # Assume: Not Create UTXO and Ledger
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO))).all()
        assert len(_utxo_list) == 0
        mock_func.assert_not_called()

    # <Normal_5>
    # Holder Changed
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_5(
        self,
        mock_func: MagicMock,
        processor: Processor,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(
            issuer_address,
            tradable_exchange_contract_address=EXCHANGE_ADDRESS,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        # Record transfer events and holder changed event
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": user_address_1, "to": EXCHANGE_ADDRESS, "value": 10},
            user_address_1,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": EXCHANGE_ADDRESS, "value": 10},
            issuer_address,
        )
        record_event(
            EXCHANGE_ADDRESS,
            "HolderChanged",
            {
                "token": token_address_1,
                "from": user_address_1,
                "to": user_address_2,
                "value": 10,
            },
            user_address_2,
        )

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Execute batch
        # Assume: Not Create UTXO and Ledger
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()

        assert len(_utxo_list) == 3
        _utxo: Any = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 0
        _utxo_block_number_1: Any = _utxo_list[1].block_number
        _utxo_block_timestamp_1: Any = _utxo_list[1].block_timestamp
        assert _utxo.block_number < _utxo_block_number_1
        assert _utxo.block_timestamp <= _utxo_block_timestamp_1
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo_block_number_2: Any = _utxo_list[2].block_number
        _utxo_block_timestamp_2: Any = _utxo_list[2].block_timestamp
        assert _utxo.block_number < _utxo_block_number_2
        assert _utxo.block_timestamp <= _utxo_block_timestamp_2
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10

        _utxo_block_number: Any = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        _utxo_block_number_1: Any = _utxo_list[1].block_number
        assert _utxo_block_number.latest_block_number >= _utxo_block_number_1

        mock_func.assert_has_calls([call(token_address=token_address_1, db=ANY)])

    # <Normal_6>
    # Additional Issue
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_6(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        token_address_2 = await create_fake_share_token_contract(issuer_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        _token_2.version = TokenVersion.V_25_09
        async_db.add(_token_2)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record additional issue events
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 70},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 80},
            issuer_address,
        )

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 2
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 70
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 80

        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_7>
    # Redeem
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_7(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        token_address_2 = await create_fake_share_token_contract(issuer_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        _token_2.version = TokenVersion.V_25_09
        async_db.add(_token_2)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record additional issue events
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 20},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 30},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 40},
            issuer_address,
        )

        # Before execute
        await processor.process()
        async_db.expire_all()

        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        # Record redeem events
        record_event(
            token_address_1,
            "Redeem",
            {"targetAddress": user_address_1, "amount": 20},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Redeem",
            {"targetAddress": user_address_2, "amount": 40},
            issuer_address,
        )

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 0
        _utxo = _utxo_list[1]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[2]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 0
        _utxo = _utxo_list[3]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30

        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_8_1>
    # Unlock(account_address!=recipient_address)
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_8_1(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]
        user_4 = default_eth_account("user4")
        lock_address = user_4["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        token_address_2 = await create_fake_share_token_contract(issuer_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        _token_2.version = TokenVersion.V_25_09
        async_db.add(_token_2)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record additional issue events
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 20},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 30},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 40},
            issuer_address,
        )

        # Before execute
        await processor.process()
        async_db.expire_all()

        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        # Record lock and force unlock events
        record_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": lock_address,
                "value": 5,
                "data": json.dumps({}),
            },
            user_address_1,
        )
        record_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": issuer_address,
                "value": 5,
                "data": json.dumps({}),
            },
            issuer_address,
        )
        record_event(
            token_address_2,
            "Lock",
            {
                "accountAddress": user_address_2,
                "recipientAddress": lock_address,
                "value": 10,
                "data": json.dumps({}),
            },
            user_address_2,
        )
        record_event(
            token_address_2,
            "ForceUnlock",
            {
                "accountAddress": user_address_2,
                "recipientAddress": issuer_address,
                "value": 10,
                "data": json.dumps({}),
            },
            issuer_address,
        )

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 6
        _utxo = _utxo_list[0]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 5
        _utxo = _utxo_list[1]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 20
        _utxo = _utxo_list[3]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40
        _utxo = _utxo_list[4]
        assert _utxo.account_address == issuer_address
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 5
        _utxo = _utxo_list[5]
        assert _utxo.account_address == issuer_address
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 10

        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_8_2>
    # Unlock(account_address==recipient_address)
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_8_2(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]
        user_4 = default_eth_account("user4")
        lock_address = user_4["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        token_address_2 = await create_fake_share_token_contract(issuer_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        _token_2.version = TokenVersion.V_25_09
        async_db.add(_token_2)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record additional issue events
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 20},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 30},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 40},
            issuer_address,
        )

        # Before execute
        await processor.process()
        async_db.expire_all()

        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        # Record lock and force unlock events
        record_event(
            token_address_1,
            "Lock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": lock_address,
                "value": 5,
                "data": json.dumps({}),
            },
            user_address_1,
        )
        record_event(
            token_address_1,
            "ForceUnlock",
            {
                "accountAddress": user_address_1,
                "recipientAddress": user_address_1,
                "value": 5,
                "data": json.dumps({}),
            },
            issuer_address,
        )
        record_event(
            token_address_2,
            "Lock",
            {
                "accountAddress": user_address_2,
                "recipientAddress": lock_address,
                "value": 10,
                "data": json.dumps({}),
            },
            user_address_2,
        )
        record_event(
            token_address_2,
            "ForceUnlock",
            {
                "accountAddress": user_address_2,
                "recipientAddress": user_address_2,
                "value": 10,
                "data": json.dumps({}),
            },
            issuer_address,
        )

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_9>
    # Transfer & Additional Issue & Redeem
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_9(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _utxo = UTXO()
        _utxo.transaction_hash = "deploy"
        _utxo.account_address = issuer_address
        _utxo.token_address = token_address_1
        _utxo.amount = 100
        _utxo.block_number = web3.eth.block_number
        _utxo.block_timestamp = None
        async_db.add(_utxo)

        await async_db.commit()

        await processor.process()
        async_db.expire_all()

        # Record events for the batch processor to consume
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": issuer_address, "amount": 1000000000000},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 90},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 1000000000000},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Redeem",
            {"targetAddress": user_address_2, "amount": 1000000000000},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Redeem",
            {"targetAddress": issuer_address, "amount": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Redeem",
            {"targetAddress": user_address_1, "amount": 90},
            issuer_address,
        )

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (
            await async_db.scalars(
                select(UTXO)
                .where(UTXO.account_address == issuer_address)
                .order_by(UTXO.created)
            )
        ).all()
        assert len(_utxo_list) == 2
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 0
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 0

        _utxo_list = (
            await async_db.scalars(
                select(UTXO)
                .where(UTXO.account_address == user_address_1)
                .order_by(UTXO.created)
            )
        ).all()
        assert len(_utxo_list) == 1
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 0

        _utxo_list = (
            await async_db.scalars(
                select(UTXO)
                .where(UTXO.account_address == user_address_2)
                .order_by(UTXO.created)
            )
        ).all()
        assert len(_utxo_list) == 1
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 0

        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_10_1>
    # ForceChangeLockedAccount(beforeAccountAddress!=afterAccountAddress)
    async def test_normal_10_1(self, processor: Processor, async_db: AsyncSession):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]
        user_4 = default_eth_account("user4")
        lock_address = user_4["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        token_address_2 = await create_fake_share_token_contract(issuer_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        _token_2.version = TokenVersion.V_25_09
        async_db.add(_token_2)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record additional issuance events
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 20},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 30},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 40},
            issuer_address,
        )

        # Before execute
        await processor.process()
        async_db.expire_all()

        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        # Record force change locked account events
        record_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "lockAddress": lock_address,
                "beforeAccountAddress": user_address_1,
                "afterAccountAddress": user_address_2,
                "value": 5,
            },
            issuer_address,
        )
        record_event(
            token_address_2,
            "ForceChangeLockedAccount",
            {
                "lockAddress": lock_address,
                "beforeAccountAddress": user_address_2,
                "afterAccountAddress": user_address_1,
                "value": 10,
            },
            issuer_address,
        )

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 6
        _utxo = _utxo_list[0]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 5
        _utxo = _utxo_list[1]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 20
        _utxo = _utxo_list[3]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40
        _utxo = _utxo_list[4]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 5
        _utxo = _utxo_list[5]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 10

        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_10_2>
    # ForceChangeLockedAccount(beforeAccountAddress==afterAccountAddress)
    async def test_normal_10_2(self, processor: Processor, async_db: AsyncSession):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        user_address_2 = user_3["address"]
        user_4 = default_eth_account("user4")
        lock_address = user_4["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        token_address_2 = await create_fake_share_token_contract(issuer_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        _token_2.version = TokenVersion.V_25_09
        async_db.add(_token_2)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # Record additional issuance events
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 10},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": user_address_1, "amount": 20},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 30},
            issuer_address,
        )
        record_event(
            token_address_2,
            "Issue",
            {"targetAddress": user_address_2, "amount": 40},
            issuer_address,
        )

        # Before execute
        await processor.process()
        async_db.expire_all()

        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        # Record force change locked account events
        record_event(
            token_address_1,
            "ForceChangeLockedAccount",
            {
                "lockAddress": lock_address,
                "beforeAccountAddress": user_address_1,
                "afterAccountAddress": user_address_1,
                "value": 5,
            },
            issuer_address,
        )
        record_event(
            token_address_2,
            "ForceChangeLockedAccount",
            {
                "lockAddress": lock_address,
                "beforeAccountAddress": user_address_2,
                "afterAccountAddress": user_address_2,
                "value": 10,
            },
            issuer_address,
        )

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_11_1>
    # Transfer with Annotation data
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_11_1(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        issuer = default_eth_account("user1")
        user = default_eth_account("user2")

        # Deploy Bond Token Contract
        token_address_1 = await create_fake_bond_token_contract(issuer["address"])

        # Prepare data
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = ""
        token_1.issuer_address = issuer["address"]
        token_1.token_address = token_address_1
        token_1.abi = {}
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer["address"]
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        utxo_1 = UTXO()
        utxo_1.transaction_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        utxo_1.account_address = issuer["address"]
        utxo_1.token_address = token_address_1
        utxo_1.amount = 30
        utxo_1.block_number = 123456
        utxo_1.block_timestamp = datetime.datetime(2025, 1, 18, 12, 34, 56, tzinfo=None)
        async_db.add(utxo_1)

        utxo_2 = UTXO()
        utxo_2.transaction_hash = (
            "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        utxo_2.account_address = issuer["address"]
        utxo_2.token_address = token_address_1
        utxo_2.amount = 70
        utxo_2.block_number = 234567
        utxo_2.block_timestamp = datetime.datetime(2025, 7, 18, 23, 45, 6, tzinfo=None)
        async_db.add(utxo_2)

        await async_db.commit()

        # Record transfer events with annotation data
        transaction_input = (
            "c0ffee00"
            + json.dumps({"purpose": "Reallocation"}, separators=(",", ":"))
            .encode("utf-8")
            .hex()
        )
        for _ in range(3):
            record_event(
                token_address_1,
                "Transfer",
                {"from": issuer["address"], "to": user["address"], "value": 20},
                issuer["address"],
                transaction_input=transaction_input,
            )

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 4

        utxo_issuer_1 = _utxo_list[0]
        assert (
            utxo_issuer_1.transaction_hash
            == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        assert utxo_issuer_1.account_address == issuer["address"]
        assert utxo_issuer_1.token_address == token_address_1
        assert utxo_issuer_1.amount == 0  # 30 - 20 (1st transfer) - 10 (2nd transfer)
        assert utxo_issuer_1.block_number == 123456
        assert utxo_issuer_1.block_timestamp == datetime.datetime(
            2025, 1, 18, 12, 34, 56
        )

        utxo_issuer_2 = _utxo_list[1]
        assert (
            utxo_issuer_2.transaction_hash
            == "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        assert utxo_issuer_2.account_address == issuer["address"]
        assert utxo_issuer_2.token_address == token_address_1
        assert utxo_issuer_2.amount == 40  # 70 - 10 (2nd transfer) - 20 (3rd transfer)
        assert utxo_issuer_2.block_number == 234567
        assert utxo_issuer_2.block_timestamp == datetime.datetime(
            2025, 7, 18, 23, 45, 6
        )

        utxo_user_1 = _utxo_list[2]
        assert (
            utxo_user_1.transaction_hash
            == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        assert utxo_user_1.account_address == user["address"]
        assert utxo_user_1.token_address == token_address_1
        assert utxo_user_1.amount == 30  # Reallocation amount #1
        assert utxo_user_1.block_number == 123456
        assert utxo_user_1.block_timestamp == datetime.datetime(
            2025, 1, 18, 12, 34, 56, tzinfo=None
        )

        utxo_user_2 = _utxo_list[3]
        assert (
            utxo_user_2.transaction_hash
            == "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        assert utxo_user_2.account_address == user["address"]
        assert utxo_user_2.token_address == token_address_1
        assert utxo_user_2.amount == 30  # Reallocation amount #2
        assert utxo_user_2.block_number == 234567
        assert utxo_user_2.block_timestamp == datetime.datetime(
            2025, 7, 18, 23, 45, 6, tzinfo=None
        )

        mock_func.assert_has_calls(
            [
                call(token_address=token_address_1, db=ANY),
            ]
        )

    # <Normal_11_2>
    # Transfer with Annotation data
    # Invalid Annotation data -> Normal transfer
    @pytest.mark.freeze_time("2025-07-21 21:00:00")
    @mock.patch("batch.processor_create_utxo.request_ledger_creation")
    async def test_normal_11_2(
        self, mock_func: MagicMock, processor: Processor, async_db: AsyncSession
    ):
        issuer = default_eth_account("user1")
        user = default_eth_account("user2")

        # Deploy Bond Token Contract
        token_address_1 = await create_fake_bond_token_contract(issuer["address"])

        # Prepare data
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = ""
        token_1.issuer_address = issuer["address"]
        token_1.token_address = token_address_1
        token_1.abi = {}
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer["address"]
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        utxo_1 = UTXO()
        utxo_1.transaction_hash = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        utxo_1.account_address = issuer["address"]
        utxo_1.token_address = token_address_1
        utxo_1.amount = 20
        utxo_1.block_number = 123456
        utxo_1.block_timestamp = datetime.datetime(2025, 1, 18, 12, 34, 56, tzinfo=None)
        utxo_1.created = datetime.datetime(2025, 1, 18, 12, 34, 56, tzinfo=None)
        async_db.add(utxo_1)

        utxo_2 = UTXO()
        utxo_2.transaction_hash = (
            "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        utxo_2.account_address = issuer["address"]
        utxo_2.token_address = token_address_1
        utxo_2.amount = 80
        utxo_2.block_number = 234567
        utxo_2.block_timestamp = datetime.datetime(2025, 7, 18, 23, 45, 6, tzinfo=None)
        utxo_2.created = datetime.datetime(2025, 7, 18, 23, 45, 6, tzinfo=None)
        async_db.add(utxo_2)

        await async_db.commit()

        # Record transfer event with annotation data (invalid)
        tx_hash, tx_receipt = record_event(
            token_address_1,
            "Transfer",
            {"from": issuer["address"], "to": user["address"], "value": 50},
            issuer["address"],
            transaction_input="c0ffee00" + "invalid_annotation_data".encode().hex(),
        )

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # assertion
        _utxo_list = (await async_db.scalars(select(UTXO).order_by(UTXO.created))).all()
        assert len(_utxo_list) == 3

        utxo_user_1 = _utxo_list[2]
        assert utxo_user_1.transaction_hash == tx_hash
        assert utxo_user_1.account_address == user["address"]
        assert utxo_user_1.token_address == token_address_1
        assert utxo_user_1.amount == 50
        assert utxo_user_1.block_number == tx_receipt["blockNumber"]
        assert utxo_user_1.block_timestamp is not None

        mock_func.assert_has_calls(
            [
                call(token_address=token_address_1, db=ANY),
            ]
        )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Web3 Error
    async def test_error_1(self, processor: Processor, async_db: AsyncSession):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # prepare data
        token_address_1 = await create_fake_bond_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        async_db.add(_token_1)

        await async_db.commit()

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Assertion
        _utxo_list = (await async_db.scalars(select(UTXO))).all()
        assert len(_utxo_list) == 0
        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block

    # <Error_2>
    # An invalid record including the number exceeding the database limit is found
    # => Discarded ledger creation request but saved UTXO data
    async def test_error_2(self, processor: Processor, async_db: AsyncSession):
        issuer = default_eth_account("user1")
        issuer_address = issuer["address"]

        user_1 = default_eth_account("user2")
        user_address_1 = user_1["address"]

        user_2 = default_eth_account("user3")
        user_address_2 = user_2["address"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_address_1 = await create_fake_share_token_contract(issuer_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_25_09
        _token_1.token_status = TokenStatus.SUCCEEDED
        async_db.add(_token_1)

        # Prepare data: LedgerTemplate
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "テスト項目1": "テスト値1",
                "テスト項目2": {
                    "テスト項目A": "テスト値2A",
                    "テスト項目B": "テスト値2B",
                },
                "テスト項目3": {
                    "テスト項目A": {"テスト項目a": "テスト値3Aa"},
                    "テスト項目B": "テスト値3B",
                },
            },
        ]
        _template.token_name = "受益権テスト"
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-テスト項目1": "f-テスト値1",
                "f-テスト項目2": {
                    "f-テスト項目A": "f-テスト値2A",
                    "f-テスト項目B": "f-テスト値2B",
                },
                "f-テスト項目3": {
                    "f-テスト項目A": {"f-テスト項目a": "f-テスト値3Aa"},
                    "f-テスト項目B": "f-テスト値3B",
                },
            },
        ]
        async_db.add(_template)

        # Record issuance and transfer events for the batch processor to consume
        record_event(
            token_address_1,
            "Issue",
            {"targetAddress": issuer_address, "amount": 1000000000000000000 - 100},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_1, "value": 100},
            issuer_address,
        )
        record_event(
            token_address_1,
            "Transfer",
            {"from": issuer_address, "to": user_address_2, "value": 200},
            issuer_address,
        )

        # Prepare data: LedgerDetailsTemplate
        _details_template = LedgerDetailsTemplate()
        _details_template.token_address = token_address_1
        _details_template.token_detail_type = "劣後受益権"
        _details_template.data_type = LedgerDataType.IBET_FIN
        _details_template.data_source = None
        async_db.add(_details_template)

        await async_db.commit()

        # Execute batch
        latest_block = web3.eth.block_number
        await processor.process()
        async_db.expire_all()

        # Assert
        _ledger_creation_list = (
            await async_db.scalars(select(LedgerCreationRequest))
        ).all()
        assert len(_ledger_creation_list) == 0
        _ledger_creation_data_list = (
            await async_db.scalars(select(LedgerCreationRequestData))
        ).all()
        assert len(_ledger_creation_data_list) == 0

        _utxo_list = (await async_db.scalars(select(UTXO))).all()
        assert len(_utxo_list) == 3
        _utxo_block_number = (
            await async_db.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        assert _utxo_block_number is not None
        assert _utxo_block_number.latest_block_number == latest_block
