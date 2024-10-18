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

from app.model.db import FreezeLogAccount
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestRetrieveFreezeLog:
    # Target API endpoint
    new_log_url = "/freeze_log/logs"
    get_log_url = "/freeze_log/logs/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db, freeze_log_contract):
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

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Get log
            resp = client.get(
                self.get_log_url.format(log_index),
                params={"account_address": user_address_1},
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "block_number": 2,
            "freezing_grace_block_count": 10,
            "log_message": "test_message",
        }

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

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Get log
            resp = client.get(self.get_log_url.format(log_index), params={})

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["query", "account_address"],
                    "msg": "Field required",
                    "input": {},
                }
            ],
        }

    # <Error_1_2>
    # Missing required fields
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

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Record new log
            resp_new = client.post(
                self.new_log_url,
                json={
                    "account_address": user_address_1,
                    "eoa_password": E2EEUtils.encrypt(password),
                    "log_message": "test_message",
                    "freezing_grace_block_count": 10,
                },
            )
            log_index = resp_new.json()["log_index"]
            # Get log
            resp = client.get(
                self.get_log_url.format(log_index),
                params={
                    "account_address": "invalid_address"
                },  # Invalid ethereum address
            )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["query", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
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

        # Request target api
        with mock.patch(
            "app.routers.misc.freeze_log.FREEZE_LOG_CONTRACT_ADDRESS",
            freeze_log_contract.address,
        ):
            # Get log
            resp = client.get(
                self.get_log_url.format(0), params={"account_address": user_address_1}
            )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "account is not exists",
        }
