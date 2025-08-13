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
import secrets
import uuid
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from eth_utils import to_checksum_address
from sqlalchemy import select

from app.model.db import (
    Account,
    EthIbetWSTTx,
    IbetWSTAuthorization,
    IbetWSTTxParamsAcceptTrade,
    IbetWSTTxParamsAddAccountWhiteList,
    IbetWSTTxParamsBurn,
    IbetWSTTxParamsCancelTrade,
    IbetWSTTxParamsDeleteAccountWhiteList,
    IbetWSTTxParamsDeploy,
    IbetWSTTxParamsForceBurn,
    IbetWSTTxParamsMint,
    IbetWSTTxParamsRequestTrade,
    IbetWSTTxParamsTransfer,
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
    user1 = default_eth_account("user3")
    user2 = default_eth_account("user4")

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
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token",
            initial_owner=self.issuer["address"],
        )
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
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token",
            initial_owner=self.issuer["address"],
        )
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

    # Normal_2_2
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Add Whitelist
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.add_account_white_list_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_2(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.ADD_WHITELIST
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsAddAccountWhiteList(
            st_account=self.user1["address"],
            sc_account_in=self.user1["address"],
            sc_account_out=self.user1["address"],
        )
        wst_tx.authorizer = self.issuer["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=add_whitelist",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_3
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Delete Whitelist
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.delete_account_white_list_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_3(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DELETE_WHITELIST
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsDeleteAccountWhiteList(
            st_account=self.user1["address"],
        )
        wst_tx.authorizer = self.issuer["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=delete_whitelist",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_4
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Request Trade
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.request_trade_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_4(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.REQUEST_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsRequestTrade(
            seller_st_account=self.user1["address"],
            buyer_st_account=self.user2["address"],
            sc_token_address=to_checksum_address(
                "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
            ),
            st_value=1000,
            sc_value=2000,
            memo="Test trade request",
        )
        wst_tx.authorizer = self.user1["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=request_trade",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_5
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Cancel Trade
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.cancel_trade_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_5(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.CANCEL_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsCancelTrade(
            index=10,
        )
        wst_tx.authorizer = self.user1["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=cancel_trade",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_6
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Accept Trade
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.accept_trade_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_6(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.ACCEPT_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsAcceptTrade(index=10)
        wst_tx.authorizer = self.user2["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=accept_trade",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_7
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Reject Trade
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.reject_trade_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_7(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.REJECT_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsAcceptTrade(index=10)
        wst_tx.authorizer = self.user2["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=reject_trade",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_8
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Mint
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.mint_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_8(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.MINT
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
        wst_tx.authorizer = self.user1["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=mint",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_9
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Burn
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.burn_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_9(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.BURN
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsBurn(
            from_address=self.user1["address"],
            value=1000,
        )
        wst_tx.authorizer = self.user1["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=burn",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_10
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Transfer
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.transfer_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_10(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.TRANSFER
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
        wst_tx.authorizer = self.user1["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=transfer",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_11
    # - Confirm that processing is performed correctly when there is target data to process
    # - transaction type: Force Burn
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_ACCOUNT_ADDRESS",
        eth_master["address"],
    )
    @mock.patch(
        "batch.processor_eth_wst_send_tx.ETH_MASTER_PRIVATE_KEY",
        eth_master["private_key"],
    )
    @mock.patch(
        "app.model.eth.wst.IbetWST.force_burn_from_with_authorization",
        AsyncMock(return_value="test_tx_hash"),
    )
    async def test_normal_2_11(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.FORCE_BURN
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.ibet_wst_address = to_checksum_address(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        wst_tx.tx_params = IbetWSTTxParamsForceBurn(
            account=self.user1["address"],
            value=1000,
        )
        wst_tx.authorizer = self.issuer["address"]
        wst_tx.authorization = IbetWSTAuthorization(
            nonce=secrets.token_bytes(32).hex(),
            v=27,
            r=secrets.token_bytes(32).hex(),
            s=secrets.token_bytes(32).hex(),
        )
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
            f"Processing transaction: id={tx_id}, type=force_burn",
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
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token",
            initial_owner=self.issuer["address"],
        )
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
        async_db.add(account)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.PENDING
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token",
            initial_owner=self.issuer["address"],
        )
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
