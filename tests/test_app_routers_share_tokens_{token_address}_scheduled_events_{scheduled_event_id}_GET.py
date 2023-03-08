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

from pytz import timezone

from app.model.db import ScheduledEvents, ScheduledEventType, TokenType
from config import TZ
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressScheduledEventsScheduledEventIdGET:
    # target API endpoint
    base_url = "/share/tokens/{}/scheduled_events/{}"
    local_tz = timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # With issuer_address(header)
    def test_normal_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_now_utc = datetime.utcnow()
        datetime_now_str = (
            timezone("UTC")
            .localize(datetime_now_utc)
            .astimezone(self.local_tz)
            .isoformat()
        )
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
        event_id = str(uuid.uuid4())

        token_event = ScheduledEvents()
        token_event.event_id = event_id
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_utc
        token_event.status = 0
        token_event.data = update_data
        token_event.created = datetime_now_utc
        db.add(token_event)

        # request target API
        resp = client.get(
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
            "token_type": TokenType.IBET_SHARE.value,
            "scheduled_datetime": datetime_now_str,
            "event_type": ScheduledEventType.UPDATE.value,
            "status": 0,
            "data": update_data,
            "created": datetime_now_str,
        }

    # <Normal_2>
    # Without issuer_address(header)
    def test_normal_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_now_utc = datetime.utcnow()
        datetime_now_str = (
            timezone("UTC")
            .localize(datetime_now_utc)
            .astimezone(self.local_tz)
            .isoformat()
        )
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
        event_id = str(uuid.uuid4())

        token_event = ScheduledEvents()
        token_event.event_id = event_id
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_utc
        token_event.status = 0
        token_event.data = update_data
        token_event.created = datetime_now_utc
        db.add(token_event)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, event_id),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "scheduled_event_id": event_id,
            "token_address": _token_address,
            "token_type": TokenType.IBET_SHARE.value,
            "scheduled_datetime": datetime_now_str,
            "event_type": ScheduledEventType.UPDATE.value,
            "status": 0,
            "data": update_data,
            "created": datetime_now_str,
        }

    #########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Event not found
    def test_error_1(self, client, db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.get(
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
