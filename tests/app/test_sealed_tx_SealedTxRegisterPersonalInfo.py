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
from sqlalchemy import select

from app.model.db import (
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
)
from tests.app.utils.generate_signature import generate_sealed_tx_signature


class TestSealedTxRegisterPersonalInfo:
    test_issuer_address = "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6"

    test_account_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    test_account_pk = "0000000000000000000000000000000000000000000000000000000000000001"

    # Target API endpoint
    url = "/sealed_tx/personal_info"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Register personal information
    @pytest.mark.freeze_time("2024-09-30 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        # Derive a signature
        _params = {
            "link_address": self.test_issuer_address,
            "personal_information": {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            },
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = await async_client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _personal_info = (
            await async_db.scalars(select(IDXPersonalInfo).limit(1))
        ).first()
        assert _personal_info.issuer_address == self.test_issuer_address
        assert _personal_info.account_address == self.test_account_address
        assert _personal_info.personal_info == {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert _personal_info.data_source == PersonalInfoDataSource.OFF_CHAIN

        _history = (
            await async_db.scalars(select(IDXPersonalInfoHistory).limit(1))
        ).first()
        assert _history.issuer_address == self.test_issuer_address
        assert _history.account_address == self.test_account_address
        assert _history.event_type == PersonalInfoEventType.REGISTER
        assert _history.personal_info == {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert _history.block_timestamp == datetime.datetime(2024, 9, 30, 12, 34, 56)

    # <Normal_1_2>
    # Blank personal information
    @pytest.mark.freeze_time("2024-09-30 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        # Derive a signature
        _params = {
            "link_address": self.test_issuer_address,
            "personal_information": {"key_manager": "test_key_manager"},
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = await async_client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _personal_info = (
            await async_db.scalars(select(IDXPersonalInfo).limit(1))
        ).first()
        assert _personal_info.issuer_address == self.test_issuer_address
        assert _personal_info.account_address == self.test_account_address
        assert _personal_info.personal_info == {
            "key_manager": "test_key_manager",
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        assert _personal_info.data_source == PersonalInfoDataSource.OFF_CHAIN

        _history = (
            await async_db.scalars(select(IDXPersonalInfoHistory).limit(1))
        ).first()
        assert _history.issuer_address == self.test_issuer_address
        assert _history.account_address == self.test_account_address
        assert _history.event_type == PersonalInfoEventType.REGISTER
        assert _history.personal_info == {
            "key_manager": "test_key_manager",
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        assert _history.block_timestamp == datetime.datetime(2024, 9, 30, 12, 34, 56)

    # <Normal_2>
    # Overwrite the already registered personal information
    @pytest.mark.freeze_time("2024-09-30 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        _personal_info = IDXPersonalInfo()
        _personal_info.issuer_address = self.test_issuer_address
        _personal_info.account_address = self.test_account_address
        _personal_info.personal_info = {
            "key_manager": "test_key_manager_1",
            "name": "name_test_1",
            "postal_code": "postal_code_test_1",
            "address": "address_test_1",
            "email": "email_test_1",
            "birth": "birth_test_1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN

        # Derive a signature
        _params = {
            "link_address": self.test_issuer_address,
            "personal_information": {
                "key_manager": "test_key_manager_2",
                "name": "test_name_2",
                "postal_code": "test_postal_code_2",
                "address": "test_address_2",
                "email": "test_email_2",
                "birth": "test_birth_2",
                "is_corporate": True,
                "tax_category": 20,
            },
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = await async_client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _personal_info_af = (
            await async_db.scalars(select(IDXPersonalInfo).limit(1))
        ).first()
        assert _personal_info_af.issuer_address == self.test_issuer_address
        assert _personal_info_af.account_address == self.test_account_address
        assert _personal_info_af.personal_info == {
            "key_manager": "test_key_manager_2",
            "name": "test_name_2",
            "postal_code": "test_postal_code_2",
            "address": "test_address_2",
            "email": "test_email_2",
            "birth": "test_birth_2",
            "is_corporate": True,
            "tax_category": 20,
        }
        assert _personal_info_af.data_source == PersonalInfoDataSource.OFF_CHAIN

        _history = (
            await async_db.scalars(select(IDXPersonalInfoHistory).limit(1))
        ).first()
        assert _history.issuer_address == self.test_issuer_address
        assert _history.account_address == self.test_account_address
        assert _history.event_type == PersonalInfoEventType.REGISTER
        assert _history.personal_info == {
            "key_manager": "test_key_manager_2",
            "name": "test_name_2",
            "postal_code": "test_postal_code_2",
            "address": "test_address_2",
            "email": "test_email_2",
            "birth": "test_birth_2",
            "is_corporate": True,
            "tax_category": 20,
        }
        assert _history.block_timestamp == datetime.datetime(2024, 9, 30, 12, 34, 56)

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # Missing X-SealedTx-Signature header
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        _params = {
            "link_address": self.test_issuer_address,
            "personal_information": {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            },
        }

        # Call API
        resp = await async_client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "X-SealedTx-Signature"],
                    "msg": "Field required",
                    "input": None,
                }
            ],
        }

    # <Error_2>
    # Missing required field: key_manager
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # Derive a signature
        _params = {
            "link_address": self.test_issuer_address,
            "personal_information": {},
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = await async_client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "personal_information", "key_manager"],
                    "msg": "Field required",
                    "input": {},
                }
            ],
        }
