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
    timezone,
    timedelta
)

from pytz import timezone as tz

from app.model.db import (
    TokenType,
    ScheduledEvents,
    ScheduledEventType
)
from tests.account_config import config_eth_account


class TestAppRoutersBondTokensTokenAddressScheduledEventsScheduledEventIdDELETE:
    # target API endpoint
    base_url = "/bond/tokens/{}/scheduled_events/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Timezone of input data is UTC, ScheduledEventType : UPDATE, Set issuer_address.
    def test_normal_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
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
            "initial_offering_status": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest"
        }

        token_event = ScheduledEvents()
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_STRAIGHT_BOND
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_str
        token_event.status = 0
        token_event.data = update_data
        db.add(token_event)

        assumed_resp = {
            "scheduled_event_id": 1,
            "token_address": _token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "scheduled_datetime": datetime_now_str,
            "event_type": ScheduledEventType.UPDATE,
            "status": 0,
            "data": update_data
        }

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, 1),
            headers={
                "issuer-address": _issuer_address,
            }
        )
        # request get API
        resp_get = client.get(
            self.base_url.format(_token_address, 1),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == assumed_resp
        assert resp_get.status_code == 404
        assert resp_get.json() == {
            "meta": {
                "code": 1, "title": "NotFound"
            },
            "detail": "scheduled event scheduled_event_id not found"
        }

    # <Normal_2>
    # Timezone of input data is JST, ScheduledEventType : UPDATE, Not set issuer_address.
    def test_normal_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        datetime_str_list = []
        datetime_jst = datetime.now(tz("Asia/Tokyo")) + timedelta(hours=1)
        datetime_str_list.append(datetime_jst.astimezone(timezone.utc).replace(tzinfo=None))
        datetime_jst = datetime.now(tz("Asia/Tokyo"))
        datetime_str_list.append(datetime_jst.astimezone(timezone.utc).replace(tzinfo=None))
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
            "initial_offering_status": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest"
        }

        for datetime_str in datetime_str_list:
            token_event = ScheduledEvents()
            token_event.issuer_address = _issuer_address
            token_event.token_address = _token_address
            token_event.token_type = TokenType.IBET_STRAIGHT_BOND
            token_event.event_type = ScheduledEventType.UPDATE
            token_event.scheduled_datetime = datetime_str.isoformat()
            token_event.status = 0
            token_event.data = update_data
            db.add(token_event)

        assumed_resp = {
            "scheduled_event_id": 2,
            "token_address": _token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "scheduled_datetime": datetime_str_list[1].isoformat(),
            "event_type": ScheduledEventType.UPDATE,
            "status": 0,
            "data": update_data
        }

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, 2),
        )
        # request get API
        resp_get_1 = client.get(
            self.base_url.format(_token_address, 1),
        )
        # request get API
        resp_get_2 = client.get(
            self.base_url.format(_token_address, 2),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == assumed_resp
        assert resp_get_1.status_code == 200
        assert resp_get_2.status_code == 404
        assert resp_get_2.json() == {
            "meta": {
                "code": 1, "title": "NotFound"
            },
            "detail": "scheduled event scheduled_event_id not found"
        }

    #########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # RequestValidationError
    # invalid scheduled_event_id
    def test_error_1(self, client, db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, "non-numeric-type"),
            headers={
                "issuer-address": _issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {"code": 1, "title": "RequestValidationError"}
        assert resp.json()["detail"] == [
            {
                "loc": ["path", "scheduled_event_id"],
                "msg": "value is not a valid integer",
                "type": "type_error.integer"
            }
        ]

    # <Error_2>
    # scheduled event scheduled_event_id not found
    def test_error_2(self, client, db):
        test_account = config_eth_account("user2")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, 1),
            headers={
                "issuer-address": _issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1, "title": "NotFound"
            },
            "detail": "scheduled event scheduled_event_id not found"
        }
