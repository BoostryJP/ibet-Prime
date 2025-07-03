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
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from web3.types import RPCEndpoint

from app.model.db import (
    Account,
    IDXEthIbetWSTTrade,
    IDXEthIbetWSTTradeBlockNumber,
    IDXEthIbetWSTTradeState,
    Token,
    TokenType,
    TokenVersion,
)
from app.model.eth import IbetWSTTrade
from app.utils.eth_contract_utils import EthWeb3
from batch.indexer_eth_wst_trades import Processor


@pytest.fixture(scope="function")
def processor(async_db, caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor()
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    # Test IbetWST and token addresses
    ibet_wst_address_1 = "0x1234567890123456789012345678900000000001"
    ibet_wst_address_2 = "0x1234567890123456789012345678900000000002"

    # Test ibet token addresses
    ibet_token_address_1 = "0x1234567890123456789012345678900000000010"
    ibet_token_address_2 = "0x1234567890123456789012345678900000000020"

    # Test issuer addresses
    issuer_address_1 = "0x1234567890123456789012345678900000000100"
    issuer_address_2 = "0x1234567890123456789012345678900000000200"

    # Test user addresses
    user_address_1 = "0x1234567890123456789012345678900000001000"
    user_address_2 = "0x1234567890123456789012345678900000002000"

    # Test SC token addresses
    sc_token_address_1 = "0x1234567890123456789012345678900000001001"
    sc_token_address_2 = "0x1234567890123456789012345678900000002001"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # No target tokens to process
    # - The synchronized block number is updated.
    async def test_normal_1_1(self, processor, async_db, caplog):
        # Generate empty block
        await EthWeb3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Prepare test data
        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer_address_1
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = False  # No IbetWST deployed
        async_db.add(token)

        account = Account()
        account.issuer_address = self.issuer_address_1
        account.is_deleted = False
        async_db.add(account)

        await async_db.commit()

        # Run target process
        latest_finalized_block = await processor.get_finalized_block_number()
        await processor.sync_events()
        async_db.expire_all()

        # Check IDXEthIbetWSTTradeBlockNumber
        synced_block_number = (
            await async_db.scalars(select(IDXEthIbetWSTTradeBlockNumber).limit(1))
        ).first()
        assert synced_block_number.latest_block_number == latest_finalized_block

        # Check log
        assert caplog.messages == [
            f"Syncing IbetWST trade events from=1, to={latest_finalized_block}",
            "Sync completed successfully",
        ]

    # <Normal_1_2>
    # Issuer is deleted
    # - Not included in the processing target.
    # - The synchronized block number is updated.
    async def test_normal_1_2(self, processor, async_db, caplog):
        # Generate empty block
        await EthWeb3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Prepare test data
        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer_address_1
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        account = Account()
        account.issuer_address = self.issuer_address_1
        account.is_deleted = True  # Account is deleted
        async_db.add(account)

        await async_db.commit()

        # Run target process
        latest_finalized_block = await processor.get_finalized_block_number()
        await processor.sync_events()
        async_db.expire_all()

        # Check IDXEthIbetWSTTradeBlockNumber
        synced_block_number = (
            await async_db.scalars(select(IDXEthIbetWSTTradeBlockNumber).limit(1))
        ).first()
        assert synced_block_number.latest_block_number == latest_finalized_block

        # Check log
        assert caplog.messages == [
            f"Syncing IbetWST trade events from=1, to={latest_finalized_block}",
            "Sync completed successfully",
        ]

    # <Normal_2_1>
    # "TradeRequested" event exists
    # - Trade data is updated.
    @mock.patch(
        "batch.indexer_eth_wst_trades.EthAsyncContractUtils.get_event_logs",
        AsyncMock(
            side_effect=[
                [{"args": {"index": 1}}],  # "TradeRequested" event exists
                [],  # No "TradeAccepted" event
                [],  # No "TradeCancelled" event
                [],  # No "TradeRejected" event
            ]
        ),
    )
    @mock.patch(
        "batch.indexer_eth_wst_trades.IbetWST.get_trade",
        AsyncMock(
            return_value=IbetWSTTrade(
                seller_st_account=user_address_1,
                buyer_st_account=user_address_2,
                sc_token_address=sc_token_address_1,
                seller_sc_account=user_address_1,
                buyer_sc_account=user_address_2,
                st_value=1000,
                sc_value=2000,
                state="Pending",
                memo="",
            )
        ),
    )
    async def test_normal_2_1(self, processor, async_db, caplog):
        # Generate empty block
        await EthWeb3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Prepare test data
        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer_address_1
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        account = Account()
        account.issuer_address = self.issuer_address_1
        account.is_deleted = False
        async_db.add(account)

        await async_db.commit()

        # Run target process
        latest_finalized_block = await processor.get_finalized_block_number()
        await processor.sync_events()
        async_db.expire_all()

        # Check IDXEthIbetWSTTrade data
        wst_trade = (
            await async_db.scalars(
                select(IDXEthIbetWSTTrade)
                .where(IDXEthIbetWSTTrade.ibet_wst_address == self.ibet_wst_address_1)
                .limit(1)
            )
        ).first()
        assert wst_trade.index == 1
        assert wst_trade.seller_st_account_address == self.user_address_1
        assert wst_trade.buyer_st_account_address == self.user_address_2
        assert wst_trade.sc_token_address == self.sc_token_address_1
        assert wst_trade.seller_sc_account_address == self.user_address_1
        assert wst_trade.buyer_sc_account_address == self.user_address_2
        assert wst_trade.st_value == 1000
        assert wst_trade.sc_value == 2000
        assert wst_trade.state == IDXEthIbetWSTTradeState.PENDING
        assert wst_trade.memo == ""

        # Check IDXEthIbetWSTTradeBlockNumber
        synced_block_number = (
            await async_db.scalars(select(IDXEthIbetWSTTradeBlockNumber).limit(1))
        ).first()
        assert synced_block_number.latest_block_number == latest_finalized_block

        # Check log
        assert caplog.messages == [
            f"Syncing IbetWST trade events from=1, to={latest_finalized_block}",
            "Sync completed successfully",
        ]

    # <Normal_2_2>
    # "TradeAccepted" event exists
    # - Trade data is updated.
    @mock.patch(
        "batch.indexer_eth_wst_trades.EthAsyncContractUtils.get_event_logs",
        AsyncMock(
            side_effect=[
                [],  # No "TradeRequested" event
                [{"args": {"index": 1}}],  # "TradeAccepted" event exists
                [],  # No "TradeCancelled" event
                [],  # No "TradeRejected" event
            ]
        ),
    )
    @mock.patch(
        "batch.indexer_eth_wst_trades.IbetWST.get_trade",
        AsyncMock(
            return_value=IbetWSTTrade(
                seller_st_account=user_address_1,
                buyer_st_account=user_address_2,
                sc_token_address=sc_token_address_1,
                seller_sc_account=user_address_1,
                buyer_sc_account=user_address_2,
                st_value=1000,
                sc_value=2000,
                state="Executed",
                memo="",
            )
        ),
    )
    async def test_normal_2_2(self, processor, async_db, caplog):
        # Generate empty block
        await EthWeb3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Prepare test data
        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer_address_1
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        account = Account()
        account.issuer_address = self.issuer_address_1
        account.is_deleted = False
        async_db.add(account)

        await async_db.commit()

        # Run target process
        latest_finalized_block = await processor.get_finalized_block_number()
        await processor.sync_events()
        async_db.expire_all()

        # Check IDXEthIbetWSTTradeBlockNumber
        synced_block_number = (
            await async_db.scalars(select(IDXEthIbetWSTTradeBlockNumber).limit(1))
        ).first()
        assert synced_block_number.latest_block_number == latest_finalized_block

        wst_trade = (
            await async_db.scalars(
                select(IDXEthIbetWSTTrade)
                .where(IDXEthIbetWSTTrade.ibet_wst_address == self.ibet_wst_address_1)
                .limit(1)
            )
        ).first()
        assert wst_trade.index == 1
        assert wst_trade.seller_st_account_address == self.user_address_1
        assert wst_trade.buyer_st_account_address == self.user_address_2
        assert wst_trade.sc_token_address == self.sc_token_address_1
        assert wst_trade.seller_sc_account_address == self.user_address_1
        assert wst_trade.buyer_sc_account_address == self.user_address_2
        assert wst_trade.st_value == 1000
        assert wst_trade.sc_value == 2000
        assert wst_trade.state == IDXEthIbetWSTTradeState.EXECUTED
        assert wst_trade.memo == ""

        # Check log
        assert caplog.messages == [
            f"Syncing IbetWST trade events from=1, to={latest_finalized_block}",
            "Sync completed successfully",
        ]

    # <Normal_2_3>
    # "TradeCancelled" event exists
    # - Trade data is updated.
    @mock.patch(
        "batch.indexer_eth_wst_trades.EthAsyncContractUtils.get_event_logs",
        AsyncMock(
            side_effect=[
                [],  # No "TradeRequested" event
                [],  # No "TradeAccepted" event
                [{"args": {"index": 1}}],  # "TradeCancelled" event exists
                [],  # No "TradeRejected" event
            ]
        ),
    )
    @mock.patch(
        "batch.indexer_eth_wst_trades.IbetWST.get_trade",
        AsyncMock(
            return_value=IbetWSTTrade(
                seller_st_account=user_address_1,
                buyer_st_account=user_address_2,
                sc_token_address=sc_token_address_1,
                seller_sc_account=user_address_1,
                buyer_sc_account=user_address_2,
                st_value=1000,
                sc_value=2000,
                state="Cancelled",
                memo="",
            )
        ),
    )
    async def test_normal_2_3(self, processor, async_db, caplog):
        # Generate empty block
        await EthWeb3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Prepare test data
        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer_address_1
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        account = Account()
        account.issuer_address = self.issuer_address_1
        account.is_deleted = False
        async_db.add(account)

        await async_db.commit()

        # Run target process
        latest_finalized_block = await processor.get_finalized_block_number()
        await processor.sync_events()
        async_db.expire_all()

        # Check IDXEthIbetWSTTradeBlockNumber
        synced_block_number = (
            await async_db.scalars(select(IDXEthIbetWSTTradeBlockNumber).limit(1))
        ).first()
        assert synced_block_number.latest_block_number == latest_finalized_block

        wst_trade = (
            await async_db.scalars(
                select(IDXEthIbetWSTTrade)
                .where(IDXEthIbetWSTTrade.ibet_wst_address == self.ibet_wst_address_1)
                .limit(1)
            )
        ).first()
        assert wst_trade.index == 1
        assert wst_trade.seller_st_account_address == self.user_address_1
        assert wst_trade.buyer_st_account_address == self.user_address_2
        assert wst_trade.sc_token_address == self.sc_token_address_1
        assert wst_trade.seller_sc_account_address == self.user_address_1
        assert wst_trade.buyer_sc_account_address == self.user_address_2
        assert wst_trade.st_value == 1000
        assert wst_trade.sc_value == 2000
        assert wst_trade.state == IDXEthIbetWSTTradeState.CANCELLED
        assert wst_trade.memo == ""

        # Check log
        assert caplog.messages == [
            f"Syncing IbetWST trade events from=1, to={latest_finalized_block}",
            "Sync completed successfully",
        ]

    # <Normal_2_4>
    # "TradeRejected" event exists
    # - Trade data is updated.
    @mock.patch(
        "batch.indexer_eth_wst_trades.EthAsyncContractUtils.get_event_logs",
        AsyncMock(
            side_effect=[
                [],  # No "TradeRequested" event
                [],  # No "TradeAccepted" event
                [],  # No "TradeCancelled" event
                [{"args": {"index": 1}}],  # "TradeRejected" event exists
            ]
        ),
    )
    @mock.patch(
        "batch.indexer_eth_wst_trades.IbetWST.get_trade",
        AsyncMock(
            return_value=IbetWSTTrade(
                seller_st_account=user_address_1,
                buyer_st_account=user_address_2,
                sc_token_address=sc_token_address_1,
                seller_sc_account=user_address_1,
                buyer_sc_account=user_address_2,
                st_value=1000,
                sc_value=2000,
                state="Rejected",
                memo="",
            )
        ),
    )
    async def test_normal_2_4(self, processor, async_db, caplog):
        # Generate empty block
        await EthWeb3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Prepare test data
        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer_address_1
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        account = Account()
        account.issuer_address = self.issuer_address_1
        account.is_deleted = False
        async_db.add(account)

        await async_db.commit()

        # Run target process
        latest_finalized_block = await processor.get_finalized_block_number()
        await processor.sync_events()
        async_db.expire_all()

        # Check IDXEthIbetWSTTradeBlockNumber
        synced_block_number = (
            await async_db.scalars(select(IDXEthIbetWSTTradeBlockNumber).limit(1))
        ).first()
        assert synced_block_number.latest_block_number == latest_finalized_block

        wst_trade = (
            await async_db.scalars(
                select(IDXEthIbetWSTTrade)
                .where(IDXEthIbetWSTTrade.ibet_wst_address == self.ibet_wst_address_1)
                .limit(1)
            )
        ).first()
        assert wst_trade.index == 1
        assert wst_trade.seller_st_account_address == self.user_address_1
        assert wst_trade.buyer_st_account_address == self.user_address_2
        assert wst_trade.sc_token_address == self.sc_token_address_1
        assert wst_trade.seller_sc_account_address == self.user_address_1
        assert wst_trade.buyer_sc_account_address == self.user_address_2
        assert wst_trade.st_value == 1000
        assert wst_trade.sc_value == 2000
        assert wst_trade.state == IDXEthIbetWSTTradeState.REJECTED
        assert wst_trade.memo == ""

        # Check log
        assert caplog.messages == [
            f"Syncing IbetWST trade events from=1, to={latest_finalized_block}",
            "Sync completed successfully",
        ]

    # <Normal_3>
    # Multiple Trade events for the same trade index occur in one process
    # - A single record is created in the final state.
    @mock.patch(
        "batch.indexer_eth_wst_trades.EthAsyncContractUtils.get_event_logs",
        AsyncMock(
            side_effect=[
                [{"args": {"index": 1}}],  # "TradeRequested" event exists
                [{"args": {"index": 1}}],  # "TradeAccepted" event exists
                [],  # No "TradeCancelled" event
                [],  # No "TradeRejected" event
            ]
        ),
    )
    @mock.patch(
        "batch.indexer_eth_wst_trades.IbetWST.get_trade",
        AsyncMock(
            return_value=IbetWSTTrade(
                seller_st_account=user_address_1,
                buyer_st_account=user_address_2,
                sc_token_address=sc_token_address_1,
                seller_sc_account=user_address_1,
                buyer_sc_account=user_address_2,
                st_value=1000,
                sc_value=2000,
                state="Executed",
                memo="",
            ),
        ),
    )
    async def test_normal_3(self, processor, async_db, caplog):
        # Generate empty block
        await EthWeb3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Prepare test data
        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer_address_1
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = {}
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        account = Account()
        account.issuer_address = self.issuer_address_1
        account.is_deleted = False
        async_db.add(account)

        await async_db.commit()

        # Run target process
        latest_finalized_block = await processor.get_finalized_block_number()
        await processor.sync_events()
        async_db.expire_all()

        # Check IDXEthIbetWSTTradeBlockNumber
        synced_block_number = (
            await async_db.scalars(select(IDXEthIbetWSTTradeBlockNumber).limit(1))
        ).first()
        assert synced_block_number.latest_block_number == latest_finalized_block

        wst_trade = (
            await async_db.scalars(
                select(IDXEthIbetWSTTrade).where(
                    IDXEthIbetWSTTrade.ibet_wst_address == self.ibet_wst_address_1,
                )
            )
        ).all()
        assert len(wst_trade) == 1
        assert wst_trade[0].state == IDXEthIbetWSTTradeState.EXECUTED

        # Check log
        assert caplog.messages == [
            f"Syncing IbetWST trade events from=1, to={latest_finalized_block}",
            "Sync completed successfully",
        ]
