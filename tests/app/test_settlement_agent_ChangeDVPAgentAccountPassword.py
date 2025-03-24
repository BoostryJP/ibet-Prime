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

from app.model.db import DVPAgentAccount
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestChangeDVPAgentAccountPassword:
    # Target API endpoint
    base_url = "/settlement/dvp/agent/account/{account_address}/eoa_password"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_password = "password"
        new_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 *+.\\()?[]^$-|!#%&\"',/:;<=>@_`{}~"

        # Prepare data
        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = user_address_1
        dvp_agent_account.keyfile = user_keyfile_1
        dvp_agent_account.eoa_password = E2EEUtils.encrypt(old_password)
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # Request target api
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(old_password),
            "eoa_password": E2EEUtils.encrypt(new_password),
        }
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # Assertion
        assert resp.status_code == 200

        dvp_agent_account_af = (
            await async_db.scalars(
                select(DVPAgentAccount)
                .where(DVPAgentAccount.account_address == user_address_1)
                .limit(1)
            )
        ).first()
        assert E2EEUtils.decrypt(dvp_agent_account_af.eoa_password) == new_password

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Missing required fields
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]

        # Request target api
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "old_eoa_password"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "eoa_password"],
                    "msg": "Field required",
                    "input": {},
                },
            ],
        }

    # <Error_2>
    # Password is not encrypted
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]

        # Request target api
        req_param = {
            "old_eoa_password": "raw_password",
            "eoa_password": "raw_password",
        }
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "old_eoa_password"],
                    "msg": "Value error, old_eoa_password is not a Base64-encoded encrypted data",
                    "input": "raw_password",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "eoa_password"],
                    "msg": "Value error, eoa_password is not a Base64-encoded encrypted data",
                    "input": "raw_password",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_3>
    # Log account is not exists
    # -> NotFound
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        old_password = "password"
        new_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 *+.\\()?[]^$-|!#%&\"',/:;<=>@_`{}~"

        # Request target api
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(old_password),
            "eoa_password": E2EEUtils.encrypt(new_password),
        }
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "account is not exists",
        }

    # <Error_4>
    # New password violates password policy
    # -> InvalidParameterError
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_password = "password"
        new_password = "password🚀"

        # Prepare data
        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = user_address_1
        dvp_agent_account.keyfile = user_keyfile_1
        dvp_agent_account.eoa_password = E2EEUtils.encrypt(old_password)
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # Request target api
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(old_password),
            "eoa_password": E2EEUtils.encrypt(new_password),
        }
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "password must be 8 to 200 alphanumeric or symbolic character",
        }
