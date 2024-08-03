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

import asyncio
import logging
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from web3.exceptions import TimeExhausted

from app.exceptions import SendTransactionError
from app.model.blockchain.tx_params.ibet_security_token_dvp import (
    CreateDeliveryParams,
    WithdrawPartialParams,
)
from app.model.db import (
    Account,
    DVPAsyncProcess,
    DVPAsyncProcessRevertTxStatus,
    DVPAsyncProcessStatus,
    DVPAsyncProcessStepTxStatus,
    DVPAsyncProcessType,
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_dvp_async_tx import LOG, Processor
from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
def processor(db, caplog: pytest.LogCaptureFixture):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield Processor(asyncio.Event())
    log.propagate = False
    log.setLevel(default_log_level)


class TestProcessor:
    issuer_account = config_eth_account("user1")
    issuer_address = issuer_account["address"]
    issuer_keyfile = issuer_account["keyfile_json"]
    issuer_eoa_password = E2EEUtils.encrypt("password")
    issuer_pk = decode_keyfile_json(
        raw_keyfile_json=issuer_keyfile,
        password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8"),
    )

    user_account = config_eth_account("user2")
    user_address = user_account["address"]

    agent_account = config_eth_account("user3")
    agent_address = agent_account["address"]

    dvp_contract_address = "0xabcDEF1234567890AbcDEf123456789000000003"
    token_address = "0xABCdeF1234567890abcdEf123456789000000000"

    ###############################################################################
    # 1. send_step_tx
    ###############################################################################

    # Normal_1_1
    # There is no data to process.
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, db, caplog):
        # Execute processor
        await processor.process()

        # Assertion
        assert caplog.messages == ["Process Start", "Process End"]

    # Normal_1_2
    # __send_step_tx
    # - DVPAsyncProcessType: CREATE_DELIVERY
    @pytest.mark.parametrize(
        "step_tx_status",
        [
            DVPAsyncProcessStepTxStatus.DONE,
            DVPAsyncProcessStepTxStatus.RETRY,
        ],
    )
    @pytest.mark.asyncio
    async def test_normal_1_2(self, step_tx_status, processor, db, caplog):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 0
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = step_tx_status
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        with (
            patch(
                target="app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.create_delivery",
                return_value="mock_create_delivery_tx_hash",
            ) as mocked_create_delivery,
            patch(
                "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt",
                MagicMock(side_effect=TimeExhausted()),
            ),
        ):
            await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step == 1
        assert after_dvp_process.step_tx_hash == "mock_create_delivery_tx_hash"
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.PENDING

        mocked_create_delivery.assert_called_with(
            data=CreateDeliveryParams(
                token_address=self.token_address,
                buyer_address=self.user_address,
                amount=10,
                agent_address=self.agent_address,
                data="test_data",
            ),
            tx_from=self.issuer_address,
            private_key=self.issuer_pk,
        )

        assert caplog.messages == [
            "Process Start",
            "[SendStepTx] Start: record_id=1",
            "[SendStepTx] Sent transaction: record_id=1, process_type=CreateDelivery, step=1",
            "[SendStepTx] End: record_id=1",
            "[SyncStepTxResult] Start: record_id=1",
            "[SyncStepTxResult] End: record_id=1",
            "Process End",
        ]

    # Normal_1_3
    # __send_step_tx
    # - DVPAsyncProcessType: CANCEL_DELIVERY, FINISH_DELIVERY, ABORT_DELIVERY
    @pytest.mark.parametrize(
        "process_type",
        [
            DVPAsyncProcessType.CANCEL_DELIVERY,
            DVPAsyncProcessType.FINISH_DELIVERY,
            DVPAsyncProcessType.ABORT_DELIVERY,
        ],
    )
    @pytest.mark.asyncio
    async def test_normal_1_3(self, process_type, processor, db, caplog):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = process_type
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 0
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.DONE
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        with (
            patch(
                target="app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.withdraw_partial",
                return_value="mocked_withdraw_partial_tx_hash",
            ) as mocked_withdraw_partial,
            patch(
                "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt",
                MagicMock(side_effect=TimeExhausted()),
            ),
        ):
            await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step == 1
        assert after_dvp_process.step_tx_hash == "mocked_withdraw_partial_tx_hash"
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.PENDING

        mocked_withdraw_partial.assert_called_with(
            data=WithdrawPartialParams(
                token_address=self.token_address,
                value=10,
            ),
            tx_from=self.issuer_address,
            private_key=self.issuer_pk,
        )

        assert caplog.messages == [
            "Process Start",
            "[SendStepTx] Start: record_id=1",
            f"[SendStepTx] Sent transaction: record_id=1, process_type={process_type}, step=1",
            "[SendStepTx] End: record_id=1",
            "[SyncStepTxResult] Start: record_id=1",
            "[SyncStepTxResult] End: record_id=1",
            "Process End",
        ]

    # Error_1_1
    # __send_step_tx
    # - Failed to get issuer's private key
    @pytest.mark.asyncio
    async def test_error_1_1(self, processor, db, caplog):
        # Prepare data
        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 0
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.DONE
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step == 0
        assert after_dvp_process.step_tx_hash == "tx_hash"
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.DONE
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SendStepTx] Start: record_id=1",
            "[SendStepTx] Failed to get issuer's private key",
            "[SendStepTx] End: record_id=1",
            "Process End",
        ]

    # Error_1_2
    # __send_step_tx
    # - SendTransactionError
    @pytest.mark.asyncio
    async def test_error_1_2(self, processor, db, caplog):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 0
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.DONE
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        with (
            patch(
                "app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.create_delivery",
                MagicMock(side_effect=SendTransactionError()),
            ),
        ):
            await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step == 0
        assert after_dvp_process.step_tx_hash == "tx_hash"
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.DONE
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SendStepTx] Start: record_id=1",
            "[SendStepTx] Failed to send step transaction: record_id=1",
            "[SendStepTx] End: record_id=1",
            "Process End",
        ]

    ###############################################################################
    # 2. sync_step_tx_result
    ###############################################################################

    # Normal_2_1
    # __sync_step_tx_result
    # - The transaction remains pending.
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @pytest.mark.asyncio
    async def test_normal_2_1(self, mocked_wait_for_tx, processor, db, caplog):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [TimeExhausted()]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.PENDING
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncStepTxResult] Start: record_id=1",
            "[SyncStepTxResult] End: record_id=1",
            "Process End",
        ]

    # Normal_2_2
    # __sync_step_tx_result
    # - <Success>
    @pytest.mark.parametrize(
        "process_type",
        [
            DVPAsyncProcessType.CREATE_DELIVERY,
            DVPAsyncProcessType.CANCEL_DELIVERY,
            DVPAsyncProcessType.FINISH_DELIVERY,
            DVPAsyncProcessType.ABORT_DELIVERY,
        ],
    )
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @pytest.mark.asyncio
    async def test_normal_2_2(
        self, mocked_wait_for_tx, process_type, processor, db, caplog
    ):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = process_type
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [{"status": 1}]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.DONE
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.DONE_SUCCESS

        assert caplog.messages == [
            "Process Start",
            "[SyncStepTxResult] Start: record_id=1",
            "[SyncStepTxResult] End: record_id=1",
            "Process End",
        ]

    # Normal_2_3_1
    # __sync_step_tx_result
    # - DVPAsyncProcessType: CREATE_DELIVERY
    # - <Reverted> -> WithdrawPartial
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.withdraw_partial"
    )
    @pytest.mark.asyncio
    async def test_normal_2_3_1(
        self, mocked_withdraw_partial, mocked_wait_for_tx, processor, db, caplog
    ):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [
            {"status": 0},
            TimeExhausted(),
        ]
        mocked_withdraw_partial.side_effect = ["mocked_withdraw_partial_tx_hash"]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.FAILED
        assert after_dvp_process.revert_tx_hash == "mocked_withdraw_partial_tx_hash"
        assert (
            after_dvp_process.revert_tx_status == DVPAsyncProcessRevertTxStatus.PENDING
        )
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        mocked_withdraw_partial.assert_called_with(
            data=WithdrawPartialParams(
                token_address=self.token_address,
                value=10,
            ),
            tx_from=self.issuer_address,
            private_key=self.issuer_pk,
        )

        assert caplog.messages == [
            "Process Start",
            "[SyncStepTxResult] Start: record_id=1",
            "[SyncStepTxResult] Step transaction has been reverted: record_id=1, process_type=CreateDelivery, step=1",
            "[SyncStepTxResult] Sent revert transaction: record_id=1, process_type=CreateDelivery, step=1",
            "[SyncStepTxResult] End: record_id=1",
            "[SyncRevertTxResult] Start: record_id=1",
            "[SyncRevertTxResult] End: record_id=1",
            "Process End",
        ]

    # Normal_2_3_2
    # __sync_step_tx_result
    # - DVPAsyncProcessType: CANCEL_DELIVERY, FINISH_DELIVERY, ABORT_DELIVERY
    # - <Reverted> -> Retry
    @pytest.mark.parametrize(
        "process_type",
        [
            DVPAsyncProcessType.CANCEL_DELIVERY,
            DVPAsyncProcessType.FINISH_DELIVERY,
            DVPAsyncProcessType.ABORT_DELIVERY,
        ],
    )
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @pytest.mark.asyncio
    async def test_normal_2_3_2(
        self, mocked_wait_for_tx, process_type, processor, db, caplog
    ):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = process_type
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [
            {"status": 0},
        ]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_hash is None
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.RETRY
        assert after_dvp_process.revert_tx_hash is None
        assert after_dvp_process.revert_tx_status is None
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncStepTxResult] Start: record_id=1",
            f"[SyncStepTxResult] Step transaction has been reverted: record_id=1, process_type={process_type}, step=1",
            "[SyncStepTxResult] End: record_id=1",
            "Process End",
        ]

    # Error_2_1
    # __sync_step_tx_result
    # - Failed to get issuer's private key
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.withdraw_partial"
    )
    @pytest.mark.asyncio
    async def test_error_2_1(
        self, mocked_withdraw_partial, mocked_wait_for_tx, processor, db, caplog
    ):
        # Prepare data
        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [
            {"status": 0},
        ]
        mocked_withdraw_partial.side_effect = [SendTransactionError()]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.PENDING
        assert after_dvp_process.revert_tx_hash is None
        assert after_dvp_process.revert_tx_status is None
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncStepTxResult] Start: record_id=1",
            "[SyncStepTxResult] Step transaction has been reverted: record_id=1, process_type=CreateDelivery, step=1",
            "[SyncStepTxResult] Failed to get issuer's private key",
            "[SyncStepTxResult] End: record_id=1",
            "Process End",
        ]

    # Error_2_2
    # __sync_step_tx_result
    # - SendTransactionError
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.withdraw_partial"
    )
    @pytest.mark.asyncio
    async def test_error_2_2(
        self, mocked_withdraw_partial, mocked_wait_for_tx, processor, db, caplog
    ):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [
            {"status": 0},
        ]
        mocked_withdraw_partial.side_effect = [SendTransactionError()]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.PENDING
        assert after_dvp_process.revert_tx_hash is None
        assert after_dvp_process.revert_tx_status is None
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncStepTxResult] Start: record_id=1",
            "[SyncStepTxResult] Step transaction has been reverted: record_id=1, process_type=CreateDelivery, step=1",
            "[SyncStepTxResult] Failed to send revert transaction: record_id=1, process_type=CreateDelivery, step=1",
            "[SyncStepTxResult] End: record_id=1",
            "Process End",
        ]

    ###############################################################################
    # sync_revert_tx_result
    ###############################################################################

    # Normal_3_1
    # __sync_revert_tx_result
    # - DVPAsyncProcessType: CREATE_DELIVERY
    # - The transaction remains pending.
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @pytest.mark.asyncio
    async def test_normal_3_1(self, mocked_wait_for_tx, processor, db, caplog):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.FAILED
        _dvp_process.revert_tx_hash = "revert_tx_hash"
        _dvp_process.revert_tx_status = DVPAsyncProcessRevertTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [TimeExhausted()]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.FAILED
        assert after_dvp_process.revert_tx_hash == "revert_tx_hash"
        assert (
            after_dvp_process.revert_tx_status == DVPAsyncProcessRevertTxStatus.PENDING
        )
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncRevertTxResult] Start: record_id=1",
            "[SyncRevertTxResult] End: record_id=1",
            "Process End",
        ]

    # Normal_3_2
    # __sync_revert_tx_result
    # - DVPAsyncProcessType: CREATE_DELIVERY
    # - <Success>
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @pytest.mark.asyncio
    async def test_normal_3_2(self, mocked_wait_for_tx, processor, db, caplog):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.FAILED
        _dvp_process.revert_tx_hash = "revert_tx_hash"
        _dvp_process.revert_tx_status = DVPAsyncProcessRevertTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [{"status": 1}]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.FAILED
        assert after_dvp_process.revert_tx_hash == "revert_tx_hash"
        assert after_dvp_process.revert_tx_status == DVPAsyncProcessRevertTxStatus.DONE
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.DONE_FAILED

        assert caplog.messages == [
            "Process Start",
            "[SyncRevertTxResult] Start: record_id=1",
            "[SyncRevertTxResult] End: record_id=1",
            "Process End",
        ]

    # Normal_3_3
    # __sync_revert_tx_result
    # - DVPAsyncProcessType: CREATE_DELIVERY
    # - <Reverted> -> Resend revert transaction
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.withdraw_partial"
    )
    @pytest.mark.asyncio
    async def test_normal_3_3(
        self, mocked_withdraw_partial, mocked_wait_for_tx, processor, db, caplog
    ):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.FAILED
        _dvp_process.revert_tx_hash = "revert_tx_hash"
        _dvp_process.revert_tx_status = DVPAsyncProcessRevertTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [{"status": 0}]
        mocked_withdraw_partial.side_effect = ["mocked_withdraw_tx_hash"]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.FAILED
        assert after_dvp_process.revert_tx_hash == "mocked_withdraw_tx_hash"
        assert (
            after_dvp_process.revert_tx_status == DVPAsyncProcessRevertTxStatus.PENDING
        )
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncRevertTxResult] Start: record_id=1",
            "[SyncRevertTxResult] Revert transaction has been reverted: record_id=1, process_type=CreateDelivery",
            "[SyncRevertTxResult] Resent revert transaction: record_id=1, process_type=CreateDelivery",
            "[SyncRevertTxResult] End: record_id=1",
            "Process End",
        ]

    # Error_3_1
    # __sync_revert_tx_result
    # - <Reverted>
    # - Failed to get issuer's private key
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.withdraw_partial"
    )
    @pytest.mark.asyncio
    async def test_error_3_1(
        self, mocked_withdraw_partial, mocked_wait_for_tx, processor, db, caplog
    ):
        # Prepare data
        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.FAILED
        _dvp_process.revert_tx_hash = "revert_tx_hash"
        _dvp_process.revert_tx_status = DVPAsyncProcessRevertTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [{"status": 0}]
        mocked_withdraw_partial.side_effect = ["mocked_withdraw_tx_hash"]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.FAILED
        assert after_dvp_process.revert_tx_hash == "revert_tx_hash"
        assert (
            after_dvp_process.revert_tx_status == DVPAsyncProcessRevertTxStatus.PENDING
        )
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncRevertTxResult] Start: record_id=1",
            "[SyncRevertTxResult] Revert transaction has been reverted: record_id=1, process_type=CreateDelivery",
            "[SyncRevertTxResult] Failed to get issuer's private key",
            "[SyncRevertTxResult] End: record_id=1",
            "Process End",
        ]

    # Error_3_2
    # __sync_revert_tx_result
    # - <Reverted>
    # - SendTransactionError
    @mock.patch(
        "app.utils.contract_utils.AsyncContractUtils.wait_for_transaction_receipt"
    )
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenDVPNoWait.withdraw_partial"
    )
    @pytest.mark.asyncio
    async def test_error_3_2(
        self, mocked_withdraw_partial, mocked_wait_for_tx, processor, db, caplog
    ):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.keyfile = self.issuer_keyfile
        _account.eoa_password = self.issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        _dvp_process = DVPAsyncProcess()
        _dvp_process.issuer_address = self.issuer_address
        _dvp_process.process_type = DVPAsyncProcessType.CREATE_DELIVERY
        _dvp_process.dvp_contract_address = self.dvp_contract_address
        _dvp_process.token_address = self.token_address
        _dvp_process.seller_address = self.issuer_address
        _dvp_process.buyer_address = self.user_address
        _dvp_process.amount = 10
        _dvp_process.agent_address = self.agent_address
        _dvp_process.data = "test_data"
        _dvp_process.delivery_id = 1
        _dvp_process.step = 1
        _dvp_process.step_tx_hash = "tx_hash"
        _dvp_process.step_tx_status = DVPAsyncProcessStepTxStatus.FAILED
        _dvp_process.revert_tx_hash = "revert_tx_hash"
        _dvp_process.revert_tx_status = DVPAsyncProcessRevertTxStatus.PENDING
        _dvp_process.process_status = DVPAsyncProcessStatus.PROCESSING
        db.add(_dvp_process)

        db.commit()

        # Execute processor
        mocked_wait_for_tx.side_effect = [{"status": 0}]
        mocked_withdraw_partial.side_effect = [SendTransactionError()]
        await processor.process()

        # Assertion
        after_dvp_process: DVPAsyncProcess = db.scalars(
            select(DVPAsyncProcess).where(DVPAsyncProcess.id == 1).limit(1)
        ).first()
        assert after_dvp_process.step_tx_status == DVPAsyncProcessStepTxStatus.FAILED
        assert after_dvp_process.revert_tx_hash == "revert_tx_hash"
        assert (
            after_dvp_process.revert_tx_status == DVPAsyncProcessRevertTxStatus.PENDING
        )
        assert after_dvp_process.process_status == DVPAsyncProcessStatus.PROCESSING

        assert caplog.messages == [
            "Process Start",
            "[SyncRevertTxResult] Start: record_id=1",
            "[SyncRevertTxResult] Revert transaction has been reverted: record_id=1, process_type=CreateDelivery",
            "[SyncRevertTxResult] Failed to send revert transaction: record_id=1, process_type=CreateDelivery",
            "[SyncRevertTxResult] End: record_id=1",
            "Process End",
        ]
