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
from typing import Any, Sequence
from unittest import mock

import pytest
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceUnavailableError
from app.model.db import IDXBlockData, IDXBlockDataBlockNumber, IDXTxData
from batch import indexer_block_tx_data
from batch.indexer_block_tx_data import LOG, Processor
from config import CHAIN_ID
from tests.account_config import default_eth_account

TOKEN_ADDRESS = to_checksum_address("0x0000000000000000000000000000000000000201")
DEPLOYMENT_TX_HASH = HexBytes("0x" + "01" * 32)
TRANSFER_TX_HASH = HexBytes("0x" + "02" * 32)


class FakeAsyncEth:
    def __init__(
        self,
        block_numbers: list[int],
        blocks: dict[int, dict[str, Any]],
        block_number_error: Exception | None = None,
    ) -> None:
        self.block_numbers = block_numbers
        self.blocks = blocks
        self.block_number_error = block_number_error

    @property
    def block_number(self):
        return self._get_block_number()

    async def _get_block_number(self) -> int:
        if self.block_number_error is not None:
            raise self.block_number_error
        return self.block_numbers.pop(0)

    async def get_block(
        self, block_number: int, full_transactions: bool = False
    ) -> dict[str, Any]:
        return self.blocks[block_number]


class FakeAsyncWeb3:
    def __init__(
        self,
        block_numbers: list[int],
        blocks: dict[int, dict[str, Any]],
        block_number_error: Exception | None = None,
    ) -> None:
        self.eth = FakeAsyncEth(block_numbers, blocks, block_number_error)


def build_block(
    block_number: int, transactions: list[dict[str, Any]]
) -> dict[str, Any]:
    block_hash = HexBytes(f"0x{block_number:064x}")
    return {
        "number": block_number,
        "parentHash": HexBytes(f"0x{block_number - 1:064x}"),
        "sha3Uncles": HexBytes("0x" + "03" * 32),
        "miner": default_eth_account("user1")["address"],
        "stateRoot": HexBytes("0x" + "04" * 32),
        "transactionsRoot": HexBytes("0x" + "05" * 32),
        "receiptsRoot": HexBytes("0x" + "06" * 32),
        "logsBloom": HexBytes("0x" + "00" * 256),
        "difficulty": 0,
        "gasLimit": 30_000_000,
        "gasUsed": 21_000,
        "timestamp": 1_700_000_000 + block_number,
        "proofOfAuthorityData": HexBytes("0x"),
        "mixHash": HexBytes("0x" + "07" * 32),
        "nonce": HexBytes("0x" + "00" * 8),
        "hash": block_hash,
        "size": 1,
        "transactions": transactions,
    }


def build_transaction(
    block_number: int,
    transaction_hash: HexBytes,
    from_address: str,
    to_address: str | None,
) -> dict[str, Any]:
    return {
        "hash": transaction_hash,
        "blockHash": HexBytes(f"0x{block_number:064x}"),
        "blockNumber": block_number,
        "transactionIndex": 0,
        "from": from_address,
        "to": to_address,
        "input": HexBytes("0x"),
        "gas": 21_000,
        "gasPrice": 0,
        "value": 0,
        "nonce": 0,
    }


