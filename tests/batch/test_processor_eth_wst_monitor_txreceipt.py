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
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from web3.exceptions import TimeExhausted

from app.model.db import (
    EthIbetWSTTx,
    IbetWSTTxParamsAcceptTrade,
    IbetWSTTxParamsAddAccountWhiteList,
    IbetWSTTxParamsBurn,
    IbetWSTTxParamsCancelTrade,
    IbetWSTTxParamsDeploy,
    IbetWSTTxParamsMint,
    IbetWSTTxParamsRejectTrade,
    IbetWSTTxParamsRequestTrade,
    IbetWSTTxParamsTransfer,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    IDXEthIbetWSTWhitelist,
    Token,
    TokenType,
    TokenVersion,
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
    user1 = default_eth_account("user3")
    user2 = default_eth_account("user4")

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
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token", initial_owner=self.issuer["address"]
        )
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
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token", initial_owner=self.issuer["address"]
        )
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
    # - TxReceipt: exists(success)
    # - Not finalized
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
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
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token", initial_owner=self.issuer["address"]
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is False

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=deploy",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_3_2
    # - TxReceipt: exists(failure)
    # - Not finalized
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 0,
                "blockNumber": 100,
                "gasUsed": 21000,
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
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token", initial_owner=self.issuer["address"]
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is False

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=deploy",
            f"Transaction failed: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_1
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: DEPLOY
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    async def test_normal_4_1(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DEPLOY
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.tx_params = IbetWSTTxParamsDeploy(
            name="Test Token", initial_owner=self.issuer["address"]
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True

        token_af = (
            await async_db.scalars(
                select(Token).where(Token.ibet_wst_tx_id == tx_id).limit(1)
            )
        ).first()
        assert token_af.ibet_wst_deployed is True
        assert token_af.ibet_wst_address == "0x9876543210abcdef1234567890abcdef12345678"

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=deploy",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_1
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: MINT
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "to": user1["address"],
                        "value": 1000,
                    },  # Mint event log
                }
            ]
        ),
    )
    async def test_normal_4_2_1(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.MINT
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsMint(
            to_address=self.user1["address"],
            value=1000,
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "to_address": self.user1["address"],
            "value": 1000,
        }

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=mint",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_2
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: BURN
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "from": user1["address"],
                        "value": 1000,
                    },  # Burn event log
                }
            ]
        ),
    )
    async def test_normal_4_2_2(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.BURN
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsBurn(
            from_address=self.user1["address"],
            value=1000,
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "from_address": self.user1["address"],
            "value": 1000,
        }

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=burn",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_3
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: ADD_WHITELIST
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "accountAddress": user1["address"],
                    },
                }
            ]
        ),
    )
    async def test_normal_4_2_3(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.ADD_WHITELIST
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsAddAccountWhiteList(
            account_address=self.user1["address"],
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "account_address": self.user1["address"],
        }

        # Verify that the whitelist entry has been created
        idx_whitelist: IDXEthIbetWSTWhitelist = (
            await async_db.scalars(select(IDXEthIbetWSTWhitelist).limit(1))
        ).first()
        assert idx_whitelist is not None
        assert (
            idx_whitelist.ibet_wst_address
            == "0x9876543210abcdef1234567890abcdef12345678"
        )
        assert idx_whitelist.account_address == self.user1["address"]

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=add_whitelist",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_4
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: DELETE_WHITELIST
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "accountAddress": user1["address"],
                    },
                }
            ]
        ),
    )
    async def test_normal_4_2_4(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.DELETE_WHITELIST
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsAddAccountWhiteList(
            account_address=self.user1["address"],
        )
        wst_tx.tx_sender = self.eth_master["address"]
        wst_tx.finalized = False
        async_db.add(wst_tx)

        idx_whitelist = IDXEthIbetWSTWhitelist(
            ibet_wst_address=wst_tx.ibet_wst_address,
            account_address=self.user1["address"],
        )
        async_db.add(idx_whitelist)
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "account_address": self.user1["address"],
        }

        # Verify that the whitelist entry has been deleted
        idx_whitelist_af = (
            await async_db.scalars(select(IDXEthIbetWSTWhitelist).limit(1))
        ).first()
        assert idx_whitelist_af is None

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=delete_whitelist",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_5
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: REQUEST_TRADE
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "index": 1,
                        "sellerSTAccountAddress": user1["address"],
                        "buyerSTAccountAddress": user2["address"],
                        "SCTokenAddress": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
                        "sellerSCAccountAddress": user1["address"],
                        "buyerSCAccountAddress": user2["address"],
                        "STValue": 1000,
                        "SCValue": 2000,
                    },
                }
            ]
        ),
    )
    async def test_normal_4_2_5(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.REQUEST_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsRequestTrade(
            seller_st_account_address=self.user1["address"],
            buyer_st_account_address=self.user2["address"],
            sc_token_address="0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
            seller_sc_account_address=self.user1["address"],
            buyer_sc_account_address=self.user2["address"],
            st_value=1000,
            sc_value=2000,
            memo="Test trade request",
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "index": 1,
            "seller_st_account_address": self.user1["address"],
            "buyer_st_account_address": self.user2["address"],
            "sc_token_address": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
            "seller_sc_account_address": self.user1["address"],
            "buyer_sc_account_address": self.user2["address"],
            "st_value": 1000,
            "sc_value": 2000,
        }

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=request_trade",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_6
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: CANCEL_TRADE
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "index": 1,
                        "sellerSTAccountAddress": user1["address"],
                        "buyerSTAccountAddress": user2["address"],
                        "SCTokenAddress": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
                        "sellerSCAccountAddress": user1["address"],
                        "buyerSCAccountAddress": user2["address"],
                        "STValue": 1000,
                        "SCValue": 2000,
                    },
                }
            ]
        ),
    )
    async def test_normal_4_2_6(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.CANCEL_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsCancelTrade(index=1)
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "index": 1,
            "seller_st_account_address": self.user1["address"],
            "buyer_st_account_address": self.user2["address"],
            "sc_token_address": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
            "seller_sc_account_address": self.user1["address"],
            "buyer_sc_account_address": self.user2["address"],
            "st_value": 1000,
            "sc_value": 2000,
        }

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=cancel_trade",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_7
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: ACCEPT_TRADE
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "index": 1,
                        "sellerSTAccountAddress": user1["address"],
                        "buyerSTAccountAddress": user2["address"],
                        "SCTokenAddress": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
                        "sellerSCAccountAddress": user1["address"],
                        "buyerSCAccountAddress": user2["address"],
                        "STValue": 1000,
                        "SCValue": 2000,
                    },
                }
            ]
        ),
    )
    async def test_normal_4_2_7(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.ACCEPT_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsAcceptTrade(index=1)
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "index": 1,
            "seller_st_account_address": self.user1["address"],
            "buyer_st_account_address": self.user2["address"],
            "sc_token_address": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
            "seller_sc_account_address": self.user1["address"],
            "buyer_sc_account_address": self.user2["address"],
            "st_value": 1000,
            "sc_value": 2000,
        }

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=accept_trade",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_8
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: REJECT_TRADE
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "index": 1,
                        "sellerSTAccountAddress": user1["address"],
                        "buyerSTAccountAddress": user2["address"],
                        "SCTokenAddress": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
                        "sellerSCAccountAddress": user1["address"],
                        "buyerSCAccountAddress": user2["address"],
                        "STValue": 1000,
                        "SCValue": 2000,
                    },
                }
            ]
        ),
    )
    async def test_normal_4_2_8(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.REJECT_TRADE
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsRejectTrade(index=1)
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "index": 1,
            "seller_st_account_address": self.user1["address"],
            "buyer_st_account_address": self.user2["address"],
            "sc_token_address": "0x876f5c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h",
            "seller_sc_account_address": self.user1["address"],
            "buyer_sc_account_address": self.user2["address"],
            "st_value": 1000,
            "sc_value": 2000,
        }

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=reject_trade",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]

    # Normal_4_2_9
    # - TxReceipt: exists(success)
    # - Finalized
    # - TxType: TRANSFER
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.wait_for_transaction_receipt",
        AsyncMock(
            return_value={
                "status": 1,
                "blockNumber": 100,
                "contractAddress": "0x9876543210abcdef1234567890abcdef12345678",
                "gasUsed": 21000,
            }
        ),
    )
    @mock.patch(
        "app.utils.eth_contract_utils.EthAsyncContractUtils.get_finalized_block_number",
        AsyncMock(return_value=100),
    )
    @mock.patch(
        "web3.contract.base_contract.BaseContractEvent.process_receipt",
        MagicMock(
            return_value=[
                {
                    "args": {
                        "from": user1["address"],
                        "to": user2["address"],
                        "value": 1000,
                    },
                }
            ]
        ),
    )
    async def test_normal_4_2_9(self, processor, async_db, caplog):
        tx_id = str(uuid.uuid4())

        # Prepare test data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token.issuer_address = self.issuer["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_25_06
        token.ibet_wst_activated = True
        token.ibet_wst_version = IbetWSTVersion.V_1
        token.ibet_wst_tx_id = tx_id
        token.ibet_wst_deployed = False
        token.ibet_wst_address = None
        async_db.add(token)

        wst_tx = EthIbetWSTTx()
        wst_tx.tx_id = tx_id
        wst_tx.tx_type = IbetWSTTxType.TRANSFER
        wst_tx.version = IbetWSTVersion.V_1
        wst_tx.status = IbetWSTTxStatus.SENT
        wst_tx.tx_hash = self.tx_hash
        wst_tx.ibet_wst_address = "0x9876543210abcdef1234567890abcdef12345678"
        wst_tx.tx_params = IbetWSTTxParamsTransfer(
            from_address=self.user1["address"],
            to_address=self.user2["address"],
            value=1000,
            valid_after=1,
            valid_before=2**64 - 1,
        )
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
        assert wst_tx_af.gas_used == 21000
        assert wst_tx_af.finalized is True
        assert wst_tx_af.event_log == {
            "from_address": self.user1["address"],
            "to_address": self.user2["address"],
            "value": 1000,
        }

        assert caplog.messages == [
            f"Monitor transaction: id={tx_id}, type=transfer",
            f"Transaction succeeded: id={tx_id}, block_number=100, gas_used=21000",
            f"Transaction finalized: id={tx_id}, block_number=100, gas_used=21000",
        ]
