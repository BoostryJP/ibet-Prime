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
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select
from web3.datastructures import AttributeDict

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import (
    Account,
    Notification,
    NotificationType,
    ScheduledEvents,
    ScheduledEventType,
    TokenType,
    TokenUpdateOperationCategory,
    TokenUpdateOperationLog,
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_scheduled_events import LOG, Processor
from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
def processor(async_db):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield Processor(worker_num=0, is_shutdown=asyncio.Event())
    log.propagate = False
    log.setLevel(default_log_level)


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # IbetStraightBond
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test1"
        _token_address_2 = "token_address_test2"
        _token_address_3 = "token_address_test3"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_past_utc = datetime.now(UTC) + timedelta(days=-1)
        datetime_now_utc = datetime.now(UTC)
        datetime_pending_utc = datetime.now(UTC) + timedelta(days=1)
        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "image_url": [
                "http://sampleurl.com/some_image1.png",
                "http://sampleurl.com/some_image2.png",
                "http://sampleurl.com/some_image3.png",
            ],
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False,
        }

        # TokenType: STRAIGHT_BOND, status is 2, will not change
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_1
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_past_utc.replace(tzinfo=None)
        token_event.status = 2
        token_event.data = update_data
        async_db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "1: Succeeded"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_2
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "0: Pending"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_3
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_pending_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        await async_db.commit()

        # mock
        IbetStraightBondContract_update = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.update",
            return_value=None,
        )
        IbetStraightBondContract_get = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.get",
            return_value=AttributeDict({}),
        )

        with IbetStraightBondContract_update, IbetStraightBondContract_get:
            # Execute batch
            await processor.process()
            async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address_1)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address_2)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 1
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address_3)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 0
        _operation_log = (
            await async_db.scalars(
                select(TokenUpdateOperationLog)
                .where(TokenUpdateOperationLog.token_address == _token_address_2)
                .limit(1)
            )
        ).first()
        assert _operation_log.issuer_address == _issuer_address
        assert _operation_log.type == TokenType.IBET_STRAIGHT_BOND
        assert _operation_log.arguments == {
            "contact_information": "問い合わせ先test",
            "face_value": 10000,
            "interest_payment_date": ["0101", "0701"],
            "interest_rate": 0.5,
            "is_offering": False,
            "is_redeemed": True,
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "privacy_policy": "プライバシーポリシーtest",
            "redemption_value": 11000,
            "status": False,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "transferable": False,
        }
        assert _operation_log.original_contents == {}
        assert (
            _operation_log.operation_category
            == TokenUpdateOperationCategory.UPDATE.value
        )

    # <Normal_2>
    # IbetShare
    @pytest.mark.asyncio
    async def test_normal_2(self, processor, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test_1"
        _token_address_2 = "token_address_test_2"
        _token_address_3 = "token_address_test_3"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_past_utc = datetime.now(UTC) + timedelta(days=-1)
        datetime_now_utc = datetime.now(UTC)
        datetime_pending_utc = datetime.now(UTC) + timedelta(days=1)

        update_data = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "image_url": [
                "http://sampleurl.com/some_image1.png",
                "http://sampleurl.com/some_image2.png",
                "http://sampleurl.com/some_image3.png",
            ],
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False,
        }

        # TokenType: STRAIGHT_BOND, status is 2, will not change
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_1
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_past_utc.replace(tzinfo=None)
        token_event.status = 2
        token_event.data = update_data
        async_db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "1: Succeeded"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_2
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "0: Pending"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_3
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_pending_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        await async_db.commit()

        # mock
        IbetShareContract_update = patch(
            target="app.model.blockchain.token.IbetShareContract.update",
            return_value=None,
        )
        IbetShareContract_get = patch(
            target="app.model.blockchain.token.IbetShareContract.get",
            return_value=AttributeDict({}),
        )

        with IbetShareContract_update, IbetShareContract_get:
            # Execute batch
            await processor.process()
            async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address_1)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address_2)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 1
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address_3)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 0
        _operation_log = (
            await async_db.scalars(
                select(TokenUpdateOperationLog)
                .where(TokenUpdateOperationLog.token_address == _token_address_2)
                .limit(1)
            )
        ).first()
        assert _operation_log.issuer_address == _issuer_address
        assert _operation_log.type == TokenType.IBET_SHARE
        assert _operation_log.arguments == {
            "cancellation_date": "20221231",
            "contact_information": "問い合わせ先test",
            "dividend_payment_date": "20211231",
            "dividend_record_date": "20211231",
            "dividends": 345.67,
            "is_canceled": False,
            "is_offering": False,
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "privacy_policy": "プライバシーポリシーtest",
            "status": False,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "transferable": False,
        }
        assert _operation_log.original_contents == {}
        assert (
            _operation_log.operation_category
            == TokenUpdateOperationCategory.UPDATE.value
        )

    # <Normal_3>
    # soft_deleted events
    @pytest.mark.asyncio
    async def test_normal_3(self, processor, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test1"
        _token_address_2 = "token_address_test2"
        _token_address_3 = "token_address_test3"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_pending_utc = datetime.now(UTC) + timedelta(days=1)
        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "image_url": [
                "http://sampleurl.com/some_image1.png",
                "http://sampleurl.com/some_image2.png",
                "http://sampleurl.com/some_image3.png",
            ],
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False,
        }

        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_1
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_pending_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        token_event.is_soft_deleted = True
        async_db.add(token_event)

        await async_db.commit()

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address_1)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 0

        _operation_log = (
            await async_db.scalars(
                select(TokenUpdateOperationLog)
                .where(TokenUpdateOperationLog.token_address == _token_address_1)
                .limit(1)
            )
        ).first()
        assert _operation_log is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Account does not exist
    @pytest.mark.asyncio
    async def test_error_1(self, processor, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(UTC)
        update_data = {}

        # TokenType: STRAIGHT_BOND, status is 2, will not change
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        await async_db.commit()

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2

        _notification = (await async_db.scalars(select(Notification).limit(1))).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 0
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": _token_address,
        }

    # <Error_2>
    # fail to get the private key
    @pytest.mark.asyncio
    async def test_error_2(self, processor, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(UTC)
        update_data = {}

        # TokenType: STRAIGHT_BOND, status is 0: Pending, will be 2: Failed
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        await async_db.commit()

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2
        _notification = (await async_db.scalars(select(Notification).limit(1))).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 1
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_SHARE,
            "token_address": _token_address,
        }

    # <Error_3>
    # IbetStraightBond : SendTransactionError
    @pytest.mark.asyncio
    async def test_error_3(self, processor, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(UTC)
        update_data = {}

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        await async_db.commit()

        # mock
        IbetStraightBondContract_update = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.update",
            side_effect=SendTransactionError(),
        )
        IbetStraightBondContract_get = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.get",
            return_value=AttributeDict({}),
        )

        with IbetStraightBondContract_update, IbetStraightBondContract_get:
            # Execute batch
            await processor.process()
            async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2
        _notification = (await async_db.scalars(select(Notification).limit(1))).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": _token_address,
        }

    # <Error_4>
    # IbetShare : SendTransactionError
    @pytest.mark.asyncio
    async def test_error_4(self, processor, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(UTC)
        update_data = {}

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        await async_db.commit()

        # mock
        IbetShareContract_update = patch(
            target="app.model.blockchain.token.IbetShareContract.update",
            side_effect=SendTransactionError(),
        )

        IbetShareContract_get = patch(
            target="app.model.blockchain.token.IbetShareContract.get",
            return_value=AttributeDict({}),
        )

        with IbetShareContract_update, IbetShareContract_get:
            # Execute batch
            await processor.process()
            async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2
        _notification = (await async_db.scalars(select(Notification).limit(1))).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_SHARE,
            "token_address": _token_address,
        }

    # <Error_5>
    # IbetStraightBond : ContractRevertError
    @pytest.mark.asyncio
    async def test_error_5(self, processor, async_db, caplog):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(UTC)
        update_data = {}

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)

        await async_db.commit()

        # mock
        IbetStraightBondContract_update = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.update",
            side_effect=ContractRevertError("999999"),
        )

        IbetStraightBondContract_get = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.get",
            return_value=AttributeDict({}),
        )

        with IbetStraightBondContract_update, IbetStraightBondContract_get:
            # Execute batch
            await processor.process()
            async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2
        _notification = (await async_db.scalars(select(Notification).limit(1))).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": _token_address,
        }
        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARNING,
                    f"Transaction reverted: id=<{token_event.id}> error_code:<999999> error_msg:<>",
                )
            )
            == 1
        )

    # <Error_6>
    # IbetShare : ContractRevertError
    @pytest.mark.asyncio
    async def test_error_6(self, processor, async_db, caplog):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        async_db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(UTC)
        update_data = {}

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc.replace(tzinfo=None)
        token_event.status = 0
        token_event.data = update_data
        async_db.add(token_event)
        await async_db.commit()
        token_event_id = token_event.id

        # mock
        IbetShareContract_update = patch(
            target="app.model.blockchain.token.IbetShareContract.update",
            side_effect=ContractRevertError("999999"),
        )

        IbetShareContract_get = patch(
            target="app.model.blockchain.token.IbetShareContract.get",
            return_value=AttributeDict({}),
        )

        with IbetShareContract_update, IbetShareContract_get:
            # Execute batch
            await processor.process()
            async_db.expire_all()

        # Assertion
        _scheduled_event = (
            await async_db.scalars(
                select(ScheduledEvents)
                .where(ScheduledEvents.token_address == _token_address)
                .limit(1)
            )
        ).first()
        assert _scheduled_event.status == 2
        _notification = (await async_db.scalars(select(Notification).limit(1))).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_SHARE,
            "token_address": _token_address,
        }

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARNING,
                    f"Transaction reverted: id=<{token_event_id}> error_code:<999999> error_msg:<>",
                )
            )
            == 1
        )
