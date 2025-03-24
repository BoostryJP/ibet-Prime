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
from unittest import mock

import pytest

from app.model.db import IDXPersonalInfo, PersonalInfoDataSource
from tests.account_config import config_eth_account


class TestListTokenHoldersPersonalInfo:
    # target API endpoint
    url = "/token/holders/personal_info"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "limit": None, "offset": None, "total": 0},
            "personal_info": [],
        }

    # <Normal_2>
    # 1 record
    @pytest.mark.freeze_time("2024-05-13 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "personal_info": [
                {
                    "account_address": account_address1,
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
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                }
            ],
        }

    # <Normal_3>
    # Multiple records
    # No search filter
    @pytest.mark.freeze_time("2024-05-13 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_3(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address1,
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
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
                {
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
            ],
        }

    # <Normal_4_1_1>
    # Multiple records
    # Search filter: key_manager_type = "SELF"
    @pytest.mark.freeze_time("2024-05-13 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_4_1_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "SELF",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.OFF_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={
                "key_manager_type": "SELF",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "personal_info": [
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "SELF",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
            ],
        }

    # <Normal_4_1_2>
    # Multiple records
    # Search filter: key_manager_type = "OTHERS"
    @pytest.mark.freeze_time("2024-05-13 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_4_1_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "SELF",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.OFF_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={
                "key_manager_type": "OTHERS",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 2},
            "personal_info": [
                {
                    "account_address": account_address1,
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
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
                {
                    "account_address": account_address3,
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
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
            ],
        }

    # <Normal_4_2>
    # Multiple records
    # Search filter: account_address
    @pytest.mark.asyncio
    async def test_normal_4_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 9, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 9, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 12, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 12, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 15, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 15, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={
                "account_address": account_address2,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:00:00+09:00",
                    "modified": "2024-05-14T21:00:00+09:00",
                },
            ],
        }

    # <Normal_4_3>
    # Multiple records
    # Search filter: created_from, created_to
    @pytest.mark.asyncio
    async def test_normal_4_3(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 9, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 9, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 12, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 12, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 15, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 15, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={
                "created_from": "2024-05-13 21:00:00",
                "created_to": "2024-05-13 21:00:00",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:00:00+09:00",
                    "modified": "2024-05-14T21:00:00+09:00",
                },
            ],
        }

    # <Normal_4_4>
    # Multiple records
    # Search filter: modified_from, modified_to
    @pytest.mark.asyncio
    async def test_normal_4_4(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 9, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 9, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 12, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 12, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2024, 5, 13, 15, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2024, 5, 14, 15, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={
                "modified_from": "2024-05-14 21:00:00",
                "modified_to": "2024-05-14 21:00:00",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:00:00+09:00",
                    "modified": "2024-05-14T21:00:00+09:00",
                },
            ],
        }

    # <Normal_5_1>
    # Sort
    # - sort_item: None(created)
    # - sort_order: DESC
    @pytest.mark.asyncio
    async def test_normal_5_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(2023, 10, 24, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(
            2023, 10, 24, 0, 0, 1, tzinfo=UTC
        ).replace(tzinfo=None)
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(
            2023, 10, 24, 0, 0, 2, tzinfo=UTC
        ).replace(tzinfo=None)
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={"sort_order": 1},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2023-10-23T09:00:02+09:00",
                    "modified": "2023-10-24T09:00:02+09:00",
                },
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2023-10-23T09:00:01+09:00",
                    "modified": "2023-10-24T09:00:01+09:00",
                },
                {
                    "account_address": account_address1,
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
                    "created": "2023-10-23T09:00:00+09:00",
                    "modified": "2023-10-24T09:00:00+09:00",
                },
            ],
        }

    # <Normal_5_2>
    # Sort
    # - sort_item: account_address
    # - sort_order: ASC
    @pytest.mark.asyncio
    async def test_normal_5_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={"sort_item": "account_address", "sort_order": 0},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address1,
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
                    "created": mock.ANY,
                    "modified": mock.ANY,
                },
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                    "modified": mock.ANY,
                },
                {
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                    "modified": mock.ANY,
                },
            ],
        }

    # <Normal_5_3>
    # Sort
    # - sort_item: modified
    # - sort_order: ASC
    @pytest.mark.asyncio
    async def test_normal_5_3(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 0, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(
            2023, 10, 24, 0, 0, 2, tzinfo=UTC
        ).replace(tzinfo=None)
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 1, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(
            2023, 10, 24, 0, 0, 1, tzinfo=UTC
        ).replace(tzinfo=None)
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = datetime(2023, 10, 23, 0, 0, 2, tzinfo=UTC).replace(
            tzinfo=None
        )
        personal_info_idx.modified = datetime(
            2023, 10, 24, 0, 0, 0, tzinfo=UTC
        ).replace(tzinfo=None)
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={"sort_item": "modified", "sort_order": 0},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2023-10-23T09:00:02+09:00",
                    "modified": "2023-10-24T09:00:00+09:00",
                },
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2023-10-23T09:00:01+09:00",
                    "modified": "2023-10-24T09:00:01+09:00",
                },
                {
                    "account_address": account_address1,
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
                    "created": "2023-10-23T09:00:00+09:00",
                    "modified": "2023-10-24T09:00:02+09:00",
                },
            ],
        }

    # <Normal_6>
    # Pagination
    @pytest.mark.freeze_time("2024-05-13 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_6(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(personal_info_idx)

        await async_db.commit()

        # request target API
        req_param = {"limit": 2, "offset": 1}
        resp = await async_client.get(
            self.url,
            params=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": 2, "offset": 1, "total": 3},
            "personal_info": [
                {
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
                {
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": "2024-05-13T21:34:56+09:00",
                    "modified": "2024-05-13T21:34:56+09:00",
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError: created_from, created_to, modified_from, modified_to
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={
                "created_from": "invalid_date",
                "created_to": "invalid_date",
                "modified_from": "invalid_date",
                "modified_to": "invalid_date",
            },
        )

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
                {
                    "type": "value_error",
                    "loc": ["query", "modified_from"],
                    "msg": "Value error, value must be of string datetime format",
                    "input": "invalid_date",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["query", "modified_to"],
                    "msg": "Value error, value must be of string datetime format",
                    "input": "invalid_date",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_1_2>
    # RequestValidationError: sort_item, sort_order
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]

        # request target API
        resp = await async_client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
            params={"sort_item": "invalid_sort_item", "sort_order": 2},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'account_address', 'created' or 'modified'",
                    "input": "invalid_sort_item",
                    "ctx": {"expected": "'account_address', 'created' or 'modified'"},
                },
                {
                    "type": "enum",
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "input": "2",
                    "ctx": {"expected": "0 or 1"},
                },
            ],
        }
