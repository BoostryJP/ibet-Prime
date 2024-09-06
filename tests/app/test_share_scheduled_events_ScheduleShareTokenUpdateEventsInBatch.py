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

from datetime import UTC, datetime, timedelta
from unittest.mock import ANY

import pytest
from pytz import timezone as tz
from sqlalchemy import and_, select

from app.model.db import (
    Account,
    ScheduledEvents,
    ScheduledEventType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestScheduleShareTokenUpdateEventsBatch:
    # target API endpoint
    base_url = "/share/tokens/{}/scheduled_events/batch"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Multiple Records
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
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        datetime_1 = datetime.now(tz("Asia/Tokyo"))
        datetime_2 = datetime.now(tz("Asia/Tokyo")) + timedelta(hours=1)
        datetime_1_str = datetime_1.isoformat()
        datetime_2_str = datetime_2.isoformat()

        req_param = [
            {
                "scheduled_datetime": datetime_1_str,
                "event_type": "Update",
                "data": {"transferable": False},
            },
            {
                "scheduled_datetime": datetime_2_str,
                "event_type": "Update",
                "data": {"transferable": True},
            },
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        _scheduled_event = db.scalars(
            select(ScheduledEvents).where(
                and_(
                    ScheduledEvents.issuer_address == _issuer_address,
                    ScheduledEvents.token_address == _token_address,
                )
            )
        ).all()
        assert len(_scheduled_event) == 2

        assert resp.status_code == 200
        assert resp.json() == {
            "scheduled_event_id_list": [
                _scheduled_event[0].event_id,
                _scheduled_event[1].event_id,
            ]
        }

        assert _scheduled_event[0].token_type == TokenType.IBET_SHARE.value
        assert _scheduled_event[0].scheduled_datetime == datetime_1.astimezone(
            UTC
        ).replace(tzinfo=None)
        assert _scheduled_event[0].event_type == ScheduledEventType.UPDATE.value
        assert _scheduled_event[0].status == 0
        assert _scheduled_event[0].data == {
            "cancellation_date": None,
            "dividend_record_date": None,
            "dividend_payment_date": None,
            "dividends": None,
            "tradable_exchange_contract_address": None,
            "personal_info_contract_address": None,
            "require_personal_info_registered": None,
            "transferable": False,
            "status": None,
            "is_offering": None,
            "contact_information": None,
            "privacy_policy": None,
            "transfer_approval_required": None,
            "principal_value": None,
            "is_canceled": None,
            "memo": None,
        }

        assert _scheduled_event[1].token_type == TokenType.IBET_SHARE.value
        assert _scheduled_event[1].scheduled_datetime == datetime_2.astimezone(
            UTC
        ).replace(tzinfo=None)
        assert _scheduled_event[1].event_type == ScheduledEventType.UPDATE.value
        assert _scheduled_event[1].status == 0
        assert _scheduled_event[1].data == {
            "cancellation_date": None,
            "dividend_record_date": None,
            "dividend_payment_date": None,
            "dividends": None,
            "tradable_exchange_contract_address": None,
            "personal_info_contract_address": None,
            "require_personal_info_registered": None,
            "transferable": True,
            "status": None,
            "is_offering": None,
            "contact_information": None,
            "privacy_policy": None,
            "transfer_approval_required": None,
            "principal_value": None,
            "is_canceled": None,
            "memo": None,
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError
    # - Empty list
    def test_error_1_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # test data
        datetime_now_utc = datetime.now(UTC)
        datetime_now_str = datetime_now_utc.isoformat()

        # request target API
        req_param = {
            "scheduled_datetime": datetime_now_str,
            "event_type": "Update",
            "data": [],
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "list_type",
                    "loc": ["body"],
                    "msg": "Input should be a valid list",
                    "input": {
                        "scheduled_datetime": ANY,
                        "event_type": "Update",
                        "data": [],
                    },
                }
            ],
        }

    # <Error_1_2>
    # RequestValidationError
    # - Invalid parameters
    def test_error_1_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        req_param = [
            {
                "scheduled_datetime": "this is not datetime format",
                "event_type": "aUpdateb",
                "data": {
                    "principal_value": "must be integer, but string",
                },
            }
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {"code": 1, "title": "RequestValidationError"}
        assert resp.json()["detail"] == [
            {
                "type": "datetime_from_date_parsing",
                "loc": ["body", 0, "scheduled_datetime"],
                "msg": "Input should be a valid datetime or date, invalid character in year",
                "input": "this is not datetime format",
                "ctx": {"error": "invalid character in year"},
            },
            {
                "type": "enum",
                "loc": ["body", 0, "event_type"],
                "msg": "Input should be 'Update'",
                "input": "aUpdateb",
                "ctx": {"expected": "'Update'"},
            },
            {
                "type": "int_parsing",
                "loc": ["body", 0, "data", "principal_value"],
                "msg": "Input should be a valid integer, unable to parse string as an integer",
                "input": "must be integer, but string",
            },
        ]

    # <Error_1_3>
    # RequestValidationError
    # - validate_headers
    def test_error_1_3(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        datetime_1 = datetime.now(tz("Asia/Tokyo"))
        datetime_1_str = datetime_1.isoformat()
        req_param = [
            {
                "scheduled_datetime": datetime_1_str,
                "event_type": "Update",
                "data": {"transferable": False},
            },
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address[:-1],  # too short
                "eoa-password": "password",  # not encrypted
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {"code": 1, "title": "RequestValidationError"}
        assert resp.json()["detail"] == [
            {
                "input": _issuer_address[:-1],
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error",
            },
            {
                "input": "password",
                "loc": ["header", "eoa-password"],
                "msg": "eoa-password is not a Base64-encoded encrypted data",
                "type": "value_error",
            },
        ]

    # <Error_2_1>
    # AuthorizationError
    # - issuer_address does not exist
    def test_error_2_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # request target API
        datetime_1 = datetime.now(tz("Asia/Tokyo"))
        datetime_1_str = datetime_1.isoformat()
        req_param = [
            {
                "scheduled_datetime": datetime_1_str,
                "event_type": "Update",
                "data": {"transferable": False},
            },
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json()["meta"] == {"code": 1, "title": "AuthorizationError"}
        assert resp.json()["detail"] == "issuer does not exist, or password mismatch"

    # <Error_2_2>
    # AuthorizationError
    # - password mismatch
    def test_error_2_2(self, client, db):
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
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        datetime_1 = datetime.now(tz("Asia/Tokyo"))
        datetime_1_str = datetime_1.isoformat()
        req_param = [
            {
                "scheduled_datetime": datetime_1_str,
                "event_type": "Update",
                "data": {"transferable": False},
            },
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("mismatch-password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json()["meta"] == {"code": 1, "title": "AuthorizationError"}
        assert resp.json()["detail"] == "issuer does not exist, or password mismatch"

    # <Error_3>
    # 404: NotFound
    # - Token not found
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

        db.commit()

        # request target API
        datetime_1 = datetime.now(tz("Asia/Tokyo"))
        datetime_1_str = datetime_1.isoformat()
        req_param = [
            {
                "scheduled_datetime": datetime_1_str,
                "event_type": "Update",
                "data": {"transferable": False},
            },
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {"code": 1, "title": "NotFound"}
        assert resp.json()["detail"] == "token not found"

    # <Error_4>
    # InvalidParameterError
    # - Processing token
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

        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        datetime_1 = datetime.now(tz("Asia/Tokyo"))
        datetime_1_str = datetime_1.isoformat()
        req_param = [
            {
                "scheduled_datetime": datetime_1_str,
                "event_type": "Update",
                "data": {"transferable": False},
            },
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # <Error_5>
    # OperationNotSupportedVersionError: v24.6
    @pytest.mark.parametrize(
        "update_data",
        [
            {
                "require_personal_info_registered": True,
            },
        ],
    )
    def test_error_5(self, client, db, update_data):
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
        token.token_status = 1
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # request target API
        datetime_1 = datetime.now(tz("Asia/Tokyo"))
        datetime_1_str = datetime_1.isoformat()
        req_param = [
            {
                "scheduled_datetime": datetime_1_str,
                "event_type": "Update",
                "data": update_data,
            },
        ]
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 6, "title": "OperationNotSupportedVersionError"},
            "detail": "the operation is not supported in 23_12",
        }
