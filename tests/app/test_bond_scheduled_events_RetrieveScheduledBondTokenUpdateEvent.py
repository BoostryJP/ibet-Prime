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
from datetime import UTC, datetime

import pytest
import pytz

from app.model.db import ScheduledEvents, ScheduledEventType, TokenType
from config import TZ
from tests.account_config import config_eth_account


class TestRetrieveScheduledBondTokenUpdateEvent:
    # target API endpoint
    base_url = "/bond/tokens/{}/scheduled_events/{}"
    local_tz = pytz.timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # issuer address is specified
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_now_utc = datetime.now(UTC).replace(tzinfo=None)
        datetime_now_str = (
            pytz.timezone("UTC")
            .localize(datetime_now_utc)
            .astimezone(self.local_tz)
            .isoformat()
        )
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
        event_id = str(uuid.uuid4())

        token_event = ScheduledEvents()
        token_event.event_id = event_id
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc
        token_event.status = 0
        token_event.data = update_data
        token_event.created = datetime_now_utc
        async_db.add(token_event)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address, event_id),
            headers={
                "issuer-address": _issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "scheduled_event_id": event_id,
            "token_address": _token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "scheduled_datetime": datetime_now_str,
            "event_type": ScheduledEventType.UPDATE,
            "status": 0,
            "data": update_data,
            "created": datetime_now_str,
        }

    # <Normal_2>
    # issuer address is not specified
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_now_utc = datetime.now(UTC).replace(tzinfo=None)
        datetime_now_str = (
            pytz.timezone("UTC")
            .localize(datetime_now_utc)
            .astimezone(self.local_tz)
            .isoformat()
        )
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
        event_id = str(uuid.uuid4())

        token_event = ScheduledEvents()
        token_event.event_id = event_id
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc
        token_event.status = 0
        token_event.data = update_data
        token_event.created = datetime_now_utc
        async_db.add(token_event)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address, event_id),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "scheduled_event_id": event_id,
            "token_address": _token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "scheduled_datetime": datetime_now_str,
            "event_type": ScheduledEventType.UPDATE,
            "status": 0,
            "data": update_data,
            "created": datetime_now_str,
        }

    #########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Event not found
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address, "test_event_id"),
            headers={
                "issuer-address": _issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "event not found",
        }
