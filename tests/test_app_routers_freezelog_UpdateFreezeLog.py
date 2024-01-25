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


class TestUpdateFreezeLog:
    # Target API endpoint
    new_log_url = "/freeze_log/logs"
    update_log_url = "/freeze_log/logs/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        db.add(log_account)

        db.commit()

        with mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_before",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Update log
            resp = client.post(
                self.update_log_url.format(log_index),
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_after",
                },
            )

        # Assertion
        assert resp.status_code == 200

        _, _, log_message_af = await FreezeLogContract(
            log_account, freeze_log_contract.address
        ).get_log(
            log_index=log_index,
        )
        assert log_message_af == "test_message_after"

    # <Normal_2>
    # E2EE_REQUEST_ENABLED = False
    @pytest.mark.asyncio
    async def test_normal_2(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        db.add(log_account)

        db.commit()

        with mock.patch(
            "app.routers.freeze_log.E2EE_REQUEST_ENABLED",
            False,
        ), mock.patch(
            "app.model.schema.freeze_log.E2EE_REQUEST_ENABLED",
            False,
        ), mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": password,
                    "log_message": "test_message_before",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Update log
            resp = client.post(
                self.update_log_url.format(log_index),
                json={
                    "account_address": user_address_1,
                    "eoa_password": password,
                    "log_message": "test_message_after",
                },
            )

        # Assertion
        assert resp.status_code == 200

        _, _, log_message_af = await FreezeLogContract(
            log_account, freeze_log_contract.address
        ).get_log(
            log_index=log_index,
        )
        assert log_message_af == "test_message_after"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Missing required fields
    # -> RequestValidationError
    def test_error_1_1(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        db.add(log_account)

        db.commit()

        with mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_before",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Update log
            resp = client.post(
                self.update_log_url.format(log_index),
                json={},
            )

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
            ],
        }

    # <Error_1_2>
    # Invalid ethereum address: account_address
    # -> RequestValidationError
    def test_error_1_2(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        db.add(log_account)

        db.commit()

        with mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_before",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Update log
            resp = client.post(
                self.update_log_url.format(log_index),
                json={
                    "account_address": "invalid address",  # invalid ethereum address
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_after",
                },
            )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid address",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_1_3>
    # Password is not encrypted
    # -> RequestValidationError
    def test_error_1_3(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        db.add(log_account)

        db.commit()

        with mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_before",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Update log
            resp = client.post(
                self.update_log_url.format(log_index),
                json={
                    "account_address": user_address_1,
                    "eoa_password": password,  # Not encrypted
                    "log_message": "test_message_after",
                },
            )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "eoa_password"],
                    "msg": "Value error, eoa_password is not a Base64-encoded encrypted data",
                    "input": "password",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_2>
    # Log account is not exists
    # -> NotFound
    def test_error_2(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        password = "password"

        with mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Update log
            resp = client.post(
                self.update_log_url.format(0),
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_after",
                },
            )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "account is not exists",
        }

    # <Error_3>
    # Password mismatch
    # -> InvalidParameterError
    def test_error_3(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        db.add(log_account)

        db.commit()

        with mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Update log
            resp = client.post(
                self.update_log_url.format(0),
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt("invalid password"),
                    "log_message": "test_message_after",
                },
            )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "password mismatch",
        }

    # <Error_4>
    # SendTransactionError
    def test_error_4(self, client, db, freeze_log_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        password = "password"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = user_address_1
        log_account.keyfile = user_keyfile_1
        log_account.eoa_password = E2EEUtils.encrypt(password)
        db.add(log_account)

        db.commit()

        with mock.patch(
            "app.utils.contract_utils.AsyncContractUtils.send_transaction",
            MagicMock(side_effect=Exception("tx error")),
        ), mock.patch(
            "app.routers.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Update log
            resp = client.post(
                self.update_log_url.format(0),
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message_after",
                },
            )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to update log",
        }
