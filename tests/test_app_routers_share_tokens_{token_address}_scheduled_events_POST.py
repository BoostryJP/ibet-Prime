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
from config import SCHEDULED_EVENTS_INTERVAL
from app.model.db import (
    Account,
    Token,
    TokenType,
    ScheduledEvents,
    ScheduledEventType
)
from app.model.utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressScheduledEventPOST:
    # target API endpoint
    base_url = "/share/tokens/{}/scheduled_event"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1> item update : None
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
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # test data
        _after_an_hour_time = datetime.now() + timedelta(hours=1)
        _after_an_hour = _after_an_hour_time.strftime("%Y-%m-%d %H:%M")
        tx_data = {
        }
        # request target API
        req_param = {
            "start_time": _after_an_hour,
            "event_type": "Update",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()

        # assertion
        assert resp.status_code == 200
        assert _scheduled_event.token_type == TokenType.IBET_SHARE
        assert _scheduled_event.event_type == ScheduledEventType.UPDATE
        assert _scheduled_event.status == 0

    # <Normal_2> All item update
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
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # test data
        _after_an_hour_time = datetime.now() + timedelta(hours=1)
        _after_an_hour = _after_an_hour_time.strftime("%Y-%m-%d %H:%M")
        tx_data = {
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
        # request target API
        req_param = {
            "start_time": _after_an_hour,
            "event_type": "Update",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()

        # assertion
        assert resp.status_code == 200
        assert _scheduled_event.token_type == TokenType.IBET_SHARE
        assert _scheduled_event.event_type == ScheduledEventType.UPDATE
        assert _scheduled_event.status == 0
        assert _scheduled_event.data == tx_data

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: account_address is short
    def test_error_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # test data
        _after_an_hour_time = datetime.now() + timedelta(hours=1)
        _after_an_hour = _after_an_hour_time.strftime("%Y-%m-%d %H:%M")
        tx_data = {
        }
        # request target API
        req_param = {
            "start_time": _after_an_hour,
            "event_type": "Update",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address[:-1],  # too short
                "eoa-password": "password"  # not encrypted
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {'code': 1, 'title': 'RequestValidationError'}
        assert resp.json()["detail"] == [
            {
                "loc": ['header', 'issuer-address'],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }, {
                "loc": ['header', 'eoa-password'],
                "msg": "eoa-password is not a Base64-encoded encrypted data",
                "type": "value_error"
            }
        ]

    # <Error_2>
    # AuthorizationError: account_address does not exists
    def test_error_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # test data
        _after_an_hour_time = datetime.now() + timedelta(hours=1)
        _after_an_hour = _after_an_hour_time.strftime("%Y-%m-%d %H:%M")
        tx_data = {
        }
        # request target API
        req_param = {
            "start_time": _after_an_hour,
            "event_type": "Update",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        # assertion
        assert resp.status_code == 401
        assert resp.json()["meta"] == {'code': 1, 'title': 'AuthorizationError'}
        assert resp.json()["detail"] == "issuer does not exist"

    # <Error_3>
    # AuthorizationError: password mismatch
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
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # test data
        _after_an_hour_time = datetime.now() + timedelta(hours=1)
        _after_an_hour = _after_an_hour_time.strftime("%Y-%m-%d %H:%M")
        tx_data = {
        }
        # request target API
        req_param = {
            "start_time": _after_an_hour,
            "event_type": "Update",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("mismatch-password")
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()

        # assertion
        assert resp.status_code == 401
        assert resp.json()["meta"] == {'code': 1, 'title': 'AuthorizationError'}
        assert resp.json()["detail"] == "password mismatch"

    # <Error_4>
    # NotFound: token not found
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
        _after_an_hour_time = datetime.now() + timedelta(hours=1)
        _after_an_hour = _after_an_hour_time.strftime("%Y-%m-%d %H:%M")
        tx_data = {
        }
        # request target API
        req_param = {
            "start_time": _after_an_hour,
            "event_type": "Update",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()

        # assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {'code': 1, 'title': 'NotFound'}
        assert resp.json()["detail"] == "token not found"

    # <Error_5>
    # RequestValidationError: event_data
    def test_error_5(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "token_address_test"

        # test data
        tx_data = {
            "dividends": "must be integer, but string",
        }
        # request target API
        req_param = {
            "start_time": "this is not time format",
            "event_type": "NOT-EXIST-EVENT",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()
        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {'code': 1, 'title': 'RequestValidationError'}
        assert resp.json()["detail"] == [
            {
                "loc": ['body', 'start_time'],
                "msg": "time data 'this is not time format' does not match format '%Y-%m-%d %H:%M'",
                "type": "value_error"
            }, {
                "loc": ['body', 'event_type'],
                "msg": "event_type is not supported",
                "type": "value_error"
            }, {
                "loc": ['body', 'data', 'dividends'],
                "msg": "value is not a valid float",
                "type": "type_error.float"
            }
        ]

    # <Error_6>
    # RequestValidationError: event_data.start_time is past time
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
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # test data
        _after_an_hour_time = datetime.now() + timedelta(hours=-1)
        _after_an_hour = _after_an_hour_time.strftime("%Y-%m-%d %H:%M")
        tx_data = {
        }
        # request target API
        req_param = {
            "start_time": _after_an_hour,
            "event_type": "Update",
            "data": tx_data
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )
        _scheduled_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.issuer_address == _issuer_address). \
            filter(ScheduledEvents.token_address == _token_address). \
            first()

        # assertion
        assert resp.status_code == 422
        assert resp.json()["meta"] == {'code': 1, 'title': 'RequestValidationError'}
        assert resp.json()["detail"] == [
            {
                "loc": ['body', 'start_time'],
                "msg": f"start_time have to set {2 * SCHEDULED_EVENTS_INTERVAL} sec later.",
                "type": "value_error"
            }
        ]
