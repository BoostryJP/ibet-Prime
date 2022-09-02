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
import pytest
from unittest.mock import patch
from datetime import (
    datetime,
    timedelta,
    timezone
)
from app.model.db import (
    Account,
    ScheduledEvents,
    ScheduledEventType,
    TokenType,
    Notification,
    NotificationType
)
from app.utils.e2ee_utils import E2EEUtils
from app.exceptions import (
    SendTransactionError,
    ContractRevertError
)
from batch.processor_scheduled_events import Processor, LOG

from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
def processor(db):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield Processor(thread_num=0)
    log.propagate = False
    log.setLevel(default_log_level)


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # IbetStraightBond
    # unset additional info
    def test_normal_1_1(self, processor, db):
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
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_past_utc = datetime.now(timezone.utc) + timedelta(days=-1)
        datetime_past_str = datetime_past_utc.isoformat()
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        datetime_pending_utc = datetime.now(timezone.utc) + timedelta(days=1)
        datetime_pending_str = datetime_pending_utc.isoformat()
        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "image_url": [
                "http://sampleurl.com/some_image1.png",
                "http://sampleurl.com/some_image2.png",
                "http://sampleurl.com/some_image3.png"
            ],
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False
        }

        # TokenType: STRAIGHT_BOND, status is 2, will not change
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_1
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_past_str
        token_event.status = 2
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "1: Succeeded"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_2
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "0: Pending"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_3
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_pending_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetStraightBondContract_update = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.update",
            return_value=None
        )

        with IbetStraightBondContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_1). \
            first()
        assert _scheduled_event.status == 2
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_2). \
            first()
        assert _scheduled_event.status == 1
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_3). \
            first()
        assert _scheduled_event.status == 0

    # <Normal_1_2>
    # IbetStraightBond
    # set additional info
    def test_normal_1_2(self, processor, db):
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
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_past_utc = datetime.now(timezone.utc) + timedelta(days=-1)
        datetime_past_str = datetime_past_utc.isoformat()
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        datetime_pending_utc = datetime.now(timezone.utc) + timedelta(days=1)
        datetime_pending_str = datetime_pending_utc.isoformat()
        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "image_url": [
                "http://sampleurl.com/some_image1.png",
                "http://sampleurl.com/some_image2.png",
                "http://sampleurl.com/some_image3.png"
            ],
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False,
        }

        # TokenType: STRAIGHT_BOND, status is 2, will not change
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_1
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_past_str
        token_event.status = 2
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "1: Succeeded"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_2
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "0: Pending"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_3
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_pending_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetStraightBondContract_update = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.update",
            return_value=None
        )

        with IbetStraightBondContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_1). \
            first()
        assert _scheduled_event.status == 2
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_2). \
            first()
        assert _scheduled_event.status == 1
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_3). \
            first()
        assert _scheduled_event.status == 0

    # <Normal_2_1>
    # IbetShare
    # unset additional info
    def test_normal_2_1(self, processor, db):
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
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_past_utc = datetime.now(timezone.utc) + timedelta(days=-1)
        datetime_past_str = datetime_past_utc.isoformat()
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        datetime_pending_utc = datetime.now(timezone.utc) + timedelta(days=1)
        datetime_pending_str = datetime_pending_utc.isoformat()

        update_data = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "image_url": [
                "http://sampleurl.com/some_image1.png",
                "http://sampleurl.com/some_image2.png",
                "http://sampleurl.com/some_image3.png"
            ],
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False
        }

        # TokenType: STRAIGHT_BOND, status is 2, will not change
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_1
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_past_str
        token_event.status = 2
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "1: Succeeded"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_2
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "0: Pending"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_3
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_pending_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetShareContract_update = patch(
            target="app.model.blockchain.token.IbetShareContract.update",
            return_value=None
        )

        with IbetShareContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_1). \
            first()
        assert _scheduled_event.status == 2
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_2). \
            first()
        assert _scheduled_event.status == 1
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_3). \
            first()
        assert _scheduled_event.status == 0

    # <Normal_2_2>
    # IbetShare
    # set additional info
    def test_normal_2_2(self, processor, db):
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
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_past_utc = datetime.now(timezone.utc) + timedelta(days=-1)
        datetime_past_str = datetime_past_utc.isoformat()
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        datetime_pending_utc = datetime.now(timezone.utc) + timedelta(days=1)
        datetime_pending_str = datetime_pending_utc.isoformat()

        update_data = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "image_url": [
                "http://sampleurl.com/some_image1.png",
                "http://sampleurl.com/some_image2.png",
                "http://sampleurl.com/some_image3.png"
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
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_past_str
        token_event.status = 2
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "1: Succeeded"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_2
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        # TokenType: STRAIGHT_BOND, status will be "0: Pending"
        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address_3
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_pending_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetShareContract_update = patch(
            target="app.model.blockchain.token.IbetShareContract.update",
            return_value=None
        )

        with IbetShareContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_1). \
            first()
        assert _scheduled_event.status == 2
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_2). \
            first()
        assert _scheduled_event.status == 1
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address_3). \
            first()
        assert _scheduled_event.status == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Account does not exist
    def test_error_1(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {}

        # TokenType: STRAIGHT_BOND, status is 2, will not change
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # Execute batch
        processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert _scheduled_event.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 0
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }

    # <Error_2>
    # fail to get the private key
    def test_error_2(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {}

        # TokenType: STRAIGHT_BOND, status is 0: Pending, will be 2: Failed
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # Execute batch
        processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert _scheduled_event.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 1
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_SHARE.value,
        }

    # <Error_3>
    # IbetStraightBond : SendTransactionError
    def test_error_3(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {
        }

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetStraightBondContract_update = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.update",
            side_effect=SendTransactionError()
        )

        with IbetStraightBondContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert _scheduled_event.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }

    # <Error_4>
    # IbetShare : SendTransactionError
    def test_error_4(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_jtc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_jtc.isoformat()

        update_data = {
        }

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetShareContract_update = patch(
            target="app.model.blockchain.token.IbetShareContract.update",
            side_effect=SendTransactionError()
        )

        with IbetShareContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert _scheduled_event.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_SHARE.value,
        }

    # <Error_5>
    # IbetStraightBond : ContractRevertError
    def test_error_5(self, processor, db, caplog):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {
        }

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetStraightBondContract_update = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.update",
            side_effect=ContractRevertError("999999")
        )

        with IbetStraightBondContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert _scheduled_event.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        assert caplog.record_tuples.count((
            LOG.name,
            logging.WARNING,
            f"Transaction reverted: id=<{token_event.id}> error_code:<999999> error_msg:<>"
        )) == 1

    # <Error_6>
    # IbetShare : ContractRevertError
    def test_error_6(self, processor, db, caplog):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _issuer_address
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # prepare data : ScheduledEvents
        datetime_now_jtc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_jtc.isoformat()

        update_data = {
        }

        # TokenType: STRAIGHT_BOND, status will be "2: Failed"
        token_event = ScheduledEvents()
        token_event.event_id = "event_id_1"
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        db.commit()

        # mock
        IbetShareContract_update = patch(
            target="app.model.blockchain.token.IbetShareContract.update",
            side_effect=ContractRevertError("999999")
        )

        with IbetShareContract_update:
            # Execute batch
            processor.process()

        # Assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert _scheduled_event.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {
            "scheduled_event_id": "event_id_1",
            "token_type": TokenType.IBET_SHARE.value,
        }

        assert caplog.record_tuples.count((
            LOG.name,
            logging.WARNING,
            f"Transaction reverted: id=<{token_event.id}> error_code:<999999> error_msg:<>"
        )) == 1
