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
from typing import Sequence
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from web3 import Web3
from web3.types import RPCEndpoint

from app.model.db import (
    Account,
    EthIbetWSTTx,
    EthToIbetBridgeTx,
    EthToIbetBridgeTxStatus,
    EthToIbetBridgeTxType,
    IbetWSTBridgeSyncedBlockNumber,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_eth_wst_monitor_bridge_events import (
    LOG,
    WSTBridgeMonitoringProcessor,
)
from config import WEB3_HTTP_PROVIDER
from eth_config import ETH_WEB3_HTTP_PROVIDER
from tests.account_config import default_eth_account

ibet_web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
eth_web3 = Web3(Web3.HTTPProvider(ETH_WEB3_HTTP_PROVIDER))


@pytest.fixture(scope="function")
def processor(async_db, caplog: pytest.LogCaptureFixture):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield WSTBridgeMonitoringProcessor()
    log.propagate = False
    log.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    # Token ABI
    ibet_token_abi = json.load(
        open("contracts/ibet/IbetSecurityTokenInterface.json", "r")
    )["abi"]

    # Test accounts
    relayer = default_eth_account("user1")
    issuer = default_eth_account("user2")
    user1 = default_eth_account("user3")
    user2 = default_eth_account("user4")

    # Test IbetWST and token addresses
    ibet_wst_address_1 = "0x1234567890123456789012345678900000000001"
    ibet_wst_address_2 = "0x1234567890123456789012345678900000000002"

    # Test ibet token addresses
    ibet_token_address_1 = "0x1234567890123456789012345678900000000010"
    ibet_token_address_2 = "0x1234567890123456789012345678900000000020"

    #############################################################
    # Normal
    #############################################################

    # Normal_1_1
    # No transactions to process
    # - Check if the latest block number is updated
    async def test_normal_1_1(self, processor, async_db, caplog):
        # Generate empty block
        ibet_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        eth_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        latest_block_ibet = await processor.get_latest_block_number("ibetfin")
        latest_block_eth = await processor.get_latest_block_number("ethereum")

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ibetfin")
                .limit(1)
            )
        ).first()
        assert synced_block_ibet.latest_block_number == latest_block_ibet

        synced_block_eth = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ethereum")
                .limit(1)
            )
        ).first()
        assert synced_block_eth.latest_block_number == latest_block_eth

        # Check log
        assert caplog.messages == []

    # Normal_1_2
    # Issuer account not found
    # - Check if the process is skipped
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_ibet_event_logs",
        AsyncMock(
            side_effect=[
                [
                    {
                        "args": {
                            "accountAddress": user1["address"],
                            "lockAddress": issuer["address"],
                            "value": 1000,
                            "data": '{"message": "ibet_wst_bridge"}',
                        }
                    }
                ],  # __process_mint
            ]
        ),
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_wst_event_logs",
        AsyncMock(
            side_effect=[
                [],  # __process_burn
                [],  # __process_transfer
            ]
        ),
    )
    async def test_normal_1_2(self, processor, async_db, caplog):
        # Generate empty block
        ibet_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        eth_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        latest_block_ibet = await processor.get_latest_block_number("ibetfin")
        latest_block_eth = await processor.get_latest_block_number("ethereum")

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.is_deleted = True  # issuer account is deleted
        async_db.add(account)

        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer["address"]
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = self.ibet_token_abi
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ibetfin")
                .limit(1)
            )
        ).first()
        assert synced_block_ibet.latest_block_number == latest_block_ibet

        synced_block_eth = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ethereum")
                .limit(1)
            )
        ).first()
        assert synced_block_eth.latest_block_number == latest_block_eth

        # Check EthIbetWSTTx
        eth_tx_list: Sequence[EthIbetWSTTx] = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(
                    EthIbetWSTTx.status == IbetWSTTxStatus.PENDING
                )
            )
        ).all()
        assert len(eth_tx_list) == 0

        # Check EthToIbetBridgeTx
        ibet_tx_list: Sequence[EthToIbetBridgeTx] = (
            await async_db.scalars(select(EthToIbetBridgeTx))
        ).all()
        assert len(ibet_tx_list) == 0

    # Normal_2
    # Synced block number is greater than the latest block number
    # - Check if the process is skipped
    async def test_normal_2(self, processor, async_db, caplog):
        # Prepare IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = IbetWSTBridgeSyncedBlockNumber(
            network="ibetfin", latest_block_number=999999999
        )
        async_db.add(synced_block_ibet)

        synced_block_eth = IbetWSTBridgeSyncedBlockNumber(
            network="ethereum", latest_block_number=888888888
        )
        async_db.add(synced_block_eth)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ibetfin")
                .limit(1)
            )
        ).first()
        assert synced_block_ibet.latest_block_number == 999999999

        synced_block_eth = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ethereum")
                .limit(1)
            )
        ).first()
        assert synced_block_eth.latest_block_number == 888888888

        # Check log
        assert caplog.messages == [
            "skip process",  # Skip ibet_to_eth
            "skip process",  # skip eth_to_ibet
        ]

    # Normal_3_1
    # ibet -> eth bridge event is detected
    # - Check if the mint transaction record is registered
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_ibet_event_logs",
        AsyncMock(
            side_effect=[
                [
                    {
                        "args": {
                            "accountAddress": user1["address"],
                            "lockAddress": issuer["address"],
                            "value": 1000,
                            "data": '{"message": "ibet_wst_bridge"}',
                        }
                    }
                ],  # __process_mint
            ]
        ),
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_wst_event_logs",
        AsyncMock(
            side_effect=[
                [],  # __process_burn
                [],  # __process_transfer
            ]
        ),
    )
    async def test_normal_3_1(self, processor, async_db, caplog):
        # Generate empty block
        ibet_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        eth_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        latest_block_ibet = await processor.get_latest_block_number("ibetfin")
        latest_block_eth = await processor.get_latest_block_number("ethereum")

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer["address"]
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = self.ibet_token_abi
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ibetfin")
                .limit(1)
            )
        ).first()
        assert synced_block_ibet.latest_block_number == latest_block_ibet

        synced_block_eth = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ethereum")
                .limit(1)
            )
        ).first()
        assert synced_block_eth.latest_block_number == latest_block_eth

        # Check EthIbetWSTTx
        eth_tx_list: Sequence[EthIbetWSTTx] = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(
                    EthIbetWSTTx.status == IbetWSTTxStatus.PENDING
                )
            )
        ).all()
        assert len(eth_tx_list) == 1
        eth_tx = eth_tx_list[0]
        assert eth_tx.tx_id is not None
        assert eth_tx.tx_type == IbetWSTTxType.MINT
        assert eth_tx.version == IbetWSTVersion.V_1
        assert eth_tx.status == IbetWSTTxStatus.PENDING
        assert eth_tx.ibet_wst_address == self.ibet_wst_address_1
        assert eth_tx.tx_params == {
            "to_address": self.user1["address"],
            "value": 1000,
        }
        assert eth_tx.tx_sender == self.relayer["address"]
        assert eth_tx.authorizer == self.issuer["address"]
        assert eth_tx.authorization == {
            "nonce": mock.ANY,
            "v": mock.ANY,
            "r": mock.ANY,
            "s": mock.ANY,
        }

        # Check EthToIbetBridgeTx
        ibet_tx_list: Sequence[EthToIbetBridgeTx] = (
            await async_db.scalars(select(EthToIbetBridgeTx))
        ).all()
        assert len(ibet_tx_list) == 0

    # Normal_3_2
    # ibet -> eth bridge event: Invalid message
    # - Check if the process is skipped
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_ibet_event_logs",
        AsyncMock(
            side_effect=[
                [
                    {
                        "args": {
                            "accountAddress": user1["address"],
                            "lockAddress": issuer["address"],
                            "value": 1000,
                            "data": '{"message": "invalid_message"}',
                        }
                    }
                ],  # __process_mint
            ]
        ),
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_wst_event_logs",
        AsyncMock(
            side_effect=[
                [],  # __process_burn
                [],  # __process_transfer
            ]
        ),
    )
    async def test_normal_3_2(self, processor, async_db, caplog):
        # Generate empty block
        ibet_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        eth_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        latest_block_ibet = await processor.get_latest_block_number("ibetfin")
        latest_block_eth = await processor.get_latest_block_number("ethereum")

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer["address"]
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = self.ibet_token_abi
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ibetfin")
                .limit(1)
            )
        ).first()
        assert synced_block_ibet.latest_block_number == latest_block_ibet

        synced_block_eth = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ethereum")
                .limit(1)
            )
        ).first()
        assert synced_block_eth.latest_block_number == latest_block_eth

        # Check EthIbetWSTTx
        eth_tx_list: Sequence[EthIbetWSTTx] = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(
                    EthIbetWSTTx.status == IbetWSTTxStatus.PENDING
                )
            )
        ).all()
        assert len(eth_tx_list) == 0

        # Check EthToIbetBridgeTx
        ibet_tx_list: Sequence[EthToIbetBridgeTx] = (
            await async_db.scalars(select(EthToIbetBridgeTx))
        ).all()
        assert len(ibet_tx_list) == 0

    # Normal_4_1
    # eth -> ibet bridge event is detected
    # - Burn event is detected
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_ibet_event_logs",
        AsyncMock(
            side_effect=[
                [],  # __process_mint
            ]
        ),
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_wst_event_logs",
        AsyncMock(
            side_effect=[
                [
                    {
                        "args": {
                            "from": user1["address"],
                            "value": 1000,
                        }
                    }
                ],  # __process_burn
                [],  # __process_transfer
            ]
        ),
    )
    async def test_normal_4_1(self, processor, async_db, caplog):
        # Generate empty block
        ibet_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        eth_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        latest_block_ibet = await processor.get_latest_block_number("ibetfin")
        latest_block_eth = await processor.get_latest_block_number("ethereum")

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer["address"]
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = self.ibet_token_abi
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ibetfin")
                .limit(1)
            )
        ).first()
        assert synced_block_ibet.latest_block_number == latest_block_ibet

        synced_block_eth = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ethereum")
                .limit(1)
            )
        ).first()
        assert synced_block_eth.latest_block_number == latest_block_eth

        # Check EthIbetWSTTx
        tx_list: Sequence[EthIbetWSTTx] = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(
                    EthIbetWSTTx.status == IbetWSTTxStatus.PENDING
                )
            )
        ).all()
        assert len(tx_list) == 0

        # Check EthToIbetBridgeTx
        ibet_tx_list: Sequence[EthToIbetBridgeTx] = (
            await async_db.scalars(select(EthToIbetBridgeTx))
        ).all()
        assert len(ibet_tx_list) == 1
        ibet_tx = ibet_tx_list[0]
        assert ibet_tx.tx_id is not None
        assert ibet_tx.token_address == self.ibet_token_address_1
        assert ibet_tx.tx_type == EthToIbetBridgeTxType.FORCE_UNLOCK
        assert ibet_tx.status == EthToIbetBridgeTxStatus.PENDING
        assert ibet_tx.tx_params == {
            "lock_address": self.issuer["address"],
            "account_address": self.user1["address"],
            "recipient_address": self.user1["address"],
            "value": 1000,
            "data": {"message": "ibet_wst_bridge"},
        }

    # Normal_4_2
    # eth -> ibet bridge event is detected
    # - Transfer event is detected
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.ETH_MASTER_ACCOUNT_ADDRESS",
        relayer["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_ibet_event_logs",
        AsyncMock(
            side_effect=[
                [],  # __process_mint
            ]
        ),
    )
    @mock.patch(
        "batch.processor_eth_wst_monitor_bridge_events.BridgeEventViewer.get_wst_event_logs",
        AsyncMock(
            side_effect=[
                [],  # __process_burn
                [
                    {
                        "args": {
                            "from": user1["address"],
                            "to": user2["address"],
                            "value": 1000,
                        }
                    }
                ],  # __process_transfer
            ]
        ),
    )
    async def test_normal_4_2(self, processor, async_db, caplog):
        # Generate empty block
        ibet_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        eth_web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        latest_block_ibet = await processor.get_latest_block_number("ibetfin")
        latest_block_eth = await processor.get_latest_block_number("ethereum")

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.token_address = self.ibet_token_address_1
        token.issuer_address = self.issuer["address"]
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.abi = self.ibet_token_abi
        token.version = TokenVersion.V_25_06
        token.ibet_wst_deployed = True
        token.ibet_wst_address = self.ibet_wst_address_1
        async_db.add(token)

        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check IbetWSTBridgeSyncedBlockNumber
        synced_block_ibet = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ibetfin")
                .limit(1)
            )
        ).first()
        assert synced_block_ibet.latest_block_number == latest_block_ibet

        synced_block_eth = (
            await async_db.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == "ethereum")
                .limit(1)
            )
        ).first()
        assert synced_block_eth.latest_block_number == latest_block_eth

        # Check EthIbetWSTTx
        tx_list: Sequence[EthIbetWSTTx] = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(
                    EthIbetWSTTx.status == IbetWSTTxStatus.PENDING
                )
            )
        ).all()
        assert len(tx_list) == 0

        # Check EthToIbetBridgeTx
        ibet_tx_list: Sequence[EthToIbetBridgeTx] = (
            await async_db.scalars(select(EthToIbetBridgeTx))
        ).all()
        assert len(ibet_tx_list) == 1
        ibet_tx = ibet_tx_list[0]
        assert ibet_tx.tx_id is not None
        assert ibet_tx.token_address == self.ibet_token_address_1
        assert ibet_tx.tx_type == EthToIbetBridgeTxType.FORCE_CHANGE_LOCKED_ACCOUNT
        assert ibet_tx.status == EthToIbetBridgeTxStatus.PENDING
        assert ibet_tx.tx_params == {
            "lock_address": self.issuer["address"],
            "before_account_address": self.user1["address"],
            "after_account_address": self.user2["address"],
            "value": 1000,
            "data": {"message": "ibet_wst_bridge"},
        }
