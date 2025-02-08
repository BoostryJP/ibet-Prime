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
from datetime import datetime
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
)
from app.model.db import LedgerCreationRequest, LedgerCreationStatus, TokenType
from batch.processor_create_ledger import LOG, Processor


@pytest.fixture(scope="function")
def processor(async_db):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True

    yield Processor(is_shutdown=asyncio.Event())

    log.propagate = False
    log.setLevel(default_log_level)


@pytest.mark.asyncio
class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # The ledger creation request does not exist.
    # -> skip end
    async def test_normal_1(self, processor, async_db, caplog):
        # Execute batch
        await processor.process()

        # Assertion
        assert caplog.messages == ["Process Start", "Process End"]

    # <Normal_2>
    # The personal information has not been fully registered yet.
    # -> Not be finalized
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch(
        "batch.processor_create_ledger.sync_request_with_registered_personal_info",
        AsyncMock(return_value=(1, 0)),
    )
    async def test_normal_2(self, token_mock, processor, async_db, caplog):
        request_id = "test_request_id"
        token_address = "test_token_address"
        issuer_address = "test_issuer_address"

        # Prepare data: LedgerCreationRequest
        ledger_req = LedgerCreationRequest()
        ledger_req.request_id = request_id
        ledger_req.token_type = TokenType.IBET_SHARE
        ledger_req.token_address = token_address
        ledger_req.status = LedgerCreationStatus.PROCESSING
        async_db.add(ledger_req)
        await async_db.commit()

        # Mock: IbetShareContract.get
        mock_token = IbetShareContract()
        mock_token.issuer_address = issuer_address
        mock_token.token_address = token_address
        token_mock.side_effect = [mock_token]

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        assert caplog.messages == [
            "Process Start",
            f"Personal information fields have been updated: {request_id} 0/1",
            "Process End",
        ]

    # <Normal_3_1>
    # Finalize ledger
    # - IbetShareContract
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch(
        "batch.processor_create_ledger.sync_request_with_registered_personal_info",
        AsyncMock(return_value=(1, 1)),
    )
    @mock.patch(
        "batch.processor_create_ledger.finalize_ledger", AsyncMock(return_value=None)
    )
    async def test_normal_3_1(self, token_mock, processor, async_db, caplog):
        request_id = "test_request_id"
        token_address = "test_token_address"
        issuer_address = "test_issuer_address"

        # Prepare data: LedgerCreationRequest
        ledger_req = LedgerCreationRequest()
        ledger_req.request_id = request_id
        ledger_req.token_type = TokenType.IBET_SHARE
        ledger_req.token_address = token_address
        ledger_req.status = LedgerCreationStatus.PROCESSING
        async_db.add(ledger_req)
        await async_db.commit()

        # Mock: IbetShareContract.get
        mock_token = IbetShareContract()
        mock_token.issuer_address = issuer_address
        mock_token.token_address = token_address
        token_mock.side_effect = [mock_token]

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        ledger_req = (
            await async_db.scalars(select(LedgerCreationRequest).limit(1))
        ).first()
        assert ledger_req.status == LedgerCreationStatus.COMPLETED

        assert caplog.messages == [
            "Process Start",
            f"Personal information fields have been updated: {request_id} 1/1",
            f"The ledger has been created: {request_id} {token_address}",
            "Process End",
        ]

    # <Normal_3_2>
    # Finalize ledger
    # - IbetStraightBondContract
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @mock.patch(
        "batch.processor_create_ledger.sync_request_with_registered_personal_info",
        AsyncMock(return_value=(1, 1)),
    )
    @mock.patch(
        "batch.processor_create_ledger.finalize_ledger", AsyncMock(return_value=None)
    )
    async def test_normal_3_2(self, token_mock, processor, async_db, caplog):
        request_id = "test_request_id"
        token_address = "test_token_address"
        issuer_address = "test_issuer_address"

        # Prepare data: LedgerCreationRequest
        ledger_req = LedgerCreationRequest()
        ledger_req.request_id = request_id
        ledger_req.token_type = TokenType.IBET_STRAIGHT_BOND
        ledger_req.token_address = token_address
        ledger_req.status = LedgerCreationStatus.PROCESSING
        async_db.add(ledger_req)
        await async_db.commit()

        # Mock: IbetShareContract.get
        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = issuer_address
        mock_token.token_address = token_address
        mock_token.face_value_currency = "JPY"
        token_mock.side_effect = [mock_token]

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        ledger_req = (
            await async_db.scalars(select(LedgerCreationRequest).limit(1))
        ).first()
        assert ledger_req.status == LedgerCreationStatus.COMPLETED

        assert caplog.messages == [
            "Process Start",
            f"Personal information fields have been updated: {request_id} 1/1",
            f"The ledger has been created: {request_id} {token_address}",
            "Process End",
        ]

    # <Normal_4_1>
    # Finalize ledger (time limit exceeded)
    # - IbetShareContract
    @pytest.mark.freeze_time("2024-11-09 00:00:01")
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    @mock.patch(
        "batch.processor_create_ledger.sync_request_with_registered_personal_info",
        AsyncMock(return_value=(1, 0)),
    )
    @mock.patch(
        "batch.processor_create_ledger.finalize_ledger", AsyncMock(return_value=None)
    )
    async def test_normal_4_1(self, token_mock, processor, async_db, caplog):
        request_id = "test_request_id"
        token_address = "test_token_address"
        issuer_address = "test_issuer_address"

        # Prepare data: LedgerCreationRequest
        ledger_req = LedgerCreationRequest()
        ledger_req.request_id = request_id
        ledger_req.token_type = TokenType.IBET_SHARE
        ledger_req.token_address = token_address
        ledger_req.status = LedgerCreationStatus.PROCESSING
        ledger_req.created = datetime(2024, 11, 8, 18, 0, 0)
        async_db.add(ledger_req)
        await async_db.commit()

        # Mock: IbetShareContract.get
        mock_token = IbetShareContract()
        mock_token.issuer_address = issuer_address
        mock_token.token_address = token_address
        token_mock.side_effect = [mock_token]

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        ledger_req = (
            await async_db.scalars(select(LedgerCreationRequest).limit(1))
        ).first()
        assert ledger_req.status == LedgerCreationStatus.COMPLETED

        assert caplog.messages == [
            "Process Start",
            f"Personal information fields have been updated: {request_id} 0/1",
            f"The ledger has been created (time limit exceeded): {request_id} {token_address}",
            "Process End",
        ]

    # <Normal_4_2>
    # Finalize ledger (time limit exceeded)
    # - IbetStraightBondContract
    @pytest.mark.freeze_time("2024-11-09 00:00:01")
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    @mock.patch(
        "batch.processor_create_ledger.sync_request_with_registered_personal_info",
        AsyncMock(return_value=(1, 0)),
    )
    @mock.patch(
        "batch.processor_create_ledger.finalize_ledger", AsyncMock(return_value=None)
    )
    async def test_normal_4_2(self, token_mock, processor, async_db, caplog):
        request_id = "test_request_id"
        token_address = "test_token_address"
        issuer_address = "test_issuer_address"

        # Prepare data: LedgerCreationRequest
        ledger_req = LedgerCreationRequest()
        ledger_req.request_id = request_id
        ledger_req.token_type = TokenType.IBET_STRAIGHT_BOND
        ledger_req.token_address = token_address
        ledger_req.status = LedgerCreationStatus.PROCESSING
        ledger_req.created = datetime(2024, 11, 8, 18, 0, 0)
        async_db.add(ledger_req)
        await async_db.commit()

        # Mock: IbetShareContract.get
        mock_token = IbetStraightBondContract()
        mock_token.issuer_address = issuer_address
        mock_token.token_address = token_address
        mock_token.face_value_currency = "JPY"
        token_mock.side_effect = [mock_token]

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        ledger_req = (
            await async_db.scalars(select(LedgerCreationRequest).limit(1))
        ).first()
        assert ledger_req.status == LedgerCreationStatus.COMPLETED

        assert caplog.messages == [
            "Process Start",
            f"Personal information fields have been updated: {request_id} 0/1",
            f"The ledger has been created (time limit exceeded): {request_id} {token_address}",
            "Process End",
        ]
