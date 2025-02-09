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

from datetime import UTC, datetime

import pytest

from app.model.db import IDXPersonalInfoHistory, PersonalInfoEventType
from tests.account_config import config_eth_account


class TestListTokenHoldersPersonalInfoHistory:
    # target API endpoint
    url = "/token/holders/personal_info/history"

    test_issuer_address_1 = config_eth_account("user1")["address"]
    test_issuer_address_2 = config_eth_account("user2")["address"]
    test_account_address_1 = config_eth_account("user3")["address"]
    test_account_address_2 = config_eth_account("user4")["address"]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "limit": None, "offset": None, "total": 0},
            "personal_info": [],
        }

    # <Normal_2>
    # Multiple records
    # No search filter
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 12, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 13, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 13, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_2
        history.account_address = self.test_account_address_2
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 13, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 2},
            "personal_info": [
                {
                    "id": 1,
                    "account_address": self.test_account_address_1,
                    "event_type": "register",
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-13T08:59:59+09:00",
                    "created": "2024-05-13T09:00:00+09:00",
                },
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T08:59:59+09:00",
                    "created": "2024-05-14T09:00:00+09:00",
                },
            ],
        }

    # <Normal_3_1_1>
    # Multiple records
    # Search filter: key_manager_type = "SELF"
    @pytest.mark.freeze_time("2024-11-11 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_3_1_1(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_2
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "SELF",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={"key_manager_type": "SELF"},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "personal_info": [
                {
                    "id": 3,
                    "account_address": self.test_account_address_2,
                    "event_type": "register",
                    "personal_info": {
                        "key_manager": "SELF",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": "birth_test3",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-11-11T21:34:56+09:00",
                    "created": "2024-11-11T21:34:56+09:00",
                },
            ],
        }

    # <Normal_3_1_2>
    # Multiple records
    # Search filter: key_manager_type = "OTHERS"
    @pytest.mark.freeze_time("2024-11-11 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_3_1_2(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_2
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "SELF",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={"key_manager_type": "OTHERS"},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 2},
            "personal_info": [
                {
                    "id": 1,
                    "account_address": self.test_account_address_1,
                    "event_type": "register",
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-11-11T21:34:56+09:00",
                    "created": "2024-11-11T21:34:56+09:00",
                },
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-11-11T21:34:56+09:00",
                    "created": "2024-11-11T21:34:56+09:00",
                },
            ],
        }

    # <Normal_3_2>
    # Multiple records
    # Search filter: account_address
    @pytest.mark.asyncio
    async def test_normal_3_2(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 12, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 13, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 13, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_2
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 13, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={"account_address": self.test_account_address_1},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "id": 1,
                    "account_address": self.test_account_address_1,
                    "event_type": "register",
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-13T08:59:59+09:00",
                    "created": "2024-05-13T09:00:00+09:00",
                },
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T08:59:59+09:00",
                    "created": "2024-05-14T09:00:00+09:00",
                },
            ],
        }

    # <Normal_3_3>
    # Multiple records
    # Search filter: event_type
    @pytest.mark.asyncio
    async def test_normal_3_3(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 12, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 13, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={
                "event_type": "modify",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T09:00:00+09:00",
                    "created": "2024-05-14T09:00:01+09:00",
                },
            ],
        }

    # <Normal_3_4>
    # Multiple records
    # Search filter: created_from, created_to
    @pytest.mark.asyncio
    async def test_normal_3_4(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 12, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 13, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={
                "created_from": "2024-05-14 09:00:01",
                "created_to": "2024-05-14 09:00:01",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T09:00:00+09:00",
                    "created": "2024-05-14T09:00:01+09:00",
                },
            ],
        }

    # <Normal_3_5>
    # Multiple records
    # Search filter: block_timestamp_from, block_timestamp_to
    @pytest.mark.asyncio
    async def test_normal_3_5(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 12, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 13, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={
                "block_timestamp_from": "2024-05-14 09:00:00",
                "block_timestamp_to": "2024-05-14 09:00:00",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T09:00:00+09:00",
                    "created": "2024-05-14T09:00:01+09:00",
                },
            ],
        }

    # <Normal_4>
    # Multiple records
    # Sort: block_timestamp, DESC
    @pytest.mark.asyncio
    async def test_normal_4(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 13, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={
                "sort_order": 1,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "id": 3,
                    "account_address": self.test_account_address_1,
                    "event_type": "register",
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": "birth_test3",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T09:00:01+09:00",
                    "created": "2024-05-14T09:00:02+09:00",
                },
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T09:00:00+09:00",
                    "created": "2024-05-14T09:00:01+09:00",
                },
                {
                    "id": 1,
                    "account_address": self.test_account_address_1,
                    "event_type": "register",
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T08:59:59+09:00",
                    "created": "2024-05-14T09:00:00+09:00",
                },
            ],
        }

    # <Normal_5>
    # Multiple records
    # Pagination: offset, limit
    @pytest.mark.asyncio
    async def test_normal_5(self, async_client, async_db):
        # Prepare data
        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 12, 23, 59, 59, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.MODIFY
        history.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        history = IDXPersonalInfoHistory()
        history.issuer_address = self.test_issuer_address_1
        history.account_address = self.test_account_address_1
        history.event_type = PersonalInfoEventType.REGISTER
        history.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        history.block_timestamp = datetime(2024, 5, 14, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        history.created = datetime(2024, 5, 14, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        async_db.add(history)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={"offset": 1, "limit": 1},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": 1, "offset": 1, "total": 3},
            "personal_info": [
                {
                    "id": 2,
                    "account_address": self.test_account_address_1,
                    "event_type": "modify",
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "block_timestamp": "2024-05-14T09:00:00+09:00",
                    "created": "2024-05-14T09:00:01+09:00",
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: created_from, created_to
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # Request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            },
            params={
                "created_from": "invalid_date",
                "created_to": "invalid_date",
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["query", "created_from"],
                    "msg": "Value error, value must be of string datetime format",
                    "input": "invalid_date",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "created_to"],
                    "msg": "Value error, value must be of string datetime format",
                    "input": "invalid_date",
                    "ctx": {"error": {}},
                },
            ],
        }
