from app.model.db import AccountRsaStatus
from app.utils.e2ee_utils import E2EEUtils

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

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.db import Account
from tests.account_config import default_eth_account


class TestRetrieveIssuer:
    # target API endpoint
    base_url = "/accounts/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # rsa_public_key is None
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client: AsyncClient, async_db: AsyncSession):
        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        # prepare data
        account = Account()
        account.eoa_password = E2EEUtils.encrypt("password")
        account.is_deleted = False
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.rsa_status = AccountRsaStatus.UNSET.value
        async_db.add(account)
        await async_db.commit()

        resp = await async_client.get(self.base_url.format(_admin_address))

        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _admin_account["address"],
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.UNSET.value,
            "is_deleted": False,
        }

    # <Normal_2>
    # rsa_public_key is not None
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client: AsyncClient, async_db: AsyncSession):
        _admin_account = default_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]
        _admin_rsa_public_key = _admin_account["rsa_public_key"]

        # prepare data
        account = Account()
        account.eoa_password = E2EEUtils.encrypt("password")
        account.is_deleted = False
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.rsa_public_key = _admin_rsa_public_key
        account.rsa_status = AccountRsaStatus.CHANGING.value
        async_db.add(account)
        await async_db.commit()

        resp = await async_client.get(self.base_url.format(_admin_address))

        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _admin_account["address"],
            "rsa_public_key": _admin_account["rsa_public_key"],
            "rsa_status": AccountRsaStatus.CHANGING.value,
            "is_deleted": False,
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # No data
    @pytest.mark.asyncio
    async def test_error_1(self, async_client: AsyncClient, async_db: AsyncSession):
        resp = await async_client.get(
            self.base_url.format("non_existent_issuer_address")
        )

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }
