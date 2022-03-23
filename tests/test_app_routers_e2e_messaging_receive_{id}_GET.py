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
import json
from datetime import datetime

from app.model.db import (
    IDXE2EMessaging,
    E2EMessagingAccount
)


class TestAppRoutersE2EMessagingReceiveIdGET:
    # target API endpoint
    base_url = "/e2e_messaging/receive/{id}"

    def insert_data(self, db, e2e_messaging):
        _e2e_messaging = IDXE2EMessaging()
        if "id" in e2e_messaging:
            _e2e_messaging.id = e2e_messaging["id"]
        _e2e_messaging.from_address = e2e_messaging["from_address"]
        _e2e_messaging.to_address = e2e_messaging["to_address"]
        _e2e_messaging.type = e2e_messaging["type"]
        _e2e_messaging.message = e2e_messaging["message"]
        _e2e_messaging.send_timestamp = e2e_messaging["send_timestamp"]
        db.add(_e2e_messaging)

        _account = db.query(E2EMessagingAccount). \
            filter(E2EMessagingAccount.account_address == e2e_messaging["to_address"]). \
            first()
        if _account is None:
            _account = E2EMessagingAccount()
            _account.account_address = e2e_messaging["to_address"]
            db.add(_account)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # string message
    def test_normal_1_1(self, client, db):
        # prepare data
        e2e_messaging = {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "message_test1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url.format(id=10),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "message_test1",
            "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
        }

    # <Normal_1_2>
    # json-string message
    def test_normal_1_2(self, client, db):
        # prepare data
        e2e_messaging = {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": json.dumps({"aaa": 1, "bbb": True, "ccc": "hoge"}),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url.format(id=10),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": {
                "aaa": 1,
                "bbb": True,
                "ccc": "hoge"
            },
            "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
        }

    # <Normal_1_3>
    # listed string message
    def test_normal_1_3(self, client, db):
        # prepare data
        e2e_messaging = {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": json.dumps(["a", 1, True]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url.format(id=10),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": ["a", 1, True],
            "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
        }

    # <Normal_1_4>
    # listed json string message
    def test_normal_1_4(self, client, db):
        # prepare data
        e2e_messaging = {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": json.dumps([{"aaa": 1, "bbb": True, "ccc": "hoge"}, {"aaa": 2, "bbb": False, "ccc": "fuga"}]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url.format(id=10),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": [
                {
                    "aaa": 1,
                    "bbb": True,
                    "ccc": "hoge"
                },
                {
                    "aaa": 2,
                    "bbb": False,
                    "ccc": "fuga"
                }
            ],
            "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    # Header
    def test_error_1(self, client, db):

        # request target API
        resp = client.get(
            self.base_url.format(id=1),
            headers={
                "account-address": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "account-address"],
                    "msg": "account-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2_1>
    # Not Found Error
    # no data
    def test_error_2_1(self, client, db):
        # prepare data
        e2e_messaging = {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "test_message1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target API
        resp = client.get(
            self.base_url.format(id=1),  # other id
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "e2e messaging not found",
        }

    # <Error_2_2>
    # Not Found Error
    # send data
    def test_error_2_2(self, client, db):
        # prepare data
        e2e_messaging = {
            "id": 10,
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",  # not registry account address
            "type": "type_test1",
            "message": "test_message1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        _e2e_messaging = IDXE2EMessaging()
        _e2e_messaging.id = e2e_messaging["id"]
        _e2e_messaging.from_address = e2e_messaging["from_address"]
        _e2e_messaging.to_address = e2e_messaging["to_address"]
        _e2e_messaging.type = e2e_messaging["type"]
        _e2e_messaging.message = e2e_messaging["message"]
        _e2e_messaging.send_timestamp = e2e_messaging["send_timestamp"]
        db.add(_e2e_messaging)

        # request target API
        resp = client.get(
            self.base_url.format(id=10),
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "e2e messaging not found",
        }
