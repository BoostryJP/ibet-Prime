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
from unittest.mock import MagicMock

import pytest

from app.model.blockchain import FreezeLogContract
from app.model.db import FreezeLogAccount
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestRecordNewFreezeLog:
    # Target API endpoint
    test_url = "/freeze_log/logs"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        async_db.add(log_account)

        await async_db.commit()

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            req_param = {
                "account_address": user_address_1,
                "eoa_password": E2EEUtils.encrypt(password),
                "log_message": "test_message",
                "freezing_grace_block_count": 10,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {"log_index": 0}

        _, freezing_grace_block_count, log_message = await FreezeLogContract(
            log_account, freeze_log_contract.address
        ).get_log(
            log_index=0,
        )
        assert freezing_grace_block_count == 10
        assert log_message == "test_message"

    # <Normal_2>
    # E2EE_REQUEST_ENABLED = False
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        async_db.add(log_account)

        await async_db.commit()

        # Request target api
        with (
            mock.patch(
                "app.routers.misc.freeze_log.E2EE_REQUEST_ENABLED",
                False,
            ),
            mock.patch(
                "app.model.schema.freeze_log.E2EE_REQUEST_ENABLED",
                False,
            ),
            mock.patch(
                "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
                freeze_log_contract.address,
            ),
        ):
            req_param = {
                "account_address": user_address_1,
                "eoa_password": password,
                "log_message": "test_message",
                "freezing_grace_block_count": 10,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {"log_index": 0}

        _, freezing_grace_block_count, log_message = await FreezeLogContract(
            log_account, freeze_log_contract.address
        ).get_log(
            log_index=0,
        )
        assert freezing_grace_block_count == 10
        assert log_message == "test_message"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Missing required fields
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db, freeze_log_contract):
        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            req_param = {}
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "account_address"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "eoa_password"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "log_message"],
                    "msg": "Field required",
                    "input": {},
                },
                {
                    "type": "missing",
                    "loc": ["body", "freezing_grace_block_count"],
                    "msg": "Field required",
                    "input": {},
                },
            ],
        }

    # <Error_1_2>
    # Invalid ethereum address: account_address
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db, freeze_log_contract):
        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            req_param = {
                "account_address": "invalid_address",
                "eoa_password": E2EEUtils.encrypt("password"),
                "log_message": "test_message",
                "freezing_grace_block_count": 10,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_1_3>
    # Input should be positive integer: freezing_grace_block_count
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_3(self, async_client, async_db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        async_db.add(log_account)

        await async_db.commit()

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            req_param = {
                "account_address": user_address_1,
                "eoa_password": E2EEUtils.encrypt(password),
                "log_message": "test_message",
                "freezing_grace_block_count": 0,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "greater_than",
                    "loc": ["body", "freezing_grace_block_count"],
                    "msg": "Input should be greater than 0",
                    "input": 0,
                    "ctx": {"gt": 0},
                }
            ],
        }

    # <Error_1_4>
    # Password is not encrypted
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_4(self, async_client, async_db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        async_db.add(log_account)

        await async_db.commit()

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            req_param = {
                "account_address": user_address_1,
                "eoa_password": "raw password",
                "log_message": "test_message",
                "freezing_grace_block_count": 10,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "eoa_password"],
                    "msg": "Value error, eoa_password is not a Base64-encoded encrypted data",
                    "input": "raw password",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_2>
    # Log account is not exists
    # -> NotFound
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        password = "password"

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            req_param = {
                "account_address": user_address_1,
                "eoa_password": E2EEUtils.encrypt(password),
                "log_message": "test_message",
                "freezing_grace_block_count": 10,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "account is not exists",
        }

    # <Error_3>
    # Password mismatch
    # -> InvalidParameterError
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        async_db.add(log_account)

        await async_db.commit()

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            req_param = {
                "account_address": user_address_1,
                "eoa_password": E2EEUtils.encrypt("invalid password"),
                "log_message": "test_message",
                "freezing_grace_block_count": 10,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "password mismatch",
        }

    # <Error_4>
    # SendTransactionError
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        async_db.add(log_account)

        await async_db.commit()

        # Request target api
        with (
            mock.patch(
                "app.utils.contract_utils.AsyncContractUtils.send_transaction",
                MagicMock(side_effect=Exception("tx error")),
            ),
            mock.patch(
                "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
                freeze_log_contract.address,
            ),
        ):
            req_param = {
                "account_address": user_address_1,
                "eoa_password": E2EEUtils.encrypt("password"),
                "log_message": "test_message",
                "freezing_grace_block_count": 10,
            }
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to record log",
        }
