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

import datetime

import pytest
from sqlalchemy import and_, select

from app.model.db import (
    Account,
    ChildAccount,
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
)


class TestUpdateChildAccount:
    issuer_address = "0x89082C5dEcB1Ad23eda99B692A9B594F7044B846"
    child_account_address = "0x9f07d281F2f78891637cD72C7a4a1b5da309449A"

    # Target API endpoint
    base_url = "/accounts/{}/child_accounts/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.freeze_time("2024-09-28 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        async_db.add(_account)

        _child_account = ChildAccount()
        _child_account.issuer_address = self.issuer_address
        _child_account.child_account_index = 1
        _child_account.child_account_address = self.child_account_address
        async_db.add(_child_account)

        _off_personal_info = IDXPersonalInfo()
        _off_personal_info.issuer_address = self.issuer_address
        _off_personal_info.account_address = self.child_account_address
        _off_personal_info.personal_info = {
            "key_manager": "SELF",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
            "tax_category": 10,
        }
        _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
        async_db.add(_off_personal_info)

        await async_db.commit()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address, 1),
            json={
                "personal_information": {
                    "name": "name_test_af",
                    "postal_code": "postal_code_test_af",
                    "address": "address_test_af",
                    "email": "email_test_af",
                    "birth": "birth_test_af",
                    "is_corporate": True,
                    "tax_category": 20,
                }
            },
        )

        # Assertion
        assert resp.status_code == 200

        _off_personal_info_af = (
            await async_db.scalars(
                select(IDXPersonalInfo)
                .where(
                    and_(
                        IDXPersonalInfo.issuer_address == self.issuer_address,
                        IDXPersonalInfo.account_address == self.child_account_address,
                        IDXPersonalInfo.data_source == PersonalInfoDataSource.OFF_CHAIN,
                    )
                )
                .limit(1)
            )
        ).first()
        assert _off_personal_info.personal_info == {
            "key_manager": "SELF",
            "name": "name_test_af",
            "postal_code": "postal_code_test_af",
            "address": "address_test_af",
            "email": "email_test_af",
            "birth": "birth_test_af",
            "is_corporate": True,
            "tax_category": 20,
        }

        _personal_info_history = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory)
                .where(IDXPersonalInfoHistory.issuer_address == self.issuer_address)
                .limit(1)
            )
        ).first()
        assert _personal_info_history.issuer_address == self.issuer_address
        assert _personal_info_history.account_address == self.child_account_address
        assert _personal_info_history.event_type == PersonalInfoEventType.MODIFY
        assert _personal_info_history.personal_info == _off_personal_info.personal_info
        assert _personal_info_history.block_timestamp == datetime.datetime(
            2024, 9, 28, 12, 34, 56
        )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # - Missing body
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address, 1), json={}
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "personal_information"],
                    "msg": "Field required",
                    "input": {},
                }
            ],
        }

    # <Error_2>
    # 404: Issuer does not exist
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address, 1),
            json={
                "personal_information": {
                    "name": "name_test_af",
                    "postal_code": "postal_code_test_af",
                    "address": "address_test_af",
                    "email": "email_test_af",
                    "birth": "birth_test_af",
                    "is_corporate": True,
                    "tax_category": 20,
                }
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }

    # <Error_3>
    # 404: Issuer does not exist
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        async_db.add(_account)
        await async_db.commit()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address, 1),
            json={
                "personal_information": {
                    "name": "name_test_af",
                    "postal_code": "postal_code_test_af",
                    "address": "address_test_af",
                    "email": "email_test_af",
                    "birth": "birth_test_af",
                    "is_corporate": True,
                    "tax_category": 20,
                }
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "child account does not exist",
        }

    # <Error_4>
    # PersonalInfoExceedsSizeLimit
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        async_db.add(_account)

        _child_account = ChildAccount()
        _child_account.issuer_address = self.issuer_address
        _child_account.child_account_index = 1
        _child_account.child_account_address = self.child_account_address
        async_db.add(_child_account)

        _off_personal_info = IDXPersonalInfo()
        _off_personal_info.issuer_address = self.issuer_address
        _off_personal_info.account_address = self.child_account_address
        _off_personal_info.personal_info = {
            "key_manager": "SELF",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
            "tax_category": 10,
        }
        _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
        async_db.add(_off_personal_info)

        await async_db.commit()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address, 1),
            json={
                "personal_information": {
                    "name": "name_test",
                    "postal_code": "postal_code_test",
                    "address": "address_test" * 100,  # Too long value
                    "email": "email_test",
                    "birth": "birth_test",
                    "is_corporate": False,
                    "tax_category": 10,
                }
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 11, "title": "PersonalInfoExceedsSizeLimit"},
            "detail": "",
        }
