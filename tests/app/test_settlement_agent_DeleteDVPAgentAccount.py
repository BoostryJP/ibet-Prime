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

from unittest import mock

import pytest
from sqlalchemy import select

from app.model.db import DVPAgentAccount


class TestDeleteDVPAgentAccount:
    # Target API endpoint
    base_url = "/settlement/dvp/agent/account/{account_address}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # DEDICATED_DVP_AGENT_MODE = False (default)
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        test_account_address = "0x1234567890123456789012345678900000000000"

        # Prepare data
        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = test_account_address
        dvp_agent_account.keyfile = "test_keyfile_0"
        dvp_agent_account.eoa_password = "test_password_0"
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # Request target api
        resp = await async_client.delete(
            self.base_url.format(account_address=test_account_address)
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "is_deleted": True,
        }

        dvp_agent_account_af = (
            await async_db.scalars(
                select(DVPAgentAccount)
                .where(DVPAgentAccount.account_address == test_account_address)
                .limit(1)
            )
        ).first()
        assert dvp_agent_account_af.is_deleted is True

    # <Normal_2>
    # DEDICATED_DVP_AGENT_MODE = True
    @pytest.mark.asyncio
    @mock.patch("app.routers.misc.settlement_agent.DEDICATED_DVP_AGENT_MODE", True)
    @mock.patch(
        "app.routers.misc.settlement_agent.DEDICATED_DVP_AGENT_ID", "test_agent_0"
    )
    async def test_normal_2(self, async_client, async_db):
        test_account_address = "0x1234567890123456789012345678900000000000"

        # Prepare data
        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = test_account_address
        dvp_agent_account.keyfile = "test_keyfile_0"
        dvp_agent_account.eoa_password = "test_password_0"
        dvp_agent_account.dedicated_agent_id = "test_agent_0"
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # Request target api
        resp = await async_client.delete(
            self.base_url.format(account_address=test_account_address)
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "is_deleted": True,
        }

        dvp_agent_account_af = (
            await async_db.scalars(
                select(DVPAgentAccount)
                .where(DVPAgentAccount.account_address == test_account_address)
                .limit(1)
            )
        ).first()
        assert dvp_agent_account_af.is_deleted is True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        test_account_address = "0x1234567890123456789012345678900000000000"

        # Request target api
        resp = await async_client.delete(
            self.base_url.format(account_address=test_account_address)
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "account is not exists",
        }
