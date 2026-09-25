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
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, cast
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import Contract
from web3.types import TxReceipt

import batch.indexer_dvp_delivery as indexer_dvp_delivery
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    Account,
    AccountRsaStatus,
    DeliveryStatus,
    DVPAgentAccount,
    DVPAsyncProcess,
    IDXDelivery,
    IDXDeliveryBlockNumber,
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
from batch.indexer_dvp_delivery import LOG, Processor, main
from config import ZERO_ADDRESS
from tests.account_config import default_eth_account

DVP_ADDRESS = to_checksum_address("0x" + "0c" * 20)
ESCROW_ADDRESS = to_checksum_address("0x" + "0d" * 20)


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
    def block_number(self):
        return self._get_block_number()

    async def _get_block_number(self) -> int:
        return self.chain.latest_block

    async def get_block(self, block_number: int) -> dict[str, int]:
        return {"timestamp": 1_700_000_000 + block_number}


class FakeSyncWeb3:
    def __init__(self, chain: FakeChain) -> None:
        self.eth = FakeSyncEth(chain)


_CHAIN = FakeChain()
web3 = FakeSyncWeb3(_CHAIN)
_EVENTS: dict[tuple[str, str], list[dict[str, Any]]] = {}
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


def record_dvp_event(
    exchange_address: str,
    event_name: str,
    token_address: str,
    buyer_address: str,
    seller_address: str,
    amount: int,
    agent_address: str,
    data: str,
    delivery_id: int = 1,
) -> tuple[str, TxReceipt]:
    block_number = _CHAIN.mine()
    transaction_hash = f"0x{_CHAIN.transaction_index:064x}"
    add_event(
        exchange_address,
        event_name,
        transaction_hash,
        block_number,
        {
            "deliveryId": delivery_id,
            "token": token_address,
            "buyer": buyer_address,
            "seller": seller_address,
            "amount": amount,
            "agent": agent_address,
            "data": data,
        },
    )
    return transaction_hash, cast(TxReceipt, {"blockNumber": block_number})


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
) -> Generator[Processor, None, None]:
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
    _TOKEN_EXCHANGES.clear()

    monkeypatch.setattr(indexer_dvp_delivery, "web3", FakeAsyncWeb3(_CHAIN))

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
def ibet_security_token_dvp_contract() -> FakeContract:
    return FakeContract(DVP_ADDRESS)


@pytest.fixture(scope="function")
def ibet_security_token_escrow_contract() -> FakeContract:
    return FakeContract(ESCROW_ADDRESS)


async def create_fake_bond_token_contract(
    tradable_exchange_contract_address: str | None = None,
) -> FakeContract:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x900 + _token_counter:040x}")
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    return FakeContract(token_address)


async def create_fake_share_token_contract(
    tradable_exchange_contract_address: str | None = None,
) -> FakeContract:
    global _token_counter
    _token_counter += 1
    token_address = to_checksum_address(f"0x{0x900 + _token_counter:040x}")
    _TOKEN_EXCHANGES[token_address] = tradable_exchange_contract_address or ZERO_ADDRESS
    return FakeContract(token_address)


def _get_block_number(tx_receipt: TxReceipt) -> int:
    block_number = tx_receipt.get("blockNumber")
    assert block_number is not None
    return block_number


