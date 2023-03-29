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
from datetime import datetime, timedelta

from pytz import timezone

from app.model.db import ScheduledEvents, ScheduledEventType, TokenType
from config import TZ
from tests.account_config import config_eth_account


class TestAppRoutersBondTokensTokenAddressScheduledEventsGET:
    # target API endpoint
    base_url = "/bond/tokens/{}/scheduled_events"
    local_tz = timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Specify issuer address
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
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        token_event.event_type = ScheduledEventType.UPDATE.value
        token_event.scheduled_datetime = datetime_now_utc
        token_event.status = 0
        token_event.data = update_data
        token_event.created = datetime_now_utc
        db.add(token_event)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "scheduled_event_id": event_id,
                "token_address": _token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "scheduled_datetime": datetime_now_str,
                "event_type": ScheduledEventType.UPDATE.value,
                "status": 0,
                "data": update_data,
                "created": datetime_now_str,
            }
        ]

    # <Normal_2>
    # No issuer address is specified
    # Multiple records
    def test_normal_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_list = []
        datetime_utc = datetime.utcnow() + timedelta(hours=1)
        datetime_list.append(datetime_utc)
        datetime_utc = datetime.utcnow()
        datetime_list.append(datetime_utc.replace(tzinfo=None))

        uuid_list = [str(uuid.uuid4()), str(uuid.uuid4())]

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

        for i, _datetime in enumerate(datetime_list):
            token_event = ScheduledEvents()
            token_event.event_id = uuid_list[i]
            token_event.issuer_address = _issuer_address
            token_event.token_address = _token_address
            token_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
            token_event.event_type = ScheduledEventType.UPDATE.value
            token_event.scheduled_datetime = _datetime
            token_event.status = 0
            token_event.data = update_data
            token_event.created = _datetime
            db.add(token_event)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "scheduled_event_id": uuid_list[0],
                "token_address": _token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "scheduled_datetime": timezone("UTC")
                .localize(datetime_list[0])
                .astimezone(self.local_tz)
                .isoformat(),
                "event_type": ScheduledEventType.UPDATE.value,
                "status": 0,
                "data": update_data,
                "created": timezone("UTC")
                .localize(datetime_list[0])
                .astimezone(self.local_tz)
                .isoformat(),
            },
            {
                "scheduled_event_id": uuid_list[1],
                "token_address": _token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "scheduled_datetime": timezone("UTC")
                .localize(datetime_list[1])
                .astimezone(self.local_tz)
                .isoformat(),
                "event_type": ScheduledEventType.UPDATE.value,
                "status": 0,
                "data": update_data,
                "created": timezone("UTC")
                .localize(datetime_list[1])
                .astimezone(self.local_tz)
                .isoformat(),
            },
        ]

    # <Normal_3>
    # No data
    def test_normal_3(self, client, db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == []

    #########################################################################
    # Error Case
    ###########################################################################
