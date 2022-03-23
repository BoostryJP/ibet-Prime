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


class TestAppRoutersE2EMessagingReceiveGET:
    # target API endpoint
    base_url = "/e2e_messaging/receive"


    def insert_data(self, db, e2e_messaging):
        _e2e_messaging = IDXE2EMessaging()
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

    # <Normal_1>
    # 0 record(not E2E account)
    def test_normal_1(self, client, db):
        # prepare data
        _e2e_messaging = IDXE2EMessaging()
        _e2e_messaging.from_address = "0x1234567890123456789012345678900000000010"
        _e2e_messaging.to_address = "0x1234567890123456789012345678900000000000"  # not registry account address
        _e2e_messaging.type = "dummy_type"
        _e2e_messaging.message = "dummy message"
        _e2e_messaging.send_timestamp = datetime.utcnow()
        db.add(_e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0
            },
            "e2e_messages": []
        }

    # <Normal_2_1>
    # 1 record
    # not specify header
    def test_normal_2_1(self, client, db):
        # prepare data
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "message_test1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1
            },
            "e2e_messages": [
                {
                    "id": 1,
                    "from_address": "0x1234567890123456789012345678900000000010",
                    "to_address": "0x1234567890123456789012345678900000000000",
                    "type": "type_test1",
                    "message": "message_test1",
                    "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
                },
            ]
        }

    # <Normal_2_2>
    # 1 record
    # specify header
    def test_normal_2_2(self, client, db):
        # prepare data
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "message_test1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000011",
            "to_address": "0x1234567890123456789012345678900000000001",  # target address
            "type": "type_test2",
            "message": "message_test2",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:31.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url,
            headers={
                "account-address": "0x1234567890123456789012345678900000000001",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1
            },
            "e2e_messages": [
                {
                    "id": 2,
                    "from_address": "0x1234567890123456789012345678900000000011",
                    "to_address": "0x1234567890123456789012345678900000000001",
                    "type": "type_test2",
                    "message": "message_test2",
                    "send_timestamp": "2022-01-02T00:20:31.000001+09:00",
                },
            ]
        }

    # <Normal_3>
    # multi record
    def test_normal_3(self, client, db):
        # prepare data
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "message_test1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000011",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test2",
            "message": json.dumps({"aaa": 1, "bbb": True, "ccc": "hoge"}),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:31.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000001",
            "type": "type_test3",
            "message": json.dumps(["a", "b", "c"]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:32.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000011",
            "to_address": "0x1234567890123456789012345678900000000001",
            "type": "type_test4",
            "message": json.dumps(["a", 1, True]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:33.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test0",
            "message": json.dumps([{"aaa": 1, "bbb": True, "ccc": "hoge"}, {"aaa": 2, "bbb": False, "ccc": "fuga"}]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 5,
                "offset": None,
                "limit": None,
                "total": 5
            },
            "e2e_messages": [
                {
                    "id": 5,
                    "from_address": "0x1234567890123456789012345678900000000010",
                    "to_address": "0x1234567890123456789012345678900000000000",
                    "type": "type_test0",
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
                        },
                    ],
                    "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
                },
                {
                    "id": 4,
                    "from_address": "0x1234567890123456789012345678900000000011",
                    "to_address": "0x1234567890123456789012345678900000000001",
                    "type": "type_test4",
                    "message": ["a", 1, True],
                    "send_timestamp": "2022-01-02T00:20:33.000001+09:00",
                },
                {
                    "id": 3,
                    "from_address": "0x1234567890123456789012345678900000000010",
                    "to_address": "0x1234567890123456789012345678900000000001",
                    "type": "type_test3",
                    "message": ["a", "b", "c"],
                    "send_timestamp": "2022-01-02T00:20:32.000001+09:00",
                },
                {
                    "id": 2,
                    "from_address": "0x1234567890123456789012345678900000000011",
                    "to_address": "0x1234567890123456789012345678900000000000",
                    "type": "type_test2",
                    "message": {
                        "aaa": 1,
                        "bbb": True,
                        "ccc": "hoge"
                    },
                    "send_timestamp": "2022-01-02T00:20:31.000001+09:00",
                },
                {
                    "id": 1,
                    "from_address": "0x1234567890123456789012345678900000000010",
                    "to_address": "0x1234567890123456789012345678900000000000",
                    "type": "type_test1",
                    "message": "message_test1",
                    "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
                },
            ]
        }

    # <Normal_4_1>
    # Search Filter
    # type
    def test_normal_4_1(self, client, db):
        # prepare data
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "message_test1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000011",
            "to_address": "0x1234567890123456789012345678900000000001",
            "type": "type_test2",
            "message": "message_test2",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000012",
            "to_address": "0x1234567890123456789012345678900000000002",
            "type": "type_test1",
            "message": "message_test3",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url,
            params={
                "type": "type_test1"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "e2e_messages": [
                {
                    "id": 3,
                    "from_address": "0x1234567890123456789012345678900000000012",
                    "to_address": "0x1234567890123456789012345678900000000002",
                    "type": "type_test1",
                    "message": "message_test3",
                    "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
                },
                {
                    "id": 1,
                    "from_address": "0x1234567890123456789012345678900000000010",
                    "to_address": "0x1234567890123456789012345678900000000000",
                    "type": "type_test1",
                    "message": "message_test1",
                    "send_timestamp": "2022-01-02T00:20:30.000001+09:00",
                },
            ]
        }

    # <Normal_5>
    # Pagination
    def test_normal_5(self, client, db):
        # prepare data
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test1",
            "message": "message_test1",
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000011",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test2",
            "message": json.dumps({"aaa": 1, "bbb": True, "ccc": "hoge"}),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:31.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000001",
            "type": "type_test3",
            "message": json.dumps(["a", "b", "c"]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:32.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000011",
            "to_address": "0x1234567890123456789012345678900000000001",
            "type": "type_test4",
            "message": json.dumps(["a", 1, True]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:33.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)
        e2e_messaging = {
            "from_address": "0x1234567890123456789012345678900000000010",
            "to_address": "0x1234567890123456789012345678900000000000",
            "type": "type_test0",
            "message": json.dumps([{"aaa": 1, "bbb": True, "ccc": "hoge"}, {"aaa": 2, "bbb": False, "ccc": "fuga"}]),
            "send_timestamp": datetime.strptime("2022/01/01 15:20:30.000001", '%Y/%m/%d %H:%M:%S.%f'),  # JST 2022/01/02
        }
        self.insert_data(db, e2e_messaging)

        # request target api
        resp = client.get(
            self.base_url,
            params={
                "offset": 1,
                "limit": 2,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 5,
                "offset": 1,
                "limit": 2,
                "total": 5
            },
            "e2e_messages": [
                {
                    "id": 4,
                    "from_address": "0x1234567890123456789012345678900000000011",
                    "to_address": "0x1234567890123456789012345678900000000001",
                    "type": "type_test4",
                    "message": ["a", 1, True],
                    "send_timestamp": "2022-01-02T00:20:33.000001+09:00",
                },
                {
                    "id": 3,
                    "from_address": "0x1234567890123456789012345678900000000010",
                    "to_address": "0x1234567890123456789012345678900000000001",
                    "type": "type_test3",
                    "message": ["a", "b", "c"],
                    "send_timestamp": "2022-01-02T00:20:32.000001+09:00",
                },
            ]
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    # Query
    def test_error_1(self, client, db):

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "offset": "test",
                "limit": "test"
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
                    "loc": ["query", "offset"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer"
                },
                {
                    "loc": ["query", "limit"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer"
                },
            ]
        }

    # <Error_2>
    # Parameter Error
    # Header
    def test_error_2(self, client, db):

        # request target API
        resp = client.get(
            self.base_url,
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