@pytest.fixture(scope="function")
def processor(
    async_db: AsyncSession, caplog: pytest.LogCaptureFixture
) -> Generator[indexer_block_tx_data.Processor, None, None]:
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield indexer_block_tx_data.Processor()
    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestProcessor:
    @staticmethod
    async def set_block_number(async_db: AsyncSession, block_number: int) -> None:
        indexed_block_number = IDXBlockDataBlockNumber()
        indexed_block_number.chain_id = str(CHAIN_ID)
        indexed_block_number.latest_block_number = block_number
        async_db.add(indexed_block_number)
        await async_db.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # Skip process: from_block > latest_block
    @pytest.mark.asyncio
    async def test_normal_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        before_block_number = 100
        await self.set_block_number(async_db, before_block_number)

        # Execute batch processing
        with mock.patch.object(
            indexer_block_tx_data,
            "web3",
            FakeAsyncWeb3([before_block_number], {}),
        ):
            await processor.process()

        # Assertion
        indexed_block = (
            await async_db.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
                .limit(1)
            )
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == before_block_number

        block_data = (await async_db.scalars(select(IDXBlockData))).all()
        assert len(block_data) == 0

        tx_data = (await async_db.scalars(select(IDXTxData))).all()
        assert len(tx_data) == 0

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "skip process: from_block > latest_block")
        )

    # Normal_2
    # BlockData: Empty block is generated
    @pytest.mark.asyncio
    async def test_normal_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        before_block_number = 100
        after_block_number = 101
        await self.set_block_number(async_db, before_block_number)

        # Execute batch processing
        with mock.patch.object(
            indexer_block_tx_data,
            "web3",
            FakeAsyncWeb3(
                [after_block_number],
                {after_block_number: build_block(after_block_number, [])},
            ),
        ):
            await processor.process()
        async_db.expire_all()

        # Assertion: Data
        indexed_block = (
            await async_db.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
                .limit(1)
            )
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == after_block_number

        block_data: Sequence[IDXBlockData] = (
            await async_db.scalars(select(IDXBlockData))
        ).all()
        assert len(block_data) == 1
        assert block_data[0].number == before_block_number + 1

        tx_data = (await async_db.scalars(select(IDXTxData))).all()
        assert len(tx_data) == 0

        # Assertion: Log
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                f"syncing from={before_block_number + 1}, to={after_block_number}",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "sync process has been completed")
        )

    # Normal_3_1
    # TxData: Contract deployment
    @pytest.mark.asyncio
    async def test_normal_3_1(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        deployer = default_eth_account("user1")

        before_block_number = 100
        after_block_number = 101
        await self.set_block_number(async_db, before_block_number)

        deployment_transaction = build_transaction(
            after_block_number,
            DEPLOYMENT_TX_HASH,
            deployer["address"],
            None,
        )

        # Execute batch processing
        with mock.patch.object(
            indexer_block_tx_data,
            "web3",
            FakeAsyncWeb3(
                [after_block_number],
                {
                    after_block_number: build_block(
                        after_block_number, [deployment_transaction]
                    )
                },
            ),
        ):
            await processor.process()
        async_db.expire_all()

        # Assertion
        indexed_block = (
            await async_db.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
                .limit(1)
            )
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == after_block_number

        block_data: Sequence[IDXBlockData] = (
            await async_db.scalars(select(IDXBlockData))
        ).all()
        assert len(block_data) == 1
        block_data_0 = block_data[0]
        assert block_data_0.number == before_block_number + 1
        assert block_data_0.transactions is not None
        assert len(block_data_0.transactions) == 1

        tx_data: Sequence[IDXTxData] = (await async_db.scalars(select(IDXTxData))).all()
        assert len(tx_data) == 1
        tx_data_0 = tx_data[0]
        assert tx_data_0.block_hash == block_data_0.hash
        assert tx_data_0.block_number == before_block_number + 1
        assert tx_data_0.transaction_index == 0
        assert tx_data_0.from_address == deployer["address"]
        assert tx_data_0.to_address is None

    # Normal_3_2
    # TxData: Transaction
    @pytest.mark.asyncio
    async def test_normal_3_2(
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        deployer = default_eth_account("user1")

        before_block_number = 100
        deployment_block_number = 101
        transfer_block_number = 102
        await self.set_block_number(async_db, before_block_number)

        deployment_transaction = build_transaction(
            deployment_block_number,
            DEPLOYMENT_TX_HASH,
            deployer["address"],
            None,
        )
        transfer_transaction = build_transaction(
            transfer_block_number,
            TRANSFER_TX_HASH,
            deployer["address"],
            TOKEN_ADDRESS,
        )

        # Execute batch processing
        with mock.patch.object(
            indexer_block_tx_data,
            "web3",
            FakeAsyncWeb3(
                [transfer_block_number],
                {
                    deployment_block_number: build_block(
                        deployment_block_number, [deployment_transaction]
                    ),
                    transfer_block_number: build_block(
                        transfer_block_number, [transfer_transaction]
                    ),
                },
            ),
        ):
            await processor.process()
        async_db.expire_all()

        # Assertion
        indexed_block = (
            await async_db.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
                .limit(1)
            )
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == transfer_block_number

        block_data: Sequence[IDXBlockData] = (
            await async_db.scalars(select(IDXBlockData).order_by(IDXBlockData.number))
        ).all()
        assert len(block_data) == 2

        assert block_data[0].number == deployment_block_number
        assert block_data[0].transactions is not None
        assert len(block_data[0].transactions) == 1

        assert block_data[1].number == transfer_block_number
        assert block_data[1].transactions is not None
        assert len(block_data[1].transactions) == 1

        tx_data: Sequence[IDXTxData] = (await async_db.scalars(select(IDXTxData))).all()
        assert len(tx_data) == 2

        assert tx_data[0].block_hash == block_data[0].hash
        assert tx_data[0].block_number == before_block_number + 1
        assert tx_data[0].transaction_index == 0
        assert tx_data[0].from_address == deployer["address"]
        assert tx_data[0].to_address is None

        assert tx_data[1].hash == TRANSFER_TX_HASH.to_0x_hex()
        assert tx_data[1].block_hash == block_data[1].hash
        assert tx_data[1].block_number == transfer_block_number
        assert tx_data[1].transaction_index == 0
        assert tx_data[1].from_address == deployer["address"]
        assert tx_data[1].to_address == TOKEN_ADDRESS

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1: ServiceUnavailable
    @pytest.mark.asyncio
    async def test_error_1(self, processor: Processor, async_db: AsyncSession):
        before_block_number = 100
        await self.set_block_number(async_db, before_block_number)

        # Execute batch processing
        with (
            mock.patch.object(
                indexer_block_tx_data,
                "web3",
                FakeAsyncWeb3([], {}, block_number_error=ServiceUnavailableError()),
            ),
            pytest.raises(ServiceUnavailableError),
        ):
            await processor.process()
            async_db.expire_all()

        # Assertion
        indexed_block = (
            await async_db.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
                .limit(1)
            )
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == before_block_number

        block_data = (await async_db.scalars(select(IDXBlockData))).all()
        assert len(block_data) == 0

        tx_data = (await async_db.scalars(select(IDXTxData))).all()
        assert len(tx_data) == 0

    # Error_2: SQLAlchemyError
    @pytest.mark.asyncio
    async def test_error_2(self, processor: Processor, async_db: AsyncSession):
        before_block_number = 100
        after_block_number = 101
        await self.set_block_number(async_db, before_block_number)

        # Execute batch processing
        with (
            mock.patch.object(
                indexer_block_tx_data,
                "web3",
                FakeAsyncWeb3(
                    [after_block_number],
                    {after_block_number: build_block(after_block_number, [])},
                ),
            ),
            mock.patch.object(AsyncSession, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.process()
            async_db.expire_all()

        # Assertion
        indexed_block = (
            await async_db.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
                .limit(1)
            )
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == before_block_number

        block_data = (await async_db.scalars(select(IDXBlockData))).all()
        assert len(block_data) == 0

        tx_data = (await async_db.scalars(select(IDXTxData))).all()
        assert len(tx_data) == 0
