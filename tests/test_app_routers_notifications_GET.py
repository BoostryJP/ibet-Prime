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
from datetime import datetime

from app.model.db import (
    Notification,
    NotificationType
)
from tests.account_config import config_eth_account


class TestAppRoutersNotificationsPOST:
    # target API endpoint
    base_url = "/notifications"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Non filtered
    def test_normal_1(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        # prepare data
        _notification_1 = Notification()
        _notification_1.notice_id = "notice_id_1"
        _notification_1.issuer_address = issuer_address_1
        _notification_1.priority = 0
        _notification_1.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_1.code = 0
        _notification_1.metainfo = {
            "test_1": "test_1"
        }
        _notification_1.created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_notification_1)

        _notification_2 = Notification()
        _notification_2.notice_id = "notice_id_2"
        _notification_2.issuer_address = issuer_address_1
        _notification_2.priority = 1
        _notification_2.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_2.code = 1
        _notification_2.metainfo = {
            "test_2": "test_2"
        }
        _notification_2.created = datetime.strptime("2022/01/02 00:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_notification_2)

        _notification_3 = Notification()
        _notification_3.notice_id = "notice_id_3"
        _notification_3.issuer_address = issuer_address_2
        _notification_3.priority = 2
        _notification_3.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_3.code = 2
        _notification_3.metainfo = {
            "test_3": "test_3"
        }
        _notification_3.created = datetime.strptime("2022/01/02 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/03
        db.add(_notification_3)

        _notification_4 = Notification()
        _notification_4.notice_id = "notice_id_4"
        _notification_4.issuer_address = issuer_address_2
        _notification_4.priority = 0
        _notification_4.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_4.code = 3
        _notification_4.metainfo = {
            "test_4": "test_4"
        }
        _notification_4.created = datetime.strptime("2022/01/03 00:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/03
        db.add(_notification_4)

        # request target API
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4
            },
            "notifications": [
                {
                    "notice_id": "notice_id_1",
                    "issuer_address": issuer_address_1,
                    "priority": 0,
                    "notice_type": NotificationType.BULK_TRANSFER_ERROR,
                    "notice_code": 0,
                    "metainfo": {
                        "test_1": "test_1"
                    },
                    "created": "2022-01-02T00:20:30+09:00"
                },
                {
                    "notice_id": "notice_id_2",
                    "issuer_address": issuer_address_1,
                    "priority": 1,
                    "notice_type": NotificationType.SCHEDULE_EVENT_ERROR,
                    "notice_code": 1,
                    "metainfo": {
                        "test_2": "test_2"
                    },
                    "created": "2022-01-02T09:20:30+09:00"
                },
                {
                    "notice_id": "notice_id_3",
                    "issuer_address": issuer_address_2,
                    "priority": 2,
                    "notice_type": NotificationType.BULK_TRANSFER_ERROR,
                    "notice_code": 2,
                    "metainfo": {
                        "test_3": "test_3"
                    },
                    "created": "2022-01-03T00:20:30+09:00"
                },
                {
                    "notice_id": "notice_id_4",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.SCHEDULE_EVENT_ERROR,
                    "notice_code": 3,
                    "metainfo": {
                        "test_4": "test_4"
                    },
                    "created": "2022-01-03T09:20:30+09:00"
                },
            ]
        }

    # <Normal_2>
    # filtered
    def test_normal_2(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        # prepare data
        _notification_1 = Notification()
        _notification_1.notice_id = "notice_id_1"
        _notification_1.issuer_address = issuer_address_1
        _notification_1.priority = 0
        _notification_1.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_1.code = 0
        _notification_1.metainfo = {
            "test_1": "test_1"
        }
        _notification_1.created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_notification_1)

        _notification_2 = Notification()
        _notification_2.notice_id = "notice_id_2"
        _notification_2.issuer_address = issuer_address_1
        _notification_2.priority = 1
        _notification_2.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_2.code = 1
        _notification_2.metainfo = {
            "test_2": "test_2"
        }
        _notification_2.created = datetime.strptime("2022/01/02 00:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_notification_2)

        _notification_3 = Notification()
        _notification_3.notice_id = "notice_id_3"
        _notification_3.issuer_address = issuer_address_2
        _notification_3.priority = 2
        _notification_3.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_3.code = 2
        _notification_3.metainfo = {
            "test_3": "test_3"
        }
        _notification_3.created = datetime.strptime("2022/01/02 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/03
        db.add(_notification_3)

        _notification_4 = Notification()
        _notification_4.notice_id = "notice_id_4"
        _notification_4.issuer_address = issuer_address_2
        _notification_4.priority = 0
        _notification_4.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_4.code = 3
        _notification_4.metainfo = {
            "test_4": "test_4"
        }
        _notification_4.created = datetime.strptime("2022/01/03 00:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/03
        db.add(_notification_4)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "notice_type": NotificationType.SCHEDULE_EVENT_ERROR,
            },
            headers={
                "issuer-address": issuer_address_1,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 4
            },
            "notifications": [
                {
                    "notice_id": "notice_id_2",
                    "issuer_address": issuer_address_1,
                    "priority": 1,
                    "notice_type": NotificationType.SCHEDULE_EVENT_ERROR,
                    "notice_code": 1,
                    "metainfo": {
                        "test_2": "test_2"
                    },
                    "created": "2022-01-02T09:20:30+09:00"
                },
            ]
        }

    # <Normal_3>
    # limit-offset
    def test_normal_3(self, client, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]

        # prepare data
        _notification_1 = Notification()
        _notification_1.notice_id = "notice_id_1"
        _notification_1.issuer_address = issuer_address_1
        _notification_1.priority = 0
        _notification_1.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_1.code = 0
        _notification_1.metainfo = {
            "test_1": "test_1"
        }
        _notification_1.created = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_notification_1)

        _notification_2 = Notification()
        _notification_2.notice_id = "notice_id_2"
        _notification_2.issuer_address = issuer_address_1
        _notification_2.priority = 1
        _notification_2.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_2.code = 1
        _notification_2.metainfo = {
            "test_2": "test_2"
        }
        _notification_2.created = datetime.strptime("2022/01/02 00:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_notification_2)

        _notification_3 = Notification()
        _notification_3.notice_id = "notice_id_3"
        _notification_3.issuer_address = issuer_address_2
        _notification_3.priority = 2
        _notification_3.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_3.code = 2
        _notification_3.metainfo = {
            "test_3": "test_3"
        }
        _notification_3.created = datetime.strptime("2022/01/02 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/03
        db.add(_notification_3)

        _notification_4 = Notification()
        _notification_4.notice_id = "notice_id_4"
        _notification_4.issuer_address = issuer_address_2
        _notification_4.priority = 0
        _notification_4.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_4.code = 3
        _notification_4.metainfo = {
            "test_4": "test_4"
        }
        _notification_4.created = datetime.strptime("2022/01/03 00:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/03
        db.add(_notification_4)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "offset": 1,
                "limit": 2
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": 1,
                "limit": 2,
                "total": 4
            },
            "notifications": [
                {
                    "notice_id": "notice_id_2",
                    "issuer_address": issuer_address_1,
                    "priority": 1,
                    "notice_type": NotificationType.SCHEDULE_EVENT_ERROR,
                    "notice_code": 1,
                    "metainfo": {
                        "test_2": "test_2"
                    },
                    "created": "2022-01-02T09:20:30+09:00"
                },
                {
                    "notice_id": "notice_id_3",
                    "issuer_address": issuer_address_2,
                    "priority": 2,
                    "notice_type": NotificationType.BULK_TRANSFER_ERROR,
                    "notice_code": 2,
                    "metainfo": {
                        "test_3": "test_3"
                    },
                    "created": "2022-01-03T00:20:30+09:00"
                },
            ]
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
            headers={
                "issuer-address": "test",
            }
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
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }
