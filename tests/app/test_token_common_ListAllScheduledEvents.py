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

import uuid
from datetime import datetime
from unittest import mock

import pytest
import pytz

from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import ScheduledEvents, ScheduledEventType, TokenType
from config import TZ
from tests.account_config import config_eth_account


class TestListAllScheduledEvents:
    # target API endpoint
    api_url = "tokens/scheduled_events"
    local_tz = pytz.timezone(TZ)

    test_issuer_address_1 = config_eth_account("user1")["address"]
    test_issuer_address_2 = config_eth_account("user2")["address"]

    test_token_1_address = "0x1234567890123456789012345678900000000010"
    test_token_1_name = "test_token_1"

    test_token_2_address = "0x1234567890123456789012345678900000000020"
    test_token_2_name = "test_token_2"

    test_token_3_address = "0x1234567890123456789012345678900000000030"
    test_token_3_name = "test_token_3"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(self.api_url)

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "scheduled_events": [],
        }

    # <Normal_2_1>
    # TokenType = IbetStraightBond
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_2_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        token_2 = IbetStraightBondContract()
        token_2_attr = {
            "issuer_address": self.test_issuer_address_2,
            "token_address": self.test_token_2_address,
            "name": self.test_token_2_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_2.__dict__ = token_2_attr

        mock_IbetStraightBondContract_get.side_effect = [token_2, token_1]

        # Request target API
        resp = await async_client.get(self.api_url)

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_2,
                    "token_address": self.test_token_2_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_2_attr,
                },
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
            ],
        }

    # <Normal_2_2>
    # TokenType = IbetShare
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    async def test_normal_2_2(self, mock_IbetShareContract_get, async_client, async_db):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        update_data = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False,
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetShareContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": False,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "issue_price": 999997,
            "cancellation_date": "99991231",
            "memo": "memo_test",
            "principal_value": 999998,
            "is_canceled": True,
            "dividends": 9.99,
            "dividend_record_date": "99991230",
            "dividend_payment_date": "99991229",
        }
        token_1.__dict__ = token_1_attr

        token_2 = IbetShareContract()
        token_2_attr = {
            "issuer_address": self.test_issuer_address_2,
            "token_address": self.test_token_2_address,
            "name": self.test_token_2_name,
            "symbol": "TEST-test",
            "total_supply": 999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": False,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "issue_price": 999997,
            "cancellation_date": "99991231",
            "memo": "memo_test",
            "principal_value": 999998,
            "is_canceled": True,
            "dividends": 9.99,
            "dividend_record_date": "99991230",
            "dividend_payment_date": "99991229",
        }
        token_2.__dict__ = token_2_attr

        mock_IbetShareContract_get.side_effect = [token_2, token_1]

        # Request target API
        resp = await async_client.get(self.api_url)

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_2,
                    "token_address": self.test_token_2_address,
                    "token_type": TokenType.IBET_SHARE,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_2_attr,
                },
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_SHARE,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
            ],
        }

    # <Normal_3>
    # Header(issuer_address) is set
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_3(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        mock_IbetStraightBondContract_get.side_effect = [token_1]

        # Request target API
        resp = await async_client.get(
            self.api_url,
            headers={"issuer-address": self.test_issuer_address_1},
        )

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": mock.ANY,
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": mock.ANY,
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
            ],
        }

    # <Normal_4_1>
    # Search Filter: token_type
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_4_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        # Prepare data: ScheduledEvents
        update_data_1 = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data_1
        token_event.created = create_datetime_1
        async_db.add(token_event)

        update_data_2 = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False,
            "memo": "memo_test1",
        }
        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data_2
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        mock_IbetStraightBondContract_get.side_effect = [token_1]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"token_type": "IbetStraightBond"}
        )

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": mock.ANY,
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data_1,
                    "created": mock.ANY,
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
            ],
        }

    # <Normal_4_2>
    # Search Filter: token_address
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_4_2(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        # Prepare data: ScheduledEvents
        update_data_1 = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data_1
        token_event.created = create_datetime_1
        async_db.add(token_event)

        update_data_2 = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "is_canceled": False,
            "memo": "memo_test1",
        }
        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data_2
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        mock_IbetStraightBondContract_get.side_effect = [token_1]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"token_address": self.test_token_1_address}
        )

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": mock.ANY,
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data_1,
                    "created": mock.ANY,
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
            ],
        }

    # <Normal_4_3>
    # Search Filter: status
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_4_3(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 1
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        mock_IbetStraightBondContract_get.side_effect = [token_1]

        # Request target API
        resp = await async_client.get(self.api_url, params={"status": 0})

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": mock.ANY,
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": mock.ANY,
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
            ],
        }

    # <Normal_5_1>
    # Sort: created
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_5_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        token_2 = IbetStraightBondContract()
        token_2_attr = {
            "issuer_address": self.test_issuer_address_2,
            "token_address": self.test_token_2_address,
            "name": self.test_token_2_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_2.__dict__ = token_2_attr

        mock_IbetStraightBondContract_get.side_effect = [token_1, token_2]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"sort_item": "created", "sort_order": 0}
        )

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
                {
                    "scheduled_event_id": event_id_2,
                    "token_address": self.test_token_2_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_2_attr,
                },
            ],
        }

    # <Normal_5_2>
    # Sort: scheduled_datetime
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_5_2(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        token_2 = IbetStraightBondContract()
        token_2_attr = {
            "issuer_address": self.test_issuer_address_2,
            "token_address": self.test_token_2_address,
            "name": self.test_token_2_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_2.__dict__ = token_2_attr

        mock_IbetStraightBondContract_get.side_effect = [token_1, token_2]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"sort_item": "scheduled_datetime", "sort_order": 0}
        )

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
                {
                    "scheduled_event_id": event_id_2,
                    "token_address": self.test_token_2_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_2_attr,
                },
            ],
        }

    # <Normal_5_3>
    # Sort: token_address
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_5_3(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)

        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_2
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_1 = IbetStraightBondContract()
        token_1_attr = {
            "issuer_address": self.test_issuer_address_1,
            "token_address": self.test_token_1_address,
            "name": self.test_token_1_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_1.__dict__ = token_1_attr

        token_2 = IbetStraightBondContract()
        token_2_attr = {
            "issuer_address": self.test_issuer_address_2,
            "token_address": self.test_token_2_address,
            "name": self.test_token_2_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_2.__dict__ = token_2_attr

        mock_IbetStraightBondContract_get.side_effect = [token_1, token_2]

        # Request target API
        resp = await async_client.get(
            self.api_url, params={"sort_item": "token_address", "sort_order": 0}
        )

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_1,
                    "token_address": self.test_token_1_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_1)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_1_attr,
                },
                {
                    "scheduled_event_id": event_id_2,
                    "token_address": self.test_token_2_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_2_attr,
                },
            ],
        }

    # <Normal_6>
    # Offset/Limit
    @pytest.mark.asyncio
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.get")
    async def test_normal_6(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        create_datetime_1 = datetime(2025, 2, 12, 0, 0, 0).replace(tzinfo=None)
        create_datetime_2 = datetime(2025, 2, 12, 0, 0, 1).replace(tzinfo=None)
        create_datetime_3 = datetime(2025, 2, 12, 0, 0, 2).replace(tzinfo=None)

        scheduled_datetime_1 = datetime(2025, 2, 15, 0, 0, 0).replace(tzinfo=None)
        scheduled_datetime_2 = datetime(2025, 2, 15, 0, 0, 1).replace(tzinfo=None)
        scheduled_datetime_3 = datetime(2025, 2, 15, 0, 0, 2).replace(tzinfo=None)

        update_data = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "memo": "memo_test1",
        }

        # Prepare data: ScheduledEvents
        event_id_1 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_1
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_1_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_1
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_1
        async_db.add(token_event)

        event_id_2 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_2
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_2_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_2
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_2
        async_db.add(token_event)

        event_id_3 = str(uuid.uuid4())
        token_event = ScheduledEvents()
        token_event.event_id = event_id_3
        token_event.issuer_address = self.test_issuer_address_1
        token_event.token_address = self.test_token_3_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = scheduled_datetime_3
        token_event.status = 0
        token_event.data = update_data
        token_event.created = create_datetime_3
        async_db.add(token_event)

        await async_db.commit()

        # Mock
        token_2 = IbetStraightBondContract()
        token_2_attr = {
            "issuer_address": self.test_issuer_address_2,
            "token_address": self.test_token_2_address,
            "name": self.test_token_2_name,
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_2.__dict__ = token_2_attr

        mock_IbetStraightBondContract_get.side_effect = [token_2]

        # Request target API
        resp = await async_client.get(self.api_url, params={"offset": 1, "limit": 1})

        # assertion
        assert resp.status_code == 200

        assert resp.json() == {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "scheduled_events": [
                {
                    "scheduled_event_id": event_id_2,
                    "token_address": self.test_token_2_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "scheduled_datetime": (
                        pytz.timezone("UTC")
                        .localize(scheduled_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "event_type": ScheduledEventType.UPDATE,
                    "status": 0,
                    "data": update_data,
                    "created": (
                        pytz.timezone("UTC")
                        .localize(create_datetime_2)
                        .astimezone(self.local_tz)
                        .isoformat()
                    ),
                    "is_soft_deleted": False,
                    "token_attributes": token_2_attr,
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Header(issuer_address): Invalid address format
    # -> 422: RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.api_url,
            headers={"issuer-address": "invalid_issuer_address"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "msg": "issuer-address is not a valid address",
                    "loc": ["header", "issuer-address"],
                    "input": "invalid_issuer_address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2_1>
    # Invalid token_type
    # -> 422: RequestValidationError
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.api_url, params={"token_type": "invalid_token_type"}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["query", "token_type"],
                    "msg": "Input should be 'IbetStraightBond' or 'IbetShare'",
                    "input": "invalid_token_type",
                    "ctx": {"expected": "'IbetStraightBond' or 'IbetShare'"},
                }
            ],
        }

    # <Error_2_2>
    # Invalid token_address
    # -> 422: RequestValidationError
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.api_url, params={"token_address": "invalid_token_address"}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["query", "token_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_token_address",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_2_3>
    # Invalid status
    # -> 422: RequestValidationError
    @pytest.mark.asyncio
    async def test_error_2_3(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(self.api_url, params={"status": 3})

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["query", "status"],
                    "msg": "Input should be 0, 1 or 2",
                    "input": "3",
                    "ctx": {"expected": "0, 1 or 2"},
                }
            ],
        }

    # <Error_2_4>
    # Invalid sort item
    # -> 422: RequestValidationError
    @pytest.mark.asyncio
    async def test_error_2_4(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.api_url, params={"sort_item": "invalid_sort_item", "sort_order": 2}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'created', 'scheduled_datetime' or 'token_address'",
                    "input": "invalid_sort_item",
                    "ctx": {
                        "expected": "'created', 'scheduled_datetime' or 'token_address'"
                    },
                },
                {
                    "type": "enum",
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "input": "2",
                    "ctx": {"expected": "0 or 1"},
                },
            ],
        }
