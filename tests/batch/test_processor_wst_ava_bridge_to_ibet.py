from app.model.db import AccountRsaStatus

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
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ContractRevertError
from app.model.db import (
    Account,
    AvaToIbetBridgeTx,
    EthToIbetBridgeTx,
    IbetBridgeTxParamsForceChangeLockedAccount,
    IbetBridgeTxParamsForceUnlock,
    ToIbetBridgeTxStatus,
    ToIbetBridgeTxType,
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_wst_ava_bridge_to_ibet import LOG, AvaWSTBridgeToIbetProcessor
from tests.account_config import default_eth_account


@pytest.fixture(scope="function")
def processor(async_db: AsyncSession, caplog: pytest.LogCaptureFixture):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield AvaWSTBridgeToIbetProcessor()
    log.propagate = False
    log.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    issuer = default_eth_account("user1")
    user1 = default_eth_account("user2")
    user2 = default_eth_account("user3")

    ibet_token_address_1 = "0x1234567890123456789012345678900000000010"

    #############################################################
    # Normal
    #############################################################

    # Normal_1
    # No records to process
    async def test_normal_1(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        await processor.send_ibet_tx()
        async_db.expire_all()

        assert caplog.messages == []

    # Normal_2_1
    # Process a single force unlock record
    @mock.patch(
        "batch.processor_wst_ava_bridge_to_ibet.IbetSecurityTokenInterface.force_unlock",
        AsyncMock(
            return_value=(
                "test_tx_hash_1",
                {
                    "status": 1,
                    "blockNumber": 123456,
                },
            )
        ),
    )
    async def test_normal_2_1(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        ava_to_ibet_tx = AvaToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=ToIbetBridgeTxType.FORCE_UNLOCK,
            status=ToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge", "network": "avalanche"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(ava_to_ibet_tx)
        await async_db.commit()

        await processor.send_ibet_tx()
        async_db.expire_all()

        ava_to_ibet_tx_af = (
            await async_db.scalars(
                select(AvaToIbetBridgeTx).where(AvaToIbetBridgeTx.tx_id == tx_id)
            )
        ).one()
        assert ava_to_ibet_tx_af.tx_hash == "test_tx_hash_1"
        assert ava_to_ibet_tx_af.block_number == 123456
        assert ava_to_ibet_tx_af.status == ToIbetBridgeTxStatus.SUCCEEDED

        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_unlock",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_2_2
    # Process a single force change locked account record
    @mock.patch(
        "batch.processor_wst_ava_bridge_to_ibet.IbetSecurityTokenInterface.force_change_locked_account",
        AsyncMock(
            return_value=(
                "test_tx_hash_2",
                {
                    "status": 1,
                    "blockNumber": 654321,
                },
            )
        ),
    )
    async def test_normal_2_2(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        ava_to_ibet_tx = AvaToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=ToIbetBridgeTxType.FORCE_CHANGE_LOCKED_ACCOUNT,
            status=ToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceChangeLockedAccount(
                lock_address=self.issuer["address"],
                before_account_address=self.user1["address"],
                after_account_address=self.user2["address"],
                value=1000,
                data={"message": "ibet_wst_bridge", "network": "avalanche"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(ava_to_ibet_tx)
        await async_db.commit()

        await processor.send_ibet_tx()
        async_db.expire_all()

        ava_to_ibet_tx_af = (
            await async_db.scalars(
                select(AvaToIbetBridgeTx).where(AvaToIbetBridgeTx.tx_id == tx_id)
            )
        ).one()
        assert ava_to_ibet_tx_af.tx_hash == "test_tx_hash_2"
        assert ava_to_ibet_tx_af.block_number == 654321
        assert ava_to_ibet_tx_af.status == ToIbetBridgeTxStatus.SUCCEEDED

        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_change_locked_account",
            f"Transaction sent successfully: id={tx_id}",
        ]

    # Normal_3
    # ETH table records are ignored by AVA processor
    async def test_normal_3(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        eth_tx_id = str(uuid.uuid4())
        eth_to_ibet_tx = EthToIbetBridgeTx(
            tx_id=eth_tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=ToIbetBridgeTxType.FORCE_UNLOCK,
            status=ToIbetBridgeTxStatus.PENDING,
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

        await processor.send_ibet_tx()
        async_db.expire_all()

        eth_to_ibet_tx_af = (
            await async_db.scalars(
                select(EthToIbetBridgeTx).where(EthToIbetBridgeTx.tx_id == eth_tx_id)
            )
        ).one()
        assert eth_to_ibet_tx_af.status == ToIbetBridgeTxStatus.PENDING
        assert caplog.messages == []

    #############################################################
    # Error
    #############################################################

    # Error_1
    # Issuer account not found
    async def test_error_1(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        tx_id = str(uuid.uuid4())
        ava_to_ibet_tx = AvaToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=ToIbetBridgeTxType.FORCE_UNLOCK,
            status=ToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge", "network": "avalanche"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(ava_to_ibet_tx)
        await async_db.commit()

        await processor.send_ibet_tx()
        async_db.expire_all()

        ava_to_ibet_tx_af = (
            await async_db.scalars(
                select(AvaToIbetBridgeTx).where(AvaToIbetBridgeTx.tx_id == tx_id)
            )
        ).one()
        assert ava_to_ibet_tx_af.status == ToIbetBridgeTxStatus.PENDING
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_unlock",
            f"Cannot find issuer for transaction: id={tx_id}",
        ]

    # Error_2
    # Unknown transaction type
    async def test_error_2(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        ava_to_ibet_tx = AvaToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type="unknown_type",
            status=ToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge", "network": "avalanche"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(ava_to_ibet_tx)
        await async_db.commit()

        await processor.send_ibet_tx()
        async_db.expire_all()

        ava_to_ibet_tx_af = (
            await async_db.scalars(
                select(AvaToIbetBridgeTx).where(AvaToIbetBridgeTx.tx_id == tx_id)
            )
        ).one()
        assert ava_to_ibet_tx_af.status == ToIbetBridgeTxStatus.FAILED
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=unknown_type",
            f"Unknown transaction type: id={tx_id}, type=unknown_type",
        ]

    # Error_3
    # Contract revert error
    @mock.patch(
        "batch.processor_wst_ava_bridge_to_ibet.IbetSecurityTokenInterface.force_unlock",
        AsyncMock(side_effect=[ContractRevertError(code_msg="111201")]),
    )
    async def test_error_3(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        ava_to_ibet_tx = AvaToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=ToIbetBridgeTxType.FORCE_UNLOCK,
            status=ToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge", "network": "avalanche"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(ava_to_ibet_tx)
        await async_db.commit()

        await processor.send_ibet_tx()
        async_db.expire_all()

        ava_to_ibet_tx_af = (
            await async_db.scalars(
                select(AvaToIbetBridgeTx).where(AvaToIbetBridgeTx.tx_id == tx_id)
            )
        ).one()
        assert ava_to_ibet_tx_af.tx_hash is None
        assert ava_to_ibet_tx_af.block_number is None
        assert ava_to_ibet_tx_af.status == ToIbetBridgeTxStatus.FAILED
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_unlock",
            f"Transaction failed: id={tx_id} ( 111201 | Unlock amount is greater than locked amount. )",
        ]

    # Error_4
    # Unknown exception is re-raised and transaction stays pending
    @mock.patch(
        "batch.processor_wst_ava_bridge_to_ibet.IbetSecurityTokenInterface.force_unlock",
        AsyncMock(side_effect=[Exception]),
    )
    async def test_error_4(
        self,
        processor: AvaWSTBridgeToIbetProcessor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = self.issuer["address"]
        account.keyfile = self.issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        tx_id = str(uuid.uuid4())
        ava_to_ibet_tx = AvaToIbetBridgeTx(
            tx_id=tx_id,
            token_address=self.ibet_token_address_1,
            tx_type=ToIbetBridgeTxType.FORCE_UNLOCK,
            status=ToIbetBridgeTxStatus.PENDING,
            tx_params=IbetBridgeTxParamsForceUnlock(
                lock_address=self.issuer["address"],
                account_address=self.user1["address"],
                recipient_address=self.user1["address"],
                value=1000,
                data={"message": "ibet_wst_bridge", "network": "avalanche"},
            ),
            tx_sender=self.issuer["address"],
        )
        async_db.add(ava_to_ibet_tx)
        await async_db.commit()

        with pytest.raises(Exception):
            await processor.send_ibet_tx()
        async_db.expire_all()

        ava_to_ibet_tx_af = (
            await async_db.scalars(
                select(AvaToIbetBridgeTx).where(AvaToIbetBridgeTx.tx_id == tx_id)
            )
        ).one()
        assert ava_to_ibet_tx_af.tx_hash is None
        assert ava_to_ibet_tx_af.block_number is None
        assert ava_to_ibet_tx_af.status == ToIbetBridgeTxStatus.PENDING
        assert caplog.messages == [
            f"Sending ibet bridge transaction: id={tx_id}, type=force_unlock",
        ]
