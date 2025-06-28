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
    EthToIbetBridgeTx,
    EthToIbetBridgeTxStatus,
    EthToIbetBridgeTxType,
    IbetBridgeTxParamsForceChangeLockedAccount,
    IbetBridgeTxParamsForceUnlock,
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_eth_wst_bridge_to_ibet import (
    LOG,
    WSTBridgeToIbetProcessor,
)
from tests.account_config import default_eth_account


@pytest.fixture(scope="function")
def processor(async_db, caplog: pytest.LogCaptureFixture):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield WSTBridgeToIbetProcessor()
    log.propagate = False
    log.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    # Test accounts
    issuer = default_eth_account("user1")
    user1 = default_eth_account("user2")
    user2 = default_eth_account("user3")

    # Test ibet token addresses
    ibet_token_address_1 = "0x1234567890123456789012345678900000000010"
    ibet_token_address_2 = "0x1234567890123456789012345678900000000020"

    #############################################################
    # Normal
    #############################################################

    # Normal_1
    # No records to process
    # - Skip processing if no records to process
    async def test_normal_1(self, processor, async_db, caplog):
        # Execute batch
        await processor.send_ibet_tx()
        async_db.expire_all()

        assert caplog.messages == []

    # Normal_2_1
    # Process a single record
    # - Force unlock transaction
    @mock.patch(
        "batch.processor_eth_wst_bridge_to_ibet.IbetSecurityTokenInterface.force_unlock",
        AsyncMock(
            side_effect=[
                (
                    "test_tx_hash_1",
                    {
                        "status": 1,  # Transaction succeeded
                        "blockNumber": 123456,
                    },
                )
            ]
        ),
    )
    async def test_normal_2_1(self, processor, async_db, caplog):
        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        eth_to_ibet_tx = EthToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=EthToIbetBridgeTxType.FORCE_UNLOCK,
            status=EthToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(eth_to_ibet_tx)
        await async_db.commit()

        # Execute batch
        await processor.send_ibet_tx()
        async_db.expire_all()

        # Check the transaction log
        eth_to_ibet_tx_af = (
            await async_db.scalars(
                select(EthToIbetBridgeTx).where(EthToIbetBridgeTx.tx_id == tx_id)
            )
        ).first()
        assert eth_to_ibet_tx_af.tx_hash == "test_tx_hash_1"
        assert eth_to_ibet_tx_af.block_number == 123456
        assert eth_to_ibet_tx_af.status == EthToIbetBridgeTxStatus.SUCCEEDED

        # Check the log
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_unlock",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_2
    # Process a single record
    # - Force change locked account transaction
    @mock.patch(
        "batch.processor_eth_wst_bridge_to_ibet.IbetSecurityTokenInterface.force_change_locked_account",
        AsyncMock(
            side_effect=[
                (
                    "test_tx_hash_1",
                    {
                        "status": 1,  # Transaction succeeded
                        "blockNumber": 123456,
                    },
                )
            ]
        ),
    )
    async def test_normal_2_2(self, processor, async_db, caplog):
        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        eth_to_ibet_tx = EthToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=EthToIbetBridgeTxType.FORCE_CHANGE_LOCKED_ACCOUNT,
            status=EthToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceChangeLockedAccount(
                lock_address=self.issuer["address"],
                before_account_address=self.user1["address"],
                after_account_address=self.user2["address"],
                value=1000,
                data={"message": "ibet_wst_bridge"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(eth_to_ibet_tx)
        await async_db.commit()

        # Execute batch
        await processor.send_ibet_tx()
        async_db.expire_all()

        # Check the transaction log
        eth_to_ibet_tx_af = (
            await async_db.scalars(
                select(EthToIbetBridgeTx).where(EthToIbetBridgeTx.tx_id == tx_id)
            )
        ).first()
        assert eth_to_ibet_tx_af.tx_hash == "test_tx_hash_1"
        assert eth_to_ibet_tx_af.block_number == 123456
        assert eth_to_ibet_tx_af.status == EthToIbetBridgeTxStatus.SUCCEEDED

        # Check the log
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_change_locked_account",
            f"Transaction sent successfully: id={tx_id}",
        ]

    #############################################################
    # Error
    #############################################################

    # Error_1
    # Issuer account not found
    # - Skip processing if the issuer account is not found
    async def test_error_1(self, processor, async_db, caplog):
        # Prepare test data
        tx_id = str(uuid.uuid4())
        eth_to_ibet_tx = EthToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=EthToIbetBridgeTxType.FORCE_UNLOCK,
            status=EthToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(eth_to_ibet_tx)
        await async_db.commit()

        # Execute batch
        await processor.send_ibet_tx()
        async_db.expire_all()

        # Check the log
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_unlock",
            f"Cannot find issuer for transaction: id={tx_id}",
        ]

        # Check the transaction log
        eth_to_ibet_tx_af = (
            await async_db.scalars(
                select(EthToIbetBridgeTx).where(EthToIbetBridgeTx.tx_id == tx_id)
            )
        ).first()
        assert eth_to_ibet_tx_af.status == EthToIbetBridgeTxStatus.PENDING

    # Error_2
    # Unknown transaction type
    # - Update the status to FAILED if the transaction type is unknown
    async def test_error_2(self, processor, async_db, caplog):
        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        eth_to_ibet_tx = EthToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type="unknown_type",  # Invalid transaction type
            status=EthToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(eth_to_ibet_tx)
        await async_db.commit()

        # Execute batch
        await processor.send_ibet_tx()
        async_db.expire_all()

        # Check the transaction log
        eth_to_ibet_tx_af = (
            await async_db.scalars(
                select(EthToIbetBridgeTx).where(EthToIbetBridgeTx.tx_id == tx_id)
            )
        ).first()
        assert eth_to_ibet_tx_af.status == EthToIbetBridgeTxStatus.FAILED

        # Check the log
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=unknown_type",
            f"Unknown transaction type: id={tx_id}, type=unknown_type",
        ]

    # Error_3
    # Transaction failed
    # - Update the status to FAILED if the transaction fails
    @mock.patch(
        "batch.processor_eth_wst_bridge_to_ibet.IbetSecurityTokenInterface.force_unlock",
        AsyncMock(
            side_effect=[
                (
                    "test_tx_hash_1",
                    {
                        "status": 0,  # Transaction failed
                        "blockNumber": None,
                    },
                )
            ]
        ),
    )
    async def test_error_3(self, processor, async_db, caplog):
        # Prepare test data
        account = Account()
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        eth_to_ibet_tx = EthToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=EthToIbetBridgeTxType.FORCE_UNLOCK,
            status=EthToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(eth_to_ibet_tx)
        await async_db.commit()

        # Execute batch
        await processor.send_ibet_tx()
        async_db.expire_all()

        # Check the transaction log
        eth_to_ibet_tx_af = (
            await async_db.scalars(
                select(EthToIbetBridgeTx).where(EthToIbetBridgeTx.tx_id == tx_id)
            )
        ).first()
        assert eth_to_ibet_tx_af.tx_hash is None
        assert eth_to_ibet_tx_af.block_number is None
        assert eth_to_ibet_tx_af.status == EthToIbetBridgeTxStatus.FAILED

        # Check the log
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_unlock",
            f"Transaction failed: id={tx_id}",
        ]
