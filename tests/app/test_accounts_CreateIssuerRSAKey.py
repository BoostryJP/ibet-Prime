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

from app.model.db import Account, AccountRsaKeyTemporary, AccountRsaStatus
from app.utils.e2ee_utils import E2EEUtils
from config import (
    PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE,
    PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG,
    ZERO_ADDRESS,
)
from tests.account_config import config_eth_account


class TestCreateIssuerRSAKey:
    # target API endpoint
    base_url = "/accounts/{}/rsakey"

    valid_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 *+.\\()?[]^$-|!#%&\"',/:;<=>@_`{}~"
    invalid_password = "password🚀"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # RSA Create
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        _user_1 = config_eth_account("user1")

        _account_before = Account()
        _account_before.issuer_address = _user_1["address"]
        _account_before.keyfile = _user_1["keyfile_json"]
        eoa_password = E2EEUtils.encrypt("password")
        _account_before.eoa_password = eoa_password
        _account_before.rsa_status = AccountRsaStatus.UNSET.value
        async_db.add(_account_before)

        await async_db.commit()

        password = self.valid_password
        req_param = {"rsa_passphrase": E2EEUtils.encrypt(password)}

        resp = await async_client.post(
            self.base_url.format(_user_1["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _user_1["address"],
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.CREATING.value,
            "is_deleted": False,
        }
        _account_after = (await async_db.scalars(select(Account).limit(1))).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.eoa_password == eoa_password
        assert _account_after.rsa_private_key is None
        assert _account_after.rsa_public_key is None
        assert E2EEUtils.decrypt(_account_after.rsa_passphrase) == password
        assert _account_after.rsa_status == AccountRsaStatus.CREATING.value

    # <Normal_2>
    # RSA Change
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        _user_1 = config_eth_account("user1")
        _user_2 = config_eth_account("user2")

        _account_before = Account()
        _account_before.issuer_address = _user_1["address"]
        _account_before.keyfile = _user_1["keyfile_json"]
        eoa_password = E2EEUtils.encrypt("password")
        _account_before.eoa_password = eoa_password
        _account_before.rsa_private_key = _user_1["rsa_private_key"]
        _account_before.rsa_public_key = _user_1["rsa_public_key"]
        rsa_passphrase = E2EEUtils.encrypt("password")
        _account_before.rsa_passphrase = rsa_passphrase
        _account_before.rsa_status = AccountRsaStatus.SET.value
        async_db.add(_account_before)

        await async_db.commit()

        _temporary_before = (
            await async_db.scalars(select(AccountRsaKeyTemporary))
        ).all()

        password = self.valid_password
        req_param = {"rsa_passphrase": E2EEUtils.encrypt(password)}

        resp = await async_client.post(
            self.base_url.format(_user_1["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _user_1["address"],
            "rsa_public_key": _user_1["rsa_public_key"],
            "rsa_status": AccountRsaStatus.CHANGING.value,
            "is_deleted": False,
        }
        _temporary_after = (
            await async_db.scalars(select(AccountRsaKeyTemporary))
        ).all()
        assert len(_temporary_before) == 0
        assert len(_temporary_after) == 1
        _temporary = _temporary_after[0]
        assert _temporary.issuer_address == _user_1["address"]
        assert _temporary.rsa_private_key == _user_1["rsa_private_key"]
        assert _temporary.rsa_public_key == _user_1["rsa_public_key"]
        assert _temporary.rsa_passphrase == rsa_passphrase

        _account_after = (await async_db.scalars(select(Account).limit(1))).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.eoa_password == eoa_password
        assert _account_after.rsa_private_key == _user_1["rsa_private_key"]
        assert _account_after.rsa_public_key == _user_1["rsa_public_key"]
        assert E2EEUtils.decrypt(_account_after.rsa_passphrase) == password
        assert _account_after.rsa_status == AccountRsaStatus.CHANGING.value

    # <Normal_3>
    # RSA Create(default passphrase)
    @pytest.mark.asyncio
    async def test_normal_3(self, async_client, async_db):
        _user_1 = config_eth_account("user1")

        _account_before = Account()
        _account_before.issuer_address = _user_1["address"]
        _account_before.keyfile = _user_1["keyfile_json"]
        eoa_password = E2EEUtils.encrypt("password")
        _account_before.eoa_password = eoa_password
        _account_before.rsa_status = AccountRsaStatus.UNSET.value
        async_db.add(_account_before)

        await async_db.commit()

        req_param = {}

        resp = await async_client.post(
            self.base_url.format(_user_1["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _user_1["address"],
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.CREATING.value,
            "is_deleted": False,
        }
        _account_after = (await async_db.scalars(select(Account).limit(1))).first()
        assert _account_after.issuer_address == _user_1["address"]
        assert _account_after.keyfile == _user_1["keyfile_json"]
        assert _account_after.eoa_password == eoa_password
        assert _account_after.rsa_private_key is None
        assert _account_after.rsa_public_key is None
        assert (
            E2EEUtils.decrypt(_account_after.rsa_passphrase)
            == PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE
        )
        assert _account_after.rsa_status == AccountRsaStatus.CREATING.value

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error: no body
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        resp = await async_client.post(self.base_url.format(ZERO_ADDRESS))

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
    # Parameter Error: rsa_passphrase
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        _user_1 = config_eth_account("user1")

        req_param = {"rsa_passphrase": "test"}

        resp = await async_client.post(
            self.base_url.format(_user_1["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": "test",
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "Value error, rsa_passphrase is not a Base64-encoded "
                    "encrypted data",
                    "type": "value_error",
                }
            ],
        }

    # <Error_3>
    # Not Exists Account
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.SET.value
        async_db.add(_account)

        await async_db.commit()

        req_param = {"rsa_passphrase": E2EEUtils.encrypt(self.valid_password)}

        _user_2 = config_eth_account("user2")
        resp = await async_client.post(
            self.base_url.format(_user_2["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }

    # <Error_4>
    # now Generating RSA(CREATING)
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.CREATING.value
        async_db.add(_account)

        await async_db.commit()

        req_param = {"rsa_passphrase": E2EEUtils.encrypt(self.valid_password)}

        resp = await async_client.post(
            self.base_url.format(_user_1["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "RSA key is now generating",
        }

    # <Error_5>
    # now Generating RSA(CHANGING)
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.CHANGING.value
        async_db.add(_account)

        await async_db.commit()

        req_param = {"rsa_passphrase": E2EEUtils.encrypt(self.valid_password)}

        resp = await async_client.post(
            self.base_url.format(_user_1["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "RSA key is now generating",
        }

    # <Error_6>
    # Passphrase Policy Violation
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        _user_1 = config_eth_account("user1")

        _account = Account()
        _account.issuer_address = _user_1["address"]
        _account.keyfile = _user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = _user_1["rsa_private_key"]
        _account.rsa_public_key = _user_1["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.SET.value
        async_db.add(_account)

        await async_db.commit()

        req_param = {"rsa_passphrase": E2EEUtils.encrypt(self.invalid_password)}

        resp = await async_client.post(
            self.base_url.format(_user_1["address"]), json=req_param
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG,
        }