async def _get_block_timestamp(tx_receipt: TxReceipt) -> datetime:
    block = await web3.eth.get_block(_get_block_number(tx_receipt))
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
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.keyfile = default_eth_account("user1")["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.is_deleted = False
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
        token_1.token_status = TokenStatus.PENDING
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        await async_db.commit()

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 0

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is None

    # <Normal_1_2>
    # No event log
    #   - Issued tokens but no exchange address is set.
    @pytest.mark.asyncio
    async def test_normal_1_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.keyfile = default_eth_account("user1")["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.rsa_private_key = user_1["rsa_private_key"]
        account.rsa_public_key = user_1["rsa_public_key"]
        account.rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_status = 3
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

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 0

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is None

    # <Normal_1_3>
    # No event log
    #   - Issued tokens but the exchange contract other than DVP contract is set.
    @pytest.mark.asyncio
    async def test_normal_1_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.keyfile = default_eth_account("user1")["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.rsa_private_key = user_1["rsa_private_key"]
        account.rsa_public_key = user_1["rsa_public_key"]
        account.rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_status = 3
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

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 0

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert _idx_delivery_block_number.latest_block_number == block_number
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_escrow_contract.address
        )

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_escrow_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_1_1>
    # Event log
    #   - Exchange: CreateDelivery (seller is related to issuer)
    # No data encryption
    @pytest.mark.asyncio
    async def test_normal_2_1_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is True
        assert _delivery.status == DeliveryStatus.DELIVERY_CREATED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_1_2>
    # Event log
    #   - Exchange: CreateDelivery (seller is related to issuer)
    # Data encryption
    @mock.patch(
        "batch.indexer_dvp_delivery.DVP_DATA_ENCRYPTION_MODE",
        "aes-256-cbc",
    )
    @mock.patch(
        "batch.indexer_dvp_delivery.DVP_DATA_ENCRYPTION_KEY",
        "YFX99ldItl93r9uy2s1lgAY/p9OtcaacM6R+dqvf2Rc=",
    )
    @pytest.mark.asyncio
    async def test_normal_2_1_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            '{"encryption_algorithm": "aes-256-cbc", "encryption_key_ref": "local", "settlement_service_type": "test_service", "data": "WFeOcAzY6erkNbbAD+m5YCUlw7HA6BxcWKsSPIuk6JY="}',
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "test_message"
        assert _delivery.settlement_service_type == "test_service"
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is True
        assert _delivery.status == DeliveryStatus.DELIVERY_CREATED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_1_3>
    # Event log
    #   - Exchange: CreateDelivery (agent is related to DVPAgentAccount)
    # Data encryption
    @mock.patch(
        "batch.indexer_dvp_delivery.DVP_DATA_ENCRYPTION_MODE",
        "aes-256-cbc",
    )
    @mock.patch(
        "batch.indexer_dvp_delivery.DVP_DATA_ENCRYPTION_KEY",
        "YFX99ldItl93r9uy2s1lgAY/p9OtcaacM6R+dqvf2Rc=",
    )
    @pytest.mark.asyncio
    async def test_normal_2_1_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : DVPAgentAccount
        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = "test_keyfile_0"  # type: ignore
        dvp_agent_account.eoa_password = "test_password_0"
        dvp_agent_account.dedicated_agent_id = "test_agent_id_0"
        async_db.add(dvp_agent_account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            ZERO_ADDRESS,
            user_address_1,
            30,
            agent_address,
            '{"encryption_algorithm": "aes-256-cbc", "encryption_key_ref": "local", "settlement_service_type": "test_service", "data": "WFeOcAzY6erkNbbAD+m5YCUlw7HA6BxcWKsSPIuk6JY="}',
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == ZERO_ADDRESS
        assert _delivery.seller_address == user_address_1
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "test_message"
        assert _delivery.settlement_service_type == "test_service"
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is True
        assert _delivery.status == DeliveryStatus.DELIVERY_CREATED
        assert _delivery.dedicated_agent_id == "test_agent_id_0"

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_2_1>
    # Event log
    #   - Exchange: CancelDelivery (from issuer)
    @pytest.mark.asyncio
    async def test_normal_2_2_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event and a DeliveryCanceled event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_2, tx_receipt_2 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCanceled",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp == await _get_block_timestamp(
            tx_receipt_2
        )
        assert _delivery.cancel_transaction_hash == tx_hash_2
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_CANCELED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list) == 1
        _async_process: DVPAsyncProcess = _async_process_list[0]
        assert _async_process.id == 1
        assert _async_process.issuer_address == issuer_address
        assert _async_process.process_type == "CancelDelivery"
        assert _async_process.process_status == 1
        assert (
            _async_process.dvp_contract_address
            == ibet_security_token_dvp_contract.address
        )
        assert _async_process.token_address == token_address_1
        assert _async_process.seller_address == issuer_address
        assert _async_process.buyer_address == user_address_1
        assert _async_process.amount == 30
        assert _async_process.agent_address == agent_address
        assert _async_process.data is None
        assert _async_process.delivery_id == _delivery.delivery_id
        assert _async_process.step == 0
        assert _async_process.step_tx_hash == tx_hash_2
        assert _async_process.step_tx_status == "done"
        assert _async_process.revert_tx_hash is None
        assert _async_process.revert_tx_status is None

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_2_2>
    # Event log
    #   - Exchange: CancelDelivery (from buyer)
    @pytest.mark.asyncio
    async def test_normal_2_2_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event and a DeliveryCanceled event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_2, tx_receipt_2 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCanceled",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp == await _get_block_timestamp(
            tx_receipt_2
        )
        assert _delivery.cancel_transaction_hash == tx_hash_2
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_CANCELED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list)
        _async_process: DVPAsyncProcess = _async_process_list[0]
        assert _async_process.id == 1
        assert _async_process.issuer_address == issuer_address
        assert _async_process.process_type == "CancelDelivery"
        assert _async_process.process_status == 1
        assert (
            _async_process.dvp_contract_address
            == ibet_security_token_dvp_contract.address
        )
        assert _async_process.token_address == token_address_1
        assert _async_process.seller_address == issuer_address
        assert _async_process.buyer_address == user_address_1
        assert _async_process.amount == 30
        assert _async_process.agent_address == agent_address
        assert _async_process.data is None
        assert _async_process.delivery_id == _delivery.delivery_id
        assert _async_process.step == 0
        assert _async_process.step_tx_hash == tx_hash_2
        assert _async_process.step_tx_status == "done"
        assert _async_process.revert_tx_hash is None
        assert _async_process.revert_tx_status is None

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_3>
    # Event log
    #   - Exchange: ConfirmDelivery (from buyer)
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event and a DeliveryConfirmed event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_2, tx_receipt_2 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryConfirmed",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp == await _get_block_timestamp(
            tx_receipt_2
        )
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is True
        assert _delivery.valid is True
        assert _delivery.status == DeliveryStatus.DELIVERY_CONFIRMED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        _notifications = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notifications) == 1
        assert _notifications[0].issuer_address == issuer_address
        assert _notifications[0].priority == 0
        assert _notifications[0].type == NotificationType.DVP_DELIVERY_INFO
        assert _notifications[0].code == 0
        assert _notifications[0].metainfo == {
            "exchange_address": ibet_security_token_dvp_contract.address,
            "delivery_id": 1,
            "token_address": token_address_1,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "seller_address": issuer_address,
            "buyer_address": user_address_1,
            "agent_address": agent_address,
            "amount": 30,
        }

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_4_1>
    # Event log
    #   - Exchange: FinishDelivery (from agent)
    #   - Seller (Buyer not exist)
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_4_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event, a DeliveryConfirmed event, and a DeliveryFinished event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_2, tx_receipt_2 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryConfirmed",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_3, tx_receipt_3 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryFinished",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp == await _get_block_timestamp(
            tx_receipt_2
        )
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp == await _get_block_timestamp(
            tx_receipt_3
        )
        assert _delivery.finish_transaction_hash == tx_hash_3
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is True
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_FINISHED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        _notifications = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notifications) == 2
        assert _notifications[0].issuer_address == issuer_address
        assert _notifications[0].priority == 0
        assert _notifications[0].type == NotificationType.DVP_DELIVERY_INFO
        assert _notifications[0].code == 0
        assert _notifications[0].metainfo == {
            "exchange_address": ibet_security_token_dvp_contract.address,
            "delivery_id": 1,
            "token_address": token_address_1,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "seller_address": issuer_address,
            "buyer_address": user_address_1,
            "agent_address": agent_address,
            "amount": 30,
        }
        assert _notifications[1].issuer_address == issuer_address
        assert _notifications[1].priority == 0
        assert _notifications[1].type == NotificationType.DVP_DELIVERY_INFO
        assert _notifications[1].code == 1
        assert _notifications[1].metainfo == {
            "exchange_address": ibet_security_token_dvp_contract.address,
            "delivery_id": 1,
            "token_address": token_address_1,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "seller_address": issuer_address,
            "buyer_address": user_address_1,
            "agent_address": agent_address,
            "amount": 30,
        }

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list) == 0

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_4_2>
    # Event log
    #   - Exchange: FinishDelivery (from agent)
    #   - Buyer exists
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_4_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = user_address_1
        account.keyfile = user_2["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event, a DeliveryConfirmed event, and a DeliveryFinished event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_2, tx_receipt_2 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryConfirmed",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_3, tx_receipt_3 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryFinished",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp == await _get_block_timestamp(
            tx_receipt_2
        )
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp == await _get_block_timestamp(
            tx_receipt_3
        )
        assert _delivery.finish_transaction_hash == tx_hash_3
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is True
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_FINISHED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        _notifications = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notifications) == 2
        assert _notifications[0].issuer_address == issuer_address
        assert _notifications[0].priority == 0
        assert _notifications[0].type == NotificationType.DVP_DELIVERY_INFO
        assert _notifications[0].code == 0
        assert _notifications[0].metainfo == {
            "exchange_address": ibet_security_token_dvp_contract.address,
            "delivery_id": 1,
            "token_address": token_address_1,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "seller_address": issuer_address,
            "buyer_address": user_address_1,
            "agent_address": agent_address,
            "amount": 30,
        }
        assert _notifications[1].issuer_address == issuer_address
        assert _notifications[1].priority == 0
        assert _notifications[1].type == NotificationType.DVP_DELIVERY_INFO
        assert _notifications[1].code == 1
        assert _notifications[1].metainfo == {
            "exchange_address": ibet_security_token_dvp_contract.address,
            "delivery_id": 1,
            "token_address": token_address_1,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "seller_address": issuer_address,
            "buyer_address": user_address_1,
            "agent_address": agent_address,
            "amount": 30,
        }

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list) == 1
        _async_process: DVPAsyncProcess = _async_process_list[0]
        assert _async_process.id == 1
        assert _async_process.issuer_address == user_address_1
        assert _async_process.process_type == "FinishDelivery"
        assert _async_process.process_status == 1
        assert (
            _async_process.dvp_contract_address
            == ibet_security_token_dvp_contract.address
        )
        assert _async_process.token_address == token_address_1
        assert _async_process.seller_address == issuer_address
        assert _async_process.buyer_address == user_address_1
        assert _async_process.amount == 30
        assert _async_process.agent_address == agent_address
        assert _async_process.data is None
        assert _async_process.delivery_id == _delivery.delivery_id
        assert _async_process.step == 0
        assert _async_process.step_tx_hash == tx_hash_3
        assert _async_process.step_tx_status == "done"
        assert _async_process.revert_tx_hash is None
        assert _async_process.revert_tx_status is None

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_5>
    # Event log
    #   - Exchange: AbortDelivery (from agent)
    @pytest.mark.asyncio
    async def test_normal_2_5(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event, a DeliveryConfirmed event, and a DeliveryAborted event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_2, tx_receipt_2 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryConfirmed",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_3, tx_receipt_3 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryAborted",
            token_address_1,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery: IDXDelivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp == await _get_block_timestamp(
            tx_receipt_2
        )
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp == await _get_block_timestamp(
            tx_receipt_3
        )
        assert _delivery.abort_transaction_hash == tx_hash_3
        assert _delivery.confirmed is True
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_ABORTED

        _idx_delivery_block_number = (
            await async_db.scalars(select(IDXDeliveryBlockNumber).limit(1))
        ).first()
        assert _idx_delivery_block_number is not None
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list) == 1
        _async_process: DVPAsyncProcess = _async_process_list[0]
        assert _async_process.id == 1
        assert _async_process.issuer_address == issuer_address
        assert _async_process.process_type == "AbortDelivery"
        assert _async_process.process_status == 1
        assert (
            _async_process.dvp_contract_address
            == ibet_security_token_dvp_contract.address
        )
        assert _async_process.token_address == token_address_1
        assert _async_process.seller_address == issuer_address
        assert _async_process.buyer_address == user_address_1
        assert _async_process.amount == 30
        assert _async_process.agent_address == agent_address
        assert _async_process.data is None
        assert _async_process.delivery_id == _delivery.delivery_id
        assert _async_process.step == 0
        assert _async_process.step_tx_hash == tx_hash_3
        assert _async_process.step_tx_status == "done"
        assert _async_process.revert_tx_hash is None
        assert _async_process.revert_tx_status is None

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_3>
    # Multi Exchange
    @pytest.mark.asyncio
    async def test_normal_3(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_escrow_contract: Contract,
        ibet_security_token_dvp_contract: Contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

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

        # Prepare data : Token
        token_contract_2 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
        )
        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        # Record a DeliveryCreated event, a DeliveryConfirmed event, and a DeliveryAborted event
        tx_hash_1, tx_receipt_1 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryCreated",
            token_address_2,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_2, tx_receipt_2 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryConfirmed",
            token_address_2,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )
        tx_hash_3, tx_receipt_3 = record_dvp_event(
            ibet_security_token_dvp_contract.address,
            "DeliveryAborted",
            token_address_2,
            user_address_1,
            issuer_address,
            30,
            agent_address,
            "." * 1000,
        )

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _delivery_list = (await async_db.scalars(select(IDXDelivery))).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_2
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        assert _delivery.settlement_service_type is None
        assert _delivery.create_blocktimestamp == await _get_block_timestamp(
            tx_receipt_1
        )
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp == await _get_block_timestamp(
            tx_receipt_2
        )
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp == await _get_block_timestamp(
            tx_receipt_3
        )
        assert _delivery.abort_transaction_hash == tx_hash_3
        assert _delivery.confirmed is True
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_ABORTED

        _idx_delivery_block_number = (
            await async_db.scalars(
                select(IDXDeliveryBlockNumber).where(
                    IDXDeliveryBlockNumber.exchange_address
                    == ibet_security_token_escrow_contract.address
                )
            )
        ).first()
        assert _idx_delivery_block_number is not None
        assert _idx_delivery_block_number.latest_block_number == block_number

        _idx_delivery_block_number = (
            await async_db.scalars(
                select(IDXDeliveryBlockNumber).where(
                    IDXDeliveryBlockNumber.exchange_address
                    == ibet_security_token_dvp_contract.address
                )
            )
        ).first()
        assert _idx_delivery_block_number is not None
        assert _idx_delivery_block_number.latest_block_number == block_number

        _notifications = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notifications) == 1
        assert _notifications[0].issuer_address == issuer_address
        assert _notifications[0].priority == 0
        assert _notifications[0].type == NotificationType.DVP_DELIVERY_INFO
        assert _notifications[0].code == 0
        assert _notifications[0].metainfo == {
            "exchange_address": ibet_security_token_dvp_contract.address,
            "delivery_id": 1,
            "token_address": token_address_2,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "seller_address": issuer_address,
            "buyer_address": user_address_1,
            "agent_address": agent_address,
            "amount": 30,
        }

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_escrow_contract.address}",
                )
            )
            == 1
        )

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_4>
    # If block number processed in batch is equal or greater than current block number,
    # batch will output a log "skip process".
    @mock.patch("web3.eth.Eth.block_number", 100)
    @pytest.mark.asyncio
    async def test_normal_4(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
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
        token_contract_1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 100
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        async_db.add(_idx_delivery_block_number)

        await async_db.commit()

        await processor.sync_new_logs()
        assert (
            caplog.record_tuples.count((LOG.name, logging.DEBUG, "skip process")) == 1
        )

    # <Normal_5>
    # Newly tokens added
    @pytest.mark.asyncio
    async def test_normal_6(
        self,
        processor: Processor,
        async_db: AsyncSession,
        ibet_security_token_dvp_contract: Contract,
        ibet_security_token_escrow_contract: Contract,
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
        token_contract1 = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address
        )
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
        assert len(processor.token_list) == 1
        assert len(processor.exchange_list) == 1

        # Prepare additional token
        token_contract2 = await create_fake_share_token_contract(
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address
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
        assert len(processor.token_list) == 2
        assert len(processor.exchange_list) == 2

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
        token_contract = await create_fake_bond_token_contract(
            tradable_exchange_contract_address=DVP_ADDRESS
        )
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
            patch("batch.indexer_dvp_delivery.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                IbetStraightBondContract,
                "get",
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
            patch("batch.indexer_dvp_delivery.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                AsyncSession, "commit", side_effect=SQLAlchemyError(code="dbapi")
            ),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert "A database error has occurred: code=dbapi" in caplog.text
        caplog.clear()
