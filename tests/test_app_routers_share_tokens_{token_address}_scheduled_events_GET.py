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
from datetime import (
    datetime,
    timedelta
)
from pytz import timezone

from config import TZ
from app.model.db import (
    TokenType,
    ScheduledEvents,
    ScheduledEventType
)
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressScheduledEventsGET:
    # target API endpoint
    base_url = "/share/tokens/{}/scheduled_events"
    tz_local = timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # ScheduledEventType : UPDATE, Set issuer_address.
    def test_normal_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_now_utc = datetime.utcnow()
        datetime_now_str = self.tz_local.localize(datetime_now_utc).isoformat()
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
            "offering_status": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest"
        }

        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        assumed_resp = [
            {
                "scheduled_event_id": 1,
                "token_address": _token_address,
                "token_type": TokenType.IBET_SHARE,
                "scheduled_datetime": datetime_now_str,
                "event_type": ScheduledEventType.UPDATE,
                "status": 0,
                "data": update_data
            }
        ]

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == assumed_resp

    # <Normal_2>
    # ScheduledEventType : UPDATE, Not set issuer_address.
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
        datetime_list.append(datetime_utc)
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
            "offering_status": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest"
        }

        for _datetime in datetime_list:
            token_event = ScheduledEvents()
            token_event.issuer_address = _issuer_address
            token_event.token_address = _token_address
            token_event.token_type = TokenType.IBET_SHARE
            token_event.event_type = ScheduledEventType.UPDATE
            token_event.scheduled_datetime = _datetime
            token_event.status = 0
            token_event.data = update_data
            db.add(token_event)

        assumed_resp = [
            {
                "scheduled_event_id": 1,
                "token_address": _token_address,
                "token_type": TokenType.IBET_SHARE,
                "scheduled_datetime": self.tz_local.localize(datetime_list[0]).isoformat(),
                "event_type": ScheduledEventType.UPDATE,
                "status": 0,
                "data": update_data
            }, {
                "scheduled_event_id": 2,
                "token_address": _token_address,
                "token_type": TokenType.IBET_SHARE,
                "scheduled_datetime": self.tz_local.localize(datetime_list[1]).isoformat(),
                "event_type": ScheduledEventType.UPDATE,
                "status": 0,
                "data": update_data
            }
        ]

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == assumed_resp

    # <Normal_3>
    # token event not found
    def test_normal_3(self, client, db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == []

    ###########################################################################
    # Error Case
    ###########################################################################
