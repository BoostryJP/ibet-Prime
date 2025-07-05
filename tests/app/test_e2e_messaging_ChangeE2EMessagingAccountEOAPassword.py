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
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select

from app.model.db import E2EMessagingAccount
from app.model.ibet import IbetStraightBondContract
from app.utils.e2ee_utils import E2EEUtils
from config import EOA_PASSWORD_PATTERN_MSG
from tests.account_config import default_eth_account


class TestChangeE2EMessagingAccountEOAPassword:
    # target API endpoint
    base_url = "/e2e_messaging/accounts/{account_address}/eoa_password"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db, ibet_e2e_messaging_contract):
        user_1 = default_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_password = "password"
        new_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 *+.\\()?[]^$-|!#%&\"',/:;<=>@_`{}~"

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt(old_password)
        async_db.add(_account)

        await async_db.commit()

        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(old_password),
            "eoa_password": E2EEUtils.encrypt(new_password),
        }
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None
        _account = (
            await async_db.scalars(select(E2EMessagingAccount).limit(1))
        ).first()
        assert _account.keyfile != user_keyfile_1
        assert E2EEUtils.decrypt(_account.eoa_password) == new_password

        # test new keyfile
        private_key = decode_keyfile_json(
            raw_keyfile_json=_account.keyfile, password=new_password.encode("utf-8")
        )
        arguments = [
            "name_test",
            "symbol_test",
            10,
            20,
            "JPY",
            "redemption_date_test",
            30,
            "JPY",
            "return_date_test",
            "return_amount_test",
            "purpose_test",
        ]
        await IbetStraightBondContract().create(
            args=arguments, tx_sender=user_address_1, tx_sender_key=private_key
        )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Parameter Error
    # no body
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        resp = await async_client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            )
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # <Error_1_2>
    # Parameter Error
    # no required field
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": {},
                    "loc": ["body", "old_eoa_password"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["body", "eoa_password"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_1_3>
    # Parameter Error
    # not decrypt
    @pytest.mark.asyncio
    async def test_error_1_3(self, async_client, async_db):
        old_password = "password"
        new_password = "passwordnew"
        req_param = {
            "old_eoa_password": old_password,
            "eoa_password": new_password,
        }
        resp = await async_client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": "password",
                    "loc": ["body", "old_eoa_password"],
                    "msg": "Value error, old_eoa_password is not a Base64-encoded "
                    "encrypted data",
                    "type": "value_error",
                },
                {
                    "ctx": {"error": {}},
                    "input": "passwordnew",
                    "loc": ["body", "eoa_password"],
                    "msg": "Value error, eoa_password is not a Base64-encoded "
                    "encrypted data",
                    "type": "value_error",
                },
            ],
        }

    # <Error_2>
    # No data
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        old_password = "password"
        new_password = "passwordnew"
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(old_password),
            "eoa_password": E2EEUtils.encrypt(new_password),
        }
        resp = await async_client.post(
            self.base_url.format(
                account_address="0x1234567890123456789012345678900000000000"
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "e2e messaging account is not exists",
        }

    # <Error_3>
    # old password mismatch
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db, ibet_e2e_messaging_contract):
        user_1 = default_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_password = "password"
        new_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 *+.\\()?[]^$-|!#%&\"',/:;<=>@_`{}~"

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt(old_password)
        async_db.add(_account)

        await async_db.commit()

        req_param = {
            "old_eoa_password": E2EEUtils.encrypt("passwordtest"),
            "eoa_password": E2EEUtils.encrypt(new_password),
        }
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "old password mismatch",
        }

    # <Error_4>
    # Passphrase Policy Violation
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db, ibet_e2e_messaging_contract):
        user_1 = default_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        old_password = "password"
        new_password = "password🚀"

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt(old_password)
        async_db.add(_account)

        await async_db.commit()

        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(old_password),
            "eoa_password": E2EEUtils.encrypt(new_password),
        }
        resp = await async_client.post(
            self.base_url.format(account_address=user_address_1), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": EOA_PASSWORD_PATTERN_MSG,
        }
