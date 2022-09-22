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
    timezone
)

from pytz import timezone as tz

from app.model.db import (
    Account,
    Token,
    TokenType,
    ScheduledEvents,
    ScheduledEventType
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressScheduledEventsPOST:
    # target API endpoint
    base_url = "/share/tokens/{}/scheduled_events"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Timezone of input data is UTC
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

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # test data
        datetime_now_utc = datetime.now(timezone.utc)  # utc
        datetime_now_str = datetime_now_utc.isoformat()
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
            "transfer_approval_required": False,
            "principal_value": 900,
            "is_canceled": False,
            "memo": "memo_test1"
        }

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": update_data
        }
        resp_1 = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert resp_1.status_code == 200
        assert resp_1.json() == {"scheduled_event_id": _scheduled_event.event_id}
        assert _scheduled_event.token_type == TokenType.IBET_SHARE.value
        assert _scheduled_event.scheduled_datetime == datetime_now_utc.replace(tzinfo=None)
        assert _scheduled_event.event_type == ScheduledEventType.UPDATE.value
        assert _scheduled_event.status == 0
        assert _scheduled_event.data == update_data

    # <Normal_2>
    # Timezone of input data is JST
    def test_normal_2(self, client, db):
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

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # test data
        datetime_now_jst = datetime.now(tz("Asia/Tokyo"))  # jst
        datetime_now_str = datetime_now_jst.isoformat()
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
            "transfer_approval_required": True,
            "principal_value": 900,
            "is_canceled": False,
            "memo": "memo_test1"
        }

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": update_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        assert resp.status_code == 200
        assert resp.json() == {"scheduled_event_id": _scheduled_event.event_id}
        assert _scheduled_event.token_type == TokenType.IBET_SHARE.value
        assert _scheduled_event.scheduled_datetime == datetime_now_jst.astimezone(timezone.utc).replace(tzinfo=None)
        assert _scheduled_event.event_type == ScheduledEventType.UPDATE.value
        assert _scheduled_event.status == 0
        assert _scheduled_event.data == update_data

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # invalid issuer_address
    def test_error_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # test data
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {}

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": update_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
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

        # test data
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {}

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": update_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
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

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # test data
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {}

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": update_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("mismatch-password")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json()["meta"] == {"code": 1, "title": "AuthorizationError"}
        assert resp.json()["detail"] == "issuer does not exist, or password mismatch"

    # <Error_4>
    # NotFound
    # token not found
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

        # test data
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {}

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": update_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {"code": 1, "title": "NotFound"}
        assert resp.json()["detail"] == "token not found"
        
    # <Error_5>
    # RequestValidationError
    # event_data
    def test_error_5(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"
        
        # request target API
        req_param = {
            "scheduled_datetime": "this is not time format",
            "event_type": "aUpdateb",
            "data": {
                "dividends": "must be integer, but string",
            }
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {"code": 1, "title": "RequestValidationError"}
        assert resp.json()["detail"] == [
            {
                "loc": ["body", "scheduled_datetime"],
                "msg": "invalid datetime format",
                "type": "value_error.datetime"
            }, {
                "ctx": {"enum_values": ["Update"]},
                "loc": ["body", "event_type"],
                "msg": "value is not a valid enumeration member; permitted: 'Update'",
                "type": "type_error.enum"
            }, {
                "loc": ["body", "data", "dividends"],
                "msg": "value is not a valid float",
                "type": "type_error.float"
            }
        ]

    # <Error_6>
    # InvalidParameterError
    # processing token
    def test_error_6(self, client, db):
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

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        db.add(token)

        # test data
        datetime_now_utc = datetime.now(timezone.utc)
        datetime_now_str = datetime_now_utc.isoformat()
        update_data = {}

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": update_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "this token is temporarily unavailable"
        }
