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
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from web3.exceptions import TimeExhausted

from app.model.db import (
    EthIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
)
from batch.processor_eth_wst_monitor_txreceipt import (
    LOG,
    ProcessorEthWSTMonitorTxReceipt,
)
from tests.account_config import default_eth_account


@pytest.fixture(scope="function")
def processor(async_db, caplog: pytest.LogCaptureFixture):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield ProcessorEthWSTMonitorTxReceipt()
    log.propagate = False
    log.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    eth_master = default_eth_account("user1")
    issuer = default_eth_account("user2")
    tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

    #############################################################
    # Normal
    #############################################################

    # Normal_1
    # - If there is no target data, it confirms that nothing is processed
    async def test_normal_1(self, processor, async_db):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SUCCEEDED
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        wst_tx.finalized = True
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check if the transaction is still in the same state
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.SUCCEEDED
        assert wst_tx_af.finalized is True

    # Normal_2
    # - TxReceipt: does not exist (TimeExhausted)
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(side_effect=TimeExhausted),
    )
    async def test_normal_2(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        wst_tx.finalized = False
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Verify that the status has not changed
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.SENT
        assert wst_tx_af.finalized is False

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=deploy",
            f"Transaction receipt not found, skipping processing: id={tx_id}",
        ]

    # Normal_3_1
    # - TxReceipt: exists
    # - Result: success
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=0),
    )
    async def test_normal_3_1(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        wst_tx.finalized = False
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Verify that the status and block number have been updated
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.SUCCEEDED
        assert wst_tx_af.block_number == 100
        assert wst_tx_af.finalized is False

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=deploy",
            f"Transaction succeeded: id={tx_id}, block_number=100",
        ]

    # Normal_3_2
    # - TxReceipt: exists
    # - Result: failure
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 0,
                "blockNumber": 100,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=0),
    )
    async def test_normal_3_2(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        wst_tx.finalized = False
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Verify that the status and block number have been updated
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.FAILED
        assert wst_tx_af.block_number == 100
        assert wst_tx_af.finalized is False

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=deploy",
            f"Transaction failed: id={tx_id}, block_number=100",
        ]

    # Normal_4
    # - TxReceipt: exists
    # - Result: success
    # - Finalized
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    async def test_normal_4(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        wst_tx.finalized = False
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Verify that the status and block number have been updated
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.SUCCEEDED
        assert wst_tx_af.block_number == 100
        assert wst_tx_af.finalized is True

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=deploy",
            f"Transaction succeeded: id={tx_id}, block_number=100",
        ]
