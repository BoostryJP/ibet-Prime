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

import asyncio
import logging
import secrets

import pytest
from coincurve import PublicKey
from eth_utils import keccak, to_checksum_address
from sqlalchemy import select

from app.model.db import (
    Account,
    ChildAccount,
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
    TmpChildAccountBatchCreate,
)
from batch.processor_batch_create_child_account import LOG, Processor


@pytest.fixture(scope="function")
def processor(async_db):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True

    yield Processor(is_shutdown=asyncio.Event())

    log.propagate = False
    log.setLevel(default_log_level)


class TestProcessor:
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

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, async_db, caplog):
        # Prepare data
        for i in range(3):
            _tmp_data = TmpChildAccountBatchCreate()
            _tmp_data.issuer_address = self.issuer_address
            _tmp_data.child_account_index = i + 1
            _tmp_data.personal_info = {
                "key_manager": "SELF",
                "name": f"name_test_{i}",
                "postal_code": f"postal_code_test_{i}",
                "address": f"address_test_{i}",
                "email": f"email_test_{i}",
                "birth": f"birth_test_{i}",
                "is_corporate": False,
                "tax_category": i,
            }
            async_db.add(_tmp_data)

        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        async_db.add(_account)

        await async_db.commit()

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        tmp_list = (await async_db.scalars(select(TmpChildAccountBatchCreate))).all()
        assert len(tmp_list) == 0

        child_account_list = (
            await async_db.scalars(select(ChildAccount).order_by(ChildAccount.created))
        ).all()
        assert len(child_account_list) == 3
        assert child_account_list[0].issuer_address == self.issuer_address
        assert child_account_list[0].child_account_index == 1
        assert child_account_list[0].child_account_address == self.child_1_address

        off_personal_info = (
            await async_db.scalars(
                select(IDXPersonalInfo).where(
                    IDXPersonalInfo.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(off_personal_info) == 3
        assert off_personal_info[0].issuer_address == self.issuer_address
        assert off_personal_info[0].account_address == self.child_1_address
        assert off_personal_info[0].personal_info == {
            "key_manager": "SELF",
            "name": "name_test_0",
            "postal_code": "postal_code_test_0",
            "address": "address_test_0",
            "email": "email_test_0",
            "birth": "birth_test_0",
            "is_corporate": False,
            "tax_category": 0,
        }
        assert off_personal_info[0].data_source == PersonalInfoDataSource.OFF_CHAIN

        personal_info_history = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory).where(
                    IDXPersonalInfoHistory.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(personal_info_history) == 3
        assert personal_info_history[0].issuer_address == self.issuer_address
        assert personal_info_history[0].account_address == self.child_1_address
        assert personal_info_history[0].event_type == PersonalInfoEventType.REGISTER
        assert (
            personal_info_history[0].personal_info == off_personal_info[0].personal_info
        )
        assert personal_info_history[0].block_timestamp is not None

        assert caplog.messages == ["Process Start", "Process End"]

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Issuer account not found
    # - Account is None
    @pytest.mark.asyncio
    async def test_error_1_1(self, processor, async_db, caplog):
        # Prepare data
        _tmp_data = TmpChildAccountBatchCreate()
        _tmp_data.issuer_address = self.issuer_address
        _tmp_data.child_account_index = 1
        _tmp_data.personal_info = {
            "key_manager": "SELF",
            "name": "name_test_1",
            "postal_code": "postal_code_test_1",
            "address": "address_test_1",
            "email": "email_test_1",
            "birth": "birth_test_1",
            "is_corporate": False,
            "tax_category": 1,
        }
        async_db.add(_tmp_data)

        await async_db.commit()

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        tmp_list = (await async_db.scalars(select(TmpChildAccountBatchCreate))).all()
        assert len(tmp_list) == 0

        child_account_list = (
            await async_db.scalars(select(ChildAccount).order_by(ChildAccount.created))
        ).all()
        assert len(child_account_list) == 0

        off_personal_info = (
            await async_db.scalars(
                select(IDXPersonalInfo).where(
                    IDXPersonalInfo.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(off_personal_info) == 0

        personal_info_history = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory).where(
                    IDXPersonalInfoHistory.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(personal_info_history) == 0

        assert caplog.messages == [
            "Process Start",
            f"Issuer account not found: {self.issuer_address}",
            "Process End",
        ]

    # <Error_1_2>
    # Issuer account not found
    # - Account.public_key is None
    @pytest.mark.asyncio
    async def test_error_1_2(self, processor, async_db, caplog):
        # Prepare data
        _tmp_data = TmpChildAccountBatchCreate()
        _tmp_data.issuer_address = self.issuer_address
        _tmp_data.child_account_index = 1
        _tmp_data.personal_info = {
            "key_manager": "SELF",
            "name": "name_test_1",
            "postal_code": "postal_code_test_1",
            "address": "address_test_1",
            "email": "email_test_1",
            "birth": "birth_test_1",
            "is_corporate": False,
            "tax_category": 1,
        }
        async_db.add(_tmp_data)

        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = None
        async_db.add(_account)

        await async_db.commit()

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        tmp_list = (await async_db.scalars(select(TmpChildAccountBatchCreate))).all()
        assert len(tmp_list) == 0

        child_account_list = (
            await async_db.scalars(select(ChildAccount).order_by(ChildAccount.created))
        ).all()
        assert len(child_account_list) == 0

        off_personal_info = (
            await async_db.scalars(
                select(IDXPersonalInfo).where(
                    IDXPersonalInfo.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(off_personal_info) == 0

        personal_info_history = (
            await async_db.scalars(
                select(IDXPersonalInfoHistory).where(
                    IDXPersonalInfoHistory.issuer_address == self.issuer_address
                )
            )
        ).all()
        assert len(personal_info_history) == 0

        assert caplog.messages == [
            "Process Start",
            f"Issuer account not found: {self.issuer_address}",
            "Process End",
        ]
