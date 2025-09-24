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

import pytest
from sqlalchemy import select

from app.model.db import Notification, NotificationType
from tests.account_config import default_eth_account


class TestDeleteNotification:
    # target API endpoint
    base_url = "/notifications/{notice_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Non filtered
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        user_1 = default_eth_account("user1")
        issuer_address_1 = user_1["address"]
        user_2 = default_eth_account("user2")
        issuer_address_2 = user_2["address"]

        # prepare data
        _notification_1 = Notification()
        _notification_1.notice_id = "notice_id_1"
        _notification_1.issuer_address = issuer_address_1
        _notification_1.priority = 0
        _notification_1.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_1.code = 0
        _notification_1.metainfo = {"test_1": "test_1"}
        _notification_1.created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_notification_1)

        _notification_2 = Notification()
        _notification_2.notice_id = "notice_id_2"
        _notification_2.issuer_address = issuer_address_1
        _notification_2.priority = 1
        _notification_2.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_2.code = 1
        _notification_2.metainfo = {"test_2": "test_2"}
        _notification_2.created = datetime.strptime(
            "2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_notification_2)

        _notification_3 = Notification()
        _notification_3.notice_id = "notice_id_3"
        _notification_3.issuer_address = issuer_address_2
        _notification_3.priority = 2
        _notification_3.type = NotificationType.BULK_TRANSFER_ERROR
        _notification_3.code = 2
        _notification_3.metainfo = {"test_3": "test_3"}
        _notification_3.created = datetime.strptime(
            "2022/01/02 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        async_db.add(_notification_3)

        _notification_4 = Notification()
        _notification_4.notice_id = "notice_id_4"
        _notification_4.issuer_address = issuer_address_2
        _notification_4.priority = 0
        _notification_4.type = NotificationType.SCHEDULE_EVENT_ERROR
        _notification_4.code = 3
        _notification_4.metainfo = {"test_4": "test_4"}
        _notification_4.created = datetime.strptime(
            "2022/01/03 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        async_db.add(_notification_4)

        await async_db.commit()

        # request target API
        resp = await async_client.delete(
            self.base_url.format(notice_id="notice_id_2"),
            headers={
                "issuer-address": issuer_address_1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None
        _notification_list = (
            await async_db.scalars(select(Notification).order_by(Notification.created))
        ).all()
        assert len(_notification_list) == 3
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert _notification.notice_id == "notice_id_1"
        assert _notification.issuer_address == issuer_address_1
        assert _notification.priority == 0
        assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
        assert _notification.code == 0
        assert _notification.metainfo == {"test_1": "test_1"}
        _notification = _notification_list[1]
        assert _notification.id == 3
        assert _notification.notice_id == "notice_id_3"
        assert _notification.issuer_address == issuer_address_2
        assert _notification.priority == 2
        assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
        assert _notification.code == 2
        assert _notification.metainfo == {"test_3": "test_3"}
        _notification = _notification_list[2]
        assert _notification.id == 4
        assert _notification.notice_id == "notice_id_4"
        assert _notification.issuer_address == issuer_address_2
        assert _notification.priority == 0
        assert _notification.type == NotificationType.SCHEDULE_EVENT_ERROR
        assert _notification.code == 3
        assert _notification.metainfo == {"test_4": "test_4"}

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error(required)
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # request target API
        resp = await async_client.delete(
            self.base_url.format(notice_id="notice_id_2"),
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # <Error_2>
    # Parameter Error(invalid address)
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # request target API
        resp = await async_client.delete(
            self.base_url.format(notice_id="notice_id_2"),
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

    # <Error_3>
    # notification does not exist
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        user_1 = default_eth_account("user1")
        issuer_address_1 = user_1["address"]

        # request target API
        resp = await async_client.delete(
            self.base_url.format(notice_id="notice_id_2"),
            headers={
                "issuer-address": issuer_address_1,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "notification does not exist",
        }
