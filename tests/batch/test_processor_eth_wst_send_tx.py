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

from app.model.db import (
    Account,
    EthIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
)
from batch.processor_eth_wst_send_tx import LOG, ProcessorEthWSTSendTx
from tests.account_config import default_eth_account


@pytest.fixture(scope="function")
def processor(async_db, caplog: pytest.LogCaptureFixture):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield ProcessorEthWSTSendTx()
    log.propagate = False
    log.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    eth_master = default_eth_account("user1")
    issuer = default_eth_account("user2")

    #############################################################
    # Normal
    #############################################################

    # Normal_1
    # - Confirm that nothing is processed when there is no target data to process
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

    # Normal_2_1
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Deploy
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.deploy_contract",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_1(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.ibet_wst_activated = True
        account.ibet_wst_version = IbetWSTVersion.V_1
        account.ibet_wst_tx_id = tx_id
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check if the transaction was processed
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.SENT
        assert wst_tx_af.tx_hash == "test_tx_hash"

        # Check if the log was recorded
        assert caplog.messages == [
            f"Processing transaction: id={tx_id}, type=deploy",
            f"Transaction sent successfully: id={tx_id}",
        ]

    #############################################################
    # Error
    #############################################################

    # Error_1
    # - Confirm that processing fails when the transaction sender account cannot be found
    async def test_error_1(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.ibet_wst_activated = True
        account.ibet_wst_version = IbetWSTVersion.V_1
        account.ibet_wst_tx_id = tx_id
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check if the transaction was processed
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.FAILED

        # Check if the log was recorded
        assert caplog.messages == [
            f"Processing transaction: id={tx_id}, type=deploy",
            f"Account not found for transaction sender: {self.eth_master['address']}",
        ]

    # Error_2
    # - Confirm that processing fails when an exception occurs during transaction sending
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.deploy_contract",
        AsyncMock(side_effect=Exception),
    )
    async def test_error_2(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.ibet_wst_activated = True
        account.ibet_wst_version = IbetWSTVersion.V_1
        account.ibet_wst_tx_id = tx_id
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.tx_params = {
            "name": "Test Token",
            "initialOwner": self.issuer["address"],
        }
        wst_tx.tx_sender = self.eth_master["address"]
        async_db.add(wst_tx)
        await async_db.commit()

        # Execute batch
        await processor.run()
        async_db.expire_all()

        # Check if the transaction was processed
        wst_tx_af = (
            await async_db.scalars(
                select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
            )
        ).first()
        assert wst_tx_af.status == IbetWSTTxStatus.PENDING

        # Check if the log was recorded
        assert caplog.messages == [
            f"Processing transaction: id={tx_id}, type=deploy",
            f"Failed to send transaction: id={tx_id}",
        ]
