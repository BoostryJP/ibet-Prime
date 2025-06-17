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

import base64
from unittest import mock

import pytest
from sqlalchemy import select

from app.model.db import FreezeLogAccount, TransactionLock
from app.utils.e2ee_utils import E2EEUtils
from config import EOA_PASSWORD_PATTERN_MSG


class TestCreateFreezeLogAccount:
    # Target API endpoint
    test_url = "/freeze_log/accounts"

    valid_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 *+.\\()?[]^$-|!#%&\"',/:;<=>@_`{}~"
    invalid_password = "password🚀"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Use Linux RNG
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db, ibet_freeze_log_contract):
        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            ibet_freeze_log_contract.address,
        ):
            req_param = {"eoa_password": E2EEUtils.encrypt(self.valid_password)}
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        log_account = (
            await async_db.scalars(select(FreezeLogAccount).limit(1))
        ).first()
        assert log_account is not None

        tx_lock = (
            await async_db.scalars(
                select(TransactionLock)
                .where(TransactionLock.tx_from == log_account.account_address)
                .limit(1)
            )
        ).first()
        assert tx_lock is not None

        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": log_account.account_address,
            "is_deleted": log_account.is_deleted,
        }

    # <Normal_2>
    # Use AWS RNG
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db, ibet_freeze_log_contract):
        # Mock setting
        class KMSClientMock:
            def generate_random(self, NumberOfBytes):
                assert NumberOfBytes == 32
                return {"Plaintext": b"12345678901234567890123456789012"}

        mock_boto3_client = mock.patch(
            target="boto3.client", side_effect=[KMSClientMock()]
        )

        # Request target api
        with (
            mock.patch(
                "app.routers.misc.freeze_log.AWS_KMS_GENERATE_RANDOM_ENABLED", True
            ),
            mock.patch(
                "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
                ibet_freeze_log_contract.address,
            ),
            mock_boto3_client,
        ):
            req_param = {"eoa_password": E2EEUtils.encrypt(self.valid_password)}
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        log_account = (
            await async_db.scalars(select(FreezeLogAccount).limit(1))
        ).first()
        assert log_account is not None

        tx_lock = (
            await async_db.scalars(
                select(TransactionLock)
                .where(TransactionLock.tx_from == log_account.account_address)
                .limit(1)
            )
        ).first()
        assert tx_lock is not None

        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": log_account.account_address,
            "is_deleted": log_account.is_deleted,
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    # Missing required field
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db, ibet_freeze_log_contract):
        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            ibet_freeze_log_contract.address,
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
                    "loc": ["body", "eoa_password"],
                    "msg": "Field required",
                    "input": {},
                }
            ],
        }

    # <Error_2>
    # Parameter Error
    # Not encrypted password
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db, ibet_freeze_log_contract):
        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            ibet_freeze_log_contract.address,
        ):
            req_param = {
                "eoa_password": base64.encodebytes(
                    "password".encode("utf-8")
                ).decode(),  # Not encrypted
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
                    "input": "cGFzc3dvcmQ=\n",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_3>
    # Password policy violation
    # -> InvalidParameterError
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db, ibet_freeze_log_contract):
        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            ibet_freeze_log_contract.address,
        ):
            req_param = {"eoa_password": E2EEUtils.encrypt(self.invalid_password)}
            resp = await async_client.post(self.test_url, json=req_param)

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": EOA_PASSWORD_PATTERN_MSG,
        }
