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
import secrets

import pytest
from coincurve import PublicKey
from eth_utils import keccak, to_checksum_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.model.db import (
    Account,
    ChildAccount,
    ChildAccountIndex,
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
)
from config import ASYNC_DATABASE_URL


class TestCreateChildAccount:
    sk_1 = secrets.token_bytes(32)
    pk_1 = PublicKey.from_valid_secret(sk_1)

    issuer_pub_key = pk_1.format().hex()
    issuer_address = to_checksum_address(
        keccak(pk_1.format(compressed=False)[1:])[-20:]
    )

    index = 1
    sk_2 = int(index).to_bytes(32)
    pk_2 = PublicKey.from_valid_secret(sk_2)

    child_1_pub_key = PublicKey.combine_keys([pk_1, pk_2])
    child_1_address = to_checksum_address(
        keccak(child_1_pub_key.format(compressed=False)[1:])[-20:]
    )

    # Target API endpoint
    base_url = "/accounts/{}/child_accounts"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_0>
    # Verify the deterministic wallet
    @pytest.mark.asyncio
    async def test_normal_0(self, async_client, async_db):
        # Generate a child public key from two private keys.
        child_sk_1 = ((int.from_bytes(self.sk_1) + self.index) % (2**256)).to_bytes(32)
        child_pk_1 = PublicKey.from_valid_secret(child_sk_1)

        # Generate a child public key from two public keys.
        child_pk_2 = PublicKey.combine_keys([self.pk_1, self.pk_2])

        assert child_pk_1 == child_pk_2

    # <Normal_1_1>
    # Successfully generated the child key
    @pytest.mark.freeze_time("2024-09-28 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        async_db.add(_account)

        _child_index = ChildAccountIndex()
        _child_index.issuer_address = self.issuer_address
        _child_index.next_index = 1
        async_db.add(_child_index)

        await async_db.commit()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address),
            json={
                "personal_information": {
                    "name": "name_test",
                    "postal_code": "postal_code_test",
                    "address": "address_test",
                    "email": "email_test",
                    "birth": "birth_test",
                    "is_corporate": False,
                    "tax_category": 10,
                }
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {"child_account_index": 1}

        _child_account = (
            await async_db.scalars(
                select(ChildAccount).where(
                    ChildAccount.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(_child_account) == 1
        assert _child_account[0].issuer_address == self.issuer_address
        assert _child_account[0].child_account_index == 1
        assert _child_account[0].child_account_address == self.child_1_address

        _child_index = (
            await async_db.scalars(
                select(ChildAccountIndex)
                .where(ChildAccountIndex.issuer_address == self.issuer_address)
                .limit(1)
            )
        ).first()
        assert _child_index.next_index == 2

        _off_personal_info = (
            await async_db.scalars(
                select(IDXPersonalInfo)
                .where(IDXPersonalInfo.issuer_address == self.issuer_address)
                .limit(1)
            )
        ).first()
        assert _off_personal_info.issuer_address == self.issuer_address
        assert (
            _off_personal_info.account_address
            == _child_account[0].child_account_address
        )
        assert _off_personal_info.personal_info == {
            "key_manager": "SELF",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert _off_personal_info.data_source == PersonalInfoDataSource.OFF_CHAIN

        _personal_info_history = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory)
                .where(IDXPersonalInfoHistory.issuer_address == self.issuer_address)
                .limit(1)
            )
        ).first()
        assert _personal_info_history.issuer_address == self.issuer_address
        assert (
            _personal_info_history.account_address
            == _child_account[0].child_account_address
        )
        assert _personal_info_history.event_type == PersonalInfoEventType.REGISTER
        assert _personal_info_history.personal_info == _off_personal_info.personal_info
        assert _personal_info_history.block_timestamp == datetime.datetime(
            2024, 9, 28, 12, 34, 56
        )

    # <Normal_1_2>
    # Personal information is blank
    @pytest.mark.freeze_time("2024-09-28 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        async_db.add(_account)

        _child_index = ChildAccountIndex()
        _child_index.issuer_address = self.issuer_address
        _child_index.next_index = 1
        async_db.add(_child_index)

        await async_db.commit()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address), json={"personal_information": {}}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {"child_account_index": 1}

        _child_account = (
            await async_db.scalars(
                select(ChildAccount).where(
                    ChildAccount.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(_child_account) == 1
        assert _child_account[0].issuer_address == self.issuer_address
        assert _child_account[0].child_account_index == 1
        assert _child_account[0].child_account_address == self.child_1_address

        _child_index = (
            await async_db.scalars(
                select(ChildAccountIndex)
                .where(ChildAccountIndex.issuer_address == self.issuer_address)
                .limit(1)
            )
        ).first()
        assert _child_index.next_index == 2

        _off_personal_info = (
            await async_db.scalars(
                select(IDXPersonalInfo)
                .where(IDXPersonalInfo.issuer_address == self.issuer_address)
                .limit(1)
            )
        ).first()
        assert _off_personal_info.issuer_address == self.issuer_address
        assert (
            _off_personal_info.account_address
            == _child_account[0].child_account_address
        )
        assert _off_personal_info.personal_info == {
            "key_manager": "SELF",
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        assert _off_personal_info.data_source == PersonalInfoDataSource.OFF_CHAIN

        _personal_info_history = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory)
                .where(IDXPersonalInfoHistory.issuer_address == self.issuer_address)
                .limit(1)
            )
        ).first()
        assert _personal_info_history.issuer_address == self.issuer_address
        assert (
            _personal_info_history.account_address
            == _child_account[0].child_account_address
        )
        assert _personal_info_history.event_type == PersonalInfoEventType.REGISTER
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
            self.base_url.format(self.issuer_address), json={}
        )

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
            self.base_url.format(self.issuer_address),
            json={
                "personal_information": {
                    "name": "name_test",
                    "postal_code": "postal_code_test",
                    "address": "address_test",
                    "email": "email_test",
                    "birth": "birth_test",
                    "is_corporate": False,
                    "tax_category": 10,
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
    # OperationNotPermittedForOlderIssuers
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = None  # public-key is not set
        async_db.add(_account)
        await async_db.commit()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address),
            json={
                "personal_information": {
                    "name": "name_test",
                    "postal_code": "postal_code_test",
                    "address": "address_test",
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
            "meta": {"code": 10, "title": "OperationNotPermittedForOlderIssuers"},
            "detail": "",
        }

    # <Error_4>
    # ServiceUnavailableError
    # - Lock timeout for index table
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        async_db.add(_account)

        _child_index = ChildAccountIndex()
        _child_index.issuer_address = self.issuer_address
        _child_index.next_index = 2
        async_db.add(_child_index)

        await async_db.commit()

        # Lock child account index table
        local_session = AsyncSession(
            autocommit=False,
            autoflush=True,
            bind=create_async_engine(
                ASYNC_DATABASE_URL, echo=False, pool_pre_ping=True
            ),
        )
        _child_index = (
            await local_session.scalars(
                select(ChildAccountIndex)
                .where(ChildAccountIndex.issuer_address == self.issuer_address)
                .limit(1)
                .with_for_update(nowait=True)
            )
        ).first()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address),
            json={
                "personal_information": {
                    "name": "name_test",
                    "postal_code": "postal_code_test",
                    "address": "address_test",
                    "email": "email_test",
                    "birth": "birth_test",
                    "is_corporate": False,
                    "tax_category": 10,
                }
            },
        )
        await local_session.rollback()
        await local_session.close()

        # Assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 1, "title": "ServiceUnavailableError"},
            "detail": "Creation of child accounts for this issuer is temporarily unavailable",
        }

    # <Error_5>
    # PersonalInfoExceedsSizeLimit
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        async_db.add(_account)

        _child_index = ChildAccountIndex()
        _child_index.issuer_address = self.issuer_address
        _child_index.next_index = 1
        async_db.add(_child_index)

        await async_db.commit()

        # Call API
        resp = await async_client.post(
            self.base_url.format(self.issuer_address),
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

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 11, "title": "PersonalInfoExceedsSizeLimit"},
            "detail": "",
        }
