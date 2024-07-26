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
from unittest import mock
from unittest.mock import MagicMock

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import RPCEndpoint

from app.exceptions import ServiceUnavailableError
from app.model.db import IDXBlockData, IDXBlockDataBlockNumber, IDXTxData
from batch import indexer_block_tx_data
from batch.indexer_block_tx_data import LOG
from config import CHAIN_ID, WEB3_HTTP_PROVIDER, ZERO_ADDRESS
from tests.account_config import config_eth_account
from tests.contract_utils import IbetStandardTokenUtils

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="function")
def processor(db, caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield indexer_block_tx_data.Processor()
    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestProcessor:
    @staticmethod
    def set_block_number(db, block_number):
        indexed_block_number = IDXBlockDataBlockNumber()
        indexed_block_number.chain_id = str(CHAIN_ID)
        indexed_block_number.latest_block_number = block_number
        db.add(indexed_block_number)
        db.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # Skip process: from_block > latest_block
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, db, caplog):
        before_block_number = web3.eth.block_number
        self.set_block_number(db, before_block_number)

        # Execute batch processing
        await processor.process()

        # Assertion
        indexed_block = db.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
            .limit(1)
        ).first()
        assert indexed_block.latest_block_number == before_block_number

        block_data = db.scalars(select(IDXBlockData)).all()
        assert len(block_data) == 0

        tx_data = db.scalars(select(IDXTxData)).all()
        assert len(tx_data) == 0

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "skip process: from_block > latest_block")
        )

    # Normal_2
    # BlockData: Empty block is generated
    @pytest.mark.asyncio
    async def test_normal_2(self, processor, db, caplog):
        before_block_number = web3.eth.block_number
        self.set_block_number(db, before_block_number)

        # Generate empty block
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Execute batch processing
        await processor.process()
        after_block_number = web3.eth.block_number

        # Assertion: Data
        indexed_block = db.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
            .limit(1)
        ).first()
        assert indexed_block.latest_block_number == after_block_number

        block_data: list[IDXBlockData] = db.scalars(select(IDXBlockData)).all()
        assert len(block_data) == 1
        assert block_data[0].number == before_block_number + 1

        tx_data = db.scalars(select(IDXTxData)).all()
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
    async def test_normal_3_1(self, processor, db, caplog):
        deployer = config_eth_account("user1")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer["keyfile_json"],
            password="password".encode("utf-8"),
        )

        before_block_number = web3.eth.block_number
        self.set_block_number(db, before_block_number)

        # Deploy contract
        IbetStandardTokenUtils.issue(
            tx_from=deployer["address"],
            private_key=deployer_pk,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": ZERO_ADDRESS,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )

        # Execute batch processing
        await processor.process()
        after_block_number = web3.eth.block_number

        # Assertion
        indexed_block = db.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
            .limit(1)
        ).first()
        assert indexed_block.latest_block_number == after_block_number

        block_data: list[IDXBlockData] = db.scalars(select(IDXBlockData)).all()
        assert len(block_data) == 1
        assert block_data[0].number == before_block_number + 1
        assert len(block_data[0].transactions) == 1

        tx_data: list[IDXTxData] = db.scalars(select(IDXTxData)).all()
        assert len(tx_data) == 1
        assert tx_data[0].block_hash == block_data[0].hash
        assert tx_data[0].block_number == before_block_number + 1
        assert tx_data[0].transaction_index == 0
        assert tx_data[0].from_address == deployer["address"]
        assert tx_data[0].to_address is None

    # Normal_3_2
    # TxData: Transaction
    @pytest.mark.asyncio
    async def test_normal_3_2(self, processor, db, caplog):
        deployer = config_eth_account("user1")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer["keyfile_json"],
            password="password".encode("utf-8"),
        )
        to_address = config_eth_account("user2")["address"]

        before_block_number = web3.eth.block_number
        self.set_block_number(db, before_block_number)

        # Deploy contract -> Transfer
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=deployer["address"],
            private_key=deployer_pk,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": ZERO_ADDRESS,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )
        tx_hash = IbetStandardTokenUtils.transfer(
            contract_address=token_contract.address,
            tx_from=deployer["address"],
            private_key=deployer_pk,
            args=[to_address, 1],
        )

        # Execute batch processing
        await processor.process()
        after_block_number = web3.eth.block_number

        # Assertion
        indexed_block = db.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
            .limit(1)
        ).first()
        assert indexed_block.latest_block_number == after_block_number

        block_data: list[IDXBlockData] = db.scalars(
            select(IDXBlockData).order_by(IDXBlockData.number)
        ).all()
        assert len(block_data) == 2

        assert block_data[0].number == before_block_number + 1
        assert len(block_data[0].transactions) == 1

        assert block_data[1].number == before_block_number + 2
        assert len(block_data[1].transactions) == 1

        tx_data: list[IDXTxData] = db.scalars(select(IDXTxData)).all()
        assert len(tx_data) == 2

        assert tx_data[0].block_hash == block_data[0].hash
        assert tx_data[0].block_number == before_block_number + 1
        assert tx_data[0].transaction_index == 0
        assert tx_data[0].from_address == deployer["address"]
        assert tx_data[0].to_address is None

        assert tx_data[1].hash == tx_hash
        assert tx_data[1].block_hash == block_data[1].hash
        assert tx_data[1].block_number == before_block_number + 2
        assert tx_data[1].transaction_index == 0
        assert tx_data[1].from_address == deployer["address"]
        assert tx_data[1].to_address == token_contract.address

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1: ServiceUnavailable
    @pytest.mark.asyncio
    async def test_error_1(self, processor, db):
        before_block_number = web3.eth.block_number
        self.set_block_number(db, before_block_number)

        # Execute batch processing
        with (
            mock.patch(
                "web3.providers.rpc.async_rpc.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailableError()),
            ),
            pytest.raises(ServiceUnavailableError),
        ):
            await processor.process()

        # Assertion
        indexed_block = db.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
            .limit(1)
        ).first()
        assert indexed_block.latest_block_number == before_block_number

        block_data = db.scalars(select(IDXBlockData)).all()
        assert len(block_data) == 0

        tx_data = db.scalars(select(IDXTxData)).all()
        assert len(tx_data) == 0

    # Error_2: SQLAlchemyError
    @pytest.mark.asyncio
    async def test_error_2(self, processor, db):
        before_block_number = web3.eth.block_number
        self.set_block_number(db, before_block_number)

        # Generate empty block
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Execute batch processing
        with (
            mock.patch.object(AsyncSession, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.process()

        # Assertion
        indexed_block = db.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
            .limit(1)
        ).first()
        assert indexed_block.latest_block_number == before_block_number

        block_data = db.scalars(select(IDXBlockData)).all()
        assert len(block_data) == 0

        tx_data = db.scalars(select(IDXTxData)).all()
        assert len(tx_data) == 0
