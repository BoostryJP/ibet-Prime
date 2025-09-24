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

import eth_keyfile
import pytest
from sqlalchemy import select

from app.model.db import Account, AccountRsaStatus
from app.model.ibet import IbetStraightBondContract
from app.utils.e2ee_utils import E2EEUtils
from config import EOA_PASSWORD_PATTERN_MSG
from tests.account_config import default_eth_account


class TestChangeIssuerEOAPassword:
    # target API endpoint
    base_url = "/accounts/{}/eoa_password"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        _account = default_eth_account("user1")
        _issuer_address = _account["address"]
        _old_keyfile = _account["keyfile_json"]
        _old_password = "password"
        _new_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 *+.\\()?[]^$-|!#%&\"',/:;<=>@_`{}~"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _old_keyfile
        account.eoa_password = E2EEUtils.encrypt(_old_password)
        account.rsa_status = AccountRsaStatus.UNSET.value
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(_old_password),
            "eoa_password": E2EEUtils.encrypt(_new_password),
        }
        resp = await async_client.post(
            self.base_url.format(_issuer_address), json=req_param
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None
        _account = (await async_db.scalars(select(Account).limit(1))).first()
        _account_keyfile = _account.keyfile
        _account_eoa_password = E2EEUtils.decrypt(_account.eoa_password)
        assert _account_keyfile != _old_keyfile
        assert _account_eoa_password == _new_password

        # deploy test
        private_key = eth_keyfile.decode_keyfile_json(
            raw_keyfile_json=_account_keyfile,
            password=_account_eoa_password.encode("utf-8"),
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
            args=arguments, tx_sender=_issuer_address, tx_sender_key=private_key
        )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # parameter error(required body)
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        _account = default_eth_account("user1")
        _issuer_address = _account["address"]

        # request target API
        resp = await async_client.post(self.base_url.format(_issuer_address))

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

    # <Error_2>
    # parameter error(required field)
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        _account = default_eth_account("user1")
        _issuer_address = _account["address"]

        # request target API
        req_param = {
            "dummy": "dummy",
        }
        resp = await async_client.post(
            self.base_url.format(_issuer_address), json=req_param
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": {"dummy": "dummy"},
                    "loc": ["body", "old_eoa_password"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {"dummy": "dummy"},
                    "loc": ["body", "eoa_password"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_3>
    # parameter error(not decrypt)
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        _account = default_eth_account("user1")
        _issuer_address = _account["address"]
        _old_password = "password"
        _new_password = "passwordnew"

        # request target API
        req_param = {
            "old_eoa_password": _old_password,
            "eoa_password": _new_password,
        }
        resp = await async_client.post(
            self.base_url.format(_issuer_address), json=req_param
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

    # <Error_4>
    # No data
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        _old_password = "password"
        _new_password = "passwordnew"

        # request target API
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(_old_password),
            "eoa_password": E2EEUtils.encrypt(_new_password),
        }
        resp = await async_client.post(
            self.base_url.format("non_existent_issuer_address"), json=req_param
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }

    # <Error_5>
    # old password mismatch
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        _account = default_eth_account("user1")
        _issuer_address = _account["address"]
        _old_keyfile = _account["keyfile_json"]
        _old_password = "password"
        _new_password = "passwordnew"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _old_keyfile
        account.eoa_password = E2EEUtils.encrypt(_old_password)
        account.rsa_status = AccountRsaStatus.UNSET.value
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt("passwordtest"),
            "eoa_password": E2EEUtils.encrypt(_new_password),
        }
        resp = await async_client.post(
            self.base_url.format(_issuer_address), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "old password mismatch",
        }

    # <Error_6>
    # password policy
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        _account = default_eth_account("user1")
        _issuer_address = _account["address"]
        _old_keyfile = _account["keyfile_json"]
        _old_password = "password"
        _new_password = "password🚀"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _old_keyfile
        account.eoa_password = E2EEUtils.encrypt(_old_password)
        account.rsa_status = AccountRsaStatus.UNSET.value
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "old_eoa_password": E2EEUtils.encrypt(_old_password),
            "eoa_password": E2EEUtils.encrypt(_new_password),
        }
        resp = await async_client.post(
            self.base_url.format(_issuer_address), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": EOA_PASSWORD_PATTERN_MSG,
        }
