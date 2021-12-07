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

from config import TZ
from app.model.db import (
    Account,
    TokenType,
    ScheduledEvents,
    ScheduledEventType
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressScheduledEventsScheduledEventIdDELETE:
    # target API endpoint
    base_url = "/share/tokens/{}/scheduled_events/{}"
    local_tz = timezone(TZ)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        datetime_now_utc = datetime.utcnow()
        datetime_now_str = timezone("UTC").localize(datetime_now_utc).astimezone(self.local_tz).isoformat()
        data = {
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
            "memo": "memo_test1"
        }
        event_id = str(uuid.uuid4())

        token_event = ScheduledEvents()
        token_event.event_id = event_id
        token_event.issuer_address = _issuer_address
        token_event.token_address = _token_address
        token_event.token_type = TokenType.IBET_SHARE
        token_event.event_type = ScheduledEventType.UPDATE
        token_event.scheduled_datetime = datetime_now_utc
        token_event.status = 0
        token_event.data = data
        token_event.created = datetime_now_utc
        db.add(token_event)

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, event_id),
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "scheduled_event_id": event_id,
            "token_address": _token_address,
            "token_type": TokenType.IBET_SHARE,
            "scheduled_datetime": datetime_now_str,
            "event_type": ScheduledEventType.UPDATE,
            "status": 0,
            "data": data,
            "created": datetime_now_str
        }
        token_event = db.query(ScheduledEvents).filter(ScheduledEvents.event_id == event_id).first()
        assert token_event is None

    #########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # invalid issuer_address, password not encrypted
    def test_error_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, "test_event_id"),
            headers={
                "issuer-address": _issuer_address[:-1],  # too short
                "eoa-password": "password"  # not encrypted
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {"code": 1, "title": "RequestValidationError"}
        assert resp.json()["detail"] == [
            {
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }, {
                "loc": ["header", "eoa-password"],
                "msg": "eoa-password is not a Base64-encoded encrypted data",
                "type": "value_error"
            }
        ]

    # <Error_2>
    # AuthorizationError
    # issuer_address does not exists
    def test_error_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, "test_event_id"),
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json()["meta"] == {"code": 1, "title": "AuthorizationError"}
        assert resp.json()["detail"] == "issuer does not exist, or password mismatch"

    # <Error_3>
    # AuthorizationError
    # password mismatch
    def test_error_3(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, "test_event_id"),
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("mismatch_password")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json()["meta"] == {"code": 1, "title": "AuthorizationError"}
        assert resp.json()["detail"] == "issuer does not exist, or password mismatch"

    # <Error_4>
    # NotFound
    # event not found
    def test_error_4(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        resp = client.delete(
            self.base_url.format(_token_address, "test_event_id"),
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {"code": 1, "title": "NotFound"}
        assert resp.json()["detail"] == "event not found"
