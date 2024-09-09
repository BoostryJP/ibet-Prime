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
from unittest.mock import ANY

from app.model.db import (
    BatchIssueRedeemProcessingCategory,
    Notification,
    NotificationType,
    TokenType,
)
from tests.account_config import config_eth_account


class TestListAllNotifications:
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
        _notification_1.code = 2
        _notification_1.metainfo = {
            "upload_id": str(uuid.uuid4()),
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "error_transfer_id": [],
        }
        _notification_1.created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_notification_1)

        _notification_2 = Notification()
        _notification_2.notice_id = "notice_id_2"
        _notification_2.issuer_address = issuer_address_1
        _notification_2.priority = 1
        _notification_2.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_2.code = 2
        _notification_2.metainfo = {
            "scheduled_event_id": "1",
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        _notification_2.created = datetime.strptime(
            "2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_notification_2)

        _notification_3 = Notification()
        _notification_3.notice_id = "notice_id_3"
        _notification_3.issuer_address = issuer_address_2
        _notification_3.priority = 2
        _notification_3.type = NotificationType.ISSUE_ERROR
        _notification_3.code = 2
        _notification_3.metainfo = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "arguments": {},
        }
        _notification_3.created = datetime.strptime(
            "2022/01/02 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_3)

        _notification_4 = Notification()
        _notification_4.notice_id = "notice_id_4"
        _notification_4.issuer_address = issuer_address_2
        _notification_4.priority = 0
        _notification_4.type = NotificationType.TRANSFER_APPROVAL_INFO
        _notification_4.code = 3
        _notification_4.metainfo = {
            "id": 1,
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        _notification_4.created = datetime.strptime(
            "2022/01/03 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_4)

        _notification_5 = Notification()
        _notification_5.notice_id = "notice_id_5"
        _notification_5.issuer_address = issuer_address_2
        _notification_5.priority = 0
        _notification_5.type = NotificationType.CREATE_LEDGER_INFO
        _notification_5.code = 0
        _notification_5.metainfo = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "ledger_id": 1,
        }
        _notification_5.created = datetime.strptime(
            "2022/01/05 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_5)

        _notification_6 = Notification()
        _notification_6.notice_id = "notice_id_6"
        _notification_6.issuer_address = issuer_address_2
        _notification_6.priority = 0
        _notification_6.type = NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
        _notification_6.code = 1
        _notification_6.metainfo = {
            "upload_id": str(uuid.uuid4()),
            "error_registration_id": [1, 2, 3],
        }
        _notification_6.created = datetime.strptime(
            "2022/01/06 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_6)

        _notification_7 = Notification()
        _notification_7.notice_id = "notice_id_7"
        _notification_7.issuer_address = issuer_address_2
        _notification_7.priority = 0
        _notification_7.type = NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
        _notification_7.code = 3
        _notification_7.metainfo = {
            "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
            "upload_id": str(uuid.uuid4()),
            "error_data_id": [1, 2, 3],
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        _notification_7.created = datetime.strptime(
            "2022/01/07 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_7)

        _notification_8 = Notification()
        _notification_8.notice_id = "notice_id_8"
        _notification_8.issuer_address = issuer_address_2
        _notification_8.priority = 0
        _notification_8.type = NotificationType.LOCK_INFO
        _notification_8.code = 0
        _notification_8.metainfo = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "lock_address": "0x0000000000000000000000000000000000000000",
            "account_address": "0x0000000000000000000000000000000000000000",
            "value": 30,
            "data": {"message": "lock1"},
        }
        _notification_8.created = datetime.strptime(
            "2022/01/08 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_8)

        _notification_9 = Notification()
        _notification_9.notice_id = "notice_id_9"
        _notification_9.issuer_address = issuer_address_2
        _notification_9.priority = 0
        _notification_9.type = NotificationType.UNLOCK_INFO
        _notification_9.code = 0
        _notification_9.metainfo = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_SHARE.value,
            "lock_address": "0x0000000000000000000000000000000000000000",
            "account_address": "0x0000000000000000000000000000000000000000",
            "recipient_address": "0x0000000000000000000000000000000000000000",
            "value": 30,
            "data": {"message": "unlock1"},
        }
        _notification_9.created = datetime.strptime(
            "2022/01/09 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_9)

        _notification_10 = Notification()
        _notification_10.notice_id = "notice_id_10"
        _notification_10.issuer_address = issuer_address_2
        _notification_10.priority = 0
        _notification_10.type = NotificationType.DVP_DELIVERY_INFO
        _notification_10.code = 0
        _notification_10.metainfo = {
            "exchange_address": "0x0000000000000000000000000000000000000000",
            "delivery_id": 1,
            "token_address": "0x0000000000000000000000000000000000000000",
            "token_type": TokenType.IBET_SHARE.value,
            "seller_address": "0x0000000000000000000000000000000000000000",
            "buyer_address": "0x0000000000000000000000000000000000000000",
            "agent_address": "0x0000000000000000000000000000000000000000",
            "amount": 30,
        }
        _notification_10.created = datetime.strptime(
            "2022/01/09 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_10)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 10, "offset": None, "limit": None, "total": 10},
            "notifications": [
                {
                    "notice_id": "notice_id_1",
                    "issuer_address": issuer_address_1,
                    "priority": 0,
                    "notice_type": NotificationType.BULK_TRANSFER_ERROR,
                    "notice_code": 2,
                    "metainfo": {
                        "upload_id": ANY,
                        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                        "error_transfer_id": [],
                    },
                    "created": "2022-01-02T00:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_2",
                    "issuer_address": issuer_address_1,
                    "priority": 1,
                    "notice_type": NotificationType.SCHEDULE_EVENT_ERROR,
                    "notice_code": 2,
                    "metainfo": {
                        "scheduled_event_id": "1",
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    },
                    "created": "2022-01-02T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_3",
                    "issuer_address": issuer_address_2,
                    "priority": 2,
                    "notice_type": NotificationType.ISSUE_ERROR,
                    "notice_code": 2,
                    "metainfo": {
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                        "arguments": {},
                    },
                    "created": "2022-01-03T00:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_4",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.TRANSFER_APPROVAL_INFO,
                    "notice_code": 3,
                    "metainfo": {
                        "id": 1,
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_STRAIGHT_BOND,
                    },
                    "created": "2022-01-03T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_5",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.CREATE_LEDGER_INFO,
                    "notice_code": 0,
                    "metainfo": {
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                        "ledger_id": 1,
                    },
                    "created": "2022-01-05T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_6",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR,
                    "notice_code": 1,
                    "metainfo": {"upload_id": ANY, "error_registration_id": [1, 2, 3]},
                    "created": "2022-01-06T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_7",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.BATCH_ISSUE_REDEEM_PROCESSED,
                    "notice_code": 3,
                    "metainfo": {
                        "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
                        "upload_id": ANY,
                        "error_data_id": [1, 2, 3],
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_STRAIGHT_BOND,
                    },
                    "created": "2022-01-07T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_8",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.LOCK_INFO,
                    "notice_code": 0,
                    "metainfo": {
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_STRAIGHT_BOND,
                        "lock_address": "0x0000000000000000000000000000000000000000",
                        "account_address": "0x0000000000000000000000000000000000000000",
                        "value": 30,
                        "data": {"message": "lock1"},
                    },
                    "created": "2022-01-08T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_9",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.UNLOCK_INFO,
                    "notice_code": 0,
                    "metainfo": {
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_SHARE,
                        "lock_address": "0x0000000000000000000000000000000000000000",
                        "account_address": "0x0000000000000000000000000000000000000000",
                        "recipient_address": "0x0000000000000000000000000000000000000000",
                        "value": 30,
                        "data": {"message": "unlock1"},
                    },
                    "created": "2022-01-09T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_10",
                    "issuer_address": issuer_address_2,
                    "priority": 0,
                    "notice_type": NotificationType.DVP_DELIVERY_INFO,
                    "notice_code": 0,
                    "metainfo": {
                        "exchange_address": "0x0000000000000000000000000000000000000000",
                        "delivery_id": 1,
                        "token_address": "0x0000000000000000000000000000000000000000",
                        "token_type": TokenType.IBET_SHARE.value,
                        "seller_address": "0x0000000000000000000000000000000000000000",
                        "buyer_address": "0x0000000000000000000000000000000000000000",
                        "agent_address": "0x0000000000000000000000000000000000000000",
                        "amount": 30,
                    },
                    "created": "2022-01-09T09:20:30+09:00",
                },
            ],
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
            "upload_id": str(uuid.uuid4()),
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "error_transfer_id": [],
        }
        _notification_1.created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_notification_1)

        _notification_2 = Notification()
        _notification_2.notice_id = "notice_id_2"
        _notification_2.issuer_address = issuer_address_1
        _notification_2.priority = 1
        _notification_2.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_2.code = 1
        _notification_2.metainfo = {
            "scheduled_event_id": "1",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        _notification_2.created = datetime.strptime(
            "2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_notification_2)

        _notification_3 = Notification()
        _notification_3.notice_id = "notice_id_3"
        _notification_3.issuer_address = issuer_address_2
        _notification_3.priority = 2
        _notification_3.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_3.code = 2
        _notification_3.metainfo = {
            "upload_id": str(uuid.uuid4()),
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "error_transfer_id": [],
        }
        _notification_3.created = datetime.strptime(
            "2022/01/02 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_3)

        _notification_4 = Notification()
        _notification_4.notice_id = "notice_id_4"
        _notification_4.issuer_address = issuer_address_2
        _notification_4.priority = 0
        _notification_4.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_4.code = 3
        _notification_4.metainfo = {
            "scheduled_event_id": "1",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        _notification_4.created = datetime.strptime(
            "2022/01/03 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_4)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "notice_type": NotificationType.SCHEDULE_EVENT_ERROR.value,
            },
            headers={
                "issuer-address": issuer_address_1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 4},
            "notifications": [
                {
                    "notice_id": "notice_id_2",
                    "issuer_address": issuer_address_1,
                    "priority": 1,
                    "notice_type": NotificationType.SCHEDULE_EVENT_ERROR.value,
                    "notice_code": 1,
                    "metainfo": {
                        "scheduled_event_id": "1",
                        "token_address": None,
                        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    },
                    "created": "2022-01-02T09:20:30+09:00",
                },
            ],
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
            "upload_id": str(uuid.uuid4()),
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "error_transfer_id": [],
        }
        _notification_1.created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_notification_1)

        _notification_2 = Notification()
        _notification_2.notice_id = "notice_id_2"
        _notification_2.issuer_address = issuer_address_1
        _notification_2.priority = 1
        _notification_2.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_2.code = 1
        _notification_2.metainfo = {
            "scheduled_event_id": "1",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        _notification_2.created = datetime.strptime(
            "2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_notification_2)

        _notification_3 = Notification()
        _notification_3.notice_id = "notice_id_3"
        _notification_3.issuer_address = issuer_address_2
        _notification_3.priority = 2
        _notification_3.type = NotificationType.TRANSFER_APPROVAL_INFO
        _notification_3.code = 2
        _notification_3.metainfo = {
            "id": 1,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_address": "0x0000000000000000000000000000000000000000",
        }
        _notification_3.created = datetime.strptime(
            "2022/01/02 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_3)

        _notification_4 = Notification()
        _notification_4.notice_id = "notice_id_4"
        _notification_4.issuer_address = issuer_address_2
        _notification_4.priority = 0
        _notification_4.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_4.code = 3
        _notification_4.metainfo = {
            "scheduled_event_id": "1",
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        }
        _notification_4.created = datetime.strptime(
            "2022/01/03 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_notification_4)

        db.commit()

        # request target API
        resp = client.get(self.base_url, params={"offset": 1, "limit": 2})

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": 1, "limit": 2, "total": 4},
            "notifications": [
                {
                    "notice_id": "notice_id_2",
                    "issuer_address": issuer_address_1,
                    "priority": 1,
                    "notice_type": NotificationType.SCHEDULE_EVENT_ERROR.value,
                    "notice_code": 1,
                    "metainfo": {
                        "scheduled_event_id": "1",
                        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                        "token_address": None,
                    },
                    "created": "2022-01-02T09:20:30+09:00",
                },
                {
                    "notice_id": "notice_id_3",
                    "issuer_address": issuer_address_2,
                    "priority": 2,
                    "notice_type": NotificationType.TRANSFER_APPROVAL_INFO.value,
                    "notice_code": 2,
                    "metainfo": {
                        "id": 1,
                        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                        "token_address": "0x0000000000000000000000000000000000000000",
                    },
                    "created": "2022-01-03T00:20:30+09:00",
                },
            ],
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
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }
