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
from sqlalchemy import select

from app.model.db import Account, AccountRsaStatus
from tests.account_config import config_eth_account


class TestDeleteIssuer:
    # target API endpoint
    base_url = "/accounts/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        async_db.add(account)
        await async_db.commit()

        # request target API
        resp = await async_client.delete(self.base_url.format(_admin_address))

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _admin_account["address"],
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.UNSET.value,
            "is_deleted": True,
        }
        _account_after = (await async_db.scalars(select(Account).limit(1))).first()
        assert _account_after.issuer_address == _admin_account["address"]
        assert _account_after.is_deleted == True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # No data
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # request target api
        resp = await async_client.delete(
            self.base_url.format("non_existent_issuer_address")
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }
