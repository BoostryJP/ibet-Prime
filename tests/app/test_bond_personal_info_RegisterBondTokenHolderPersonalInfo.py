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

import hashlib
from unittest.mock import patch

import pytest
from sqlalchemy import and_, select

from app.exceptions import SendTransactionError
from app.model.db import (
    Account,
    AuthToken,
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    Token,
    TokenType,
    TokenVersion,
)
from app.model.ibet import IbetStraightBondContract, PersonalInfoContract
from app.model.schema import PersonalInfoDataSource
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import default_eth_account


class TestRegisterBondTokenHolderPersonalInfo:
    # target API endpoint
    test_url = "/bond/tokens/{}/personal_info"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # data_source = on_chain
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = (
            "personal_info_contract_address"
        )
        IbetStraightBondContract_get = patch(
            target="app.model.ibet.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract,
        )
        PersonalInfoContract_init = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.__init__",
            return_value=None,
        )
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value=None,
        )

        with (
            IbetStraightBondContract_get,
            PersonalInfoContract_init,
            PersonalInfoContract_register_info,
        ):
            # request target API
            req_param = {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
            resp = await async_client.post(
                self.test_url.format(_token_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 200
            assert resp.json() is None
            PersonalInfoContract.register_info.assert_called_with(
                account_address=_test_account_address,
                data={
                    "key_manager": "test_key_manager",
                    "name": "test_name",
                    "postal_code": "test_postal_code",
                    "address": "test_address",
                    "email": "test_email",
                    "birth": "test_birth",
                    "is_corporate": False,
                    "tax_category": 10,
                },
                default_value=None,
            )

    # <Normal_1_2>
    # data_source = off_chain
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = (
            "personal_info_contract_address"
        )
        IbetStraightBondContract_get = patch(
            target="app.model.ibet.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract,
        )
        PersonalInfoContract_init = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.__init__",
            return_value=None,
        )
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value=None,
        )

        with (
            IbetStraightBondContract_get,
            PersonalInfoContract_init,
            PersonalInfoContract_register_info,
        ):
            # request target API
            req_param = {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
                "data_source": PersonalInfoDataSource.OFF_CHAIN,
            }
            resp = await async_client.post(
                self.test_url.format(_token_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 200
            assert resp.json() is None

            _off_personal_info = (
                await async_db.scalars(
                    select(IDXPersonalInfo)
                    .where(IDXPersonalInfo.issuer_address == _issuer_address)
                    .limit(1)
                )
            ).first()
            assert _off_personal_info is not None
            assert _off_personal_info.issuer_address == _issuer_address
            assert _off_personal_info.account_address == _test_account_address
            assert _off_personal_info.personal_info == {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "address": "test_address",
                "postal_code": "test_postal_code",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
            assert _off_personal_info.data_source == PersonalInfoDataSource.OFF_CHAIN

            _personal_info_history = (
                await async_db.scalars(
                    select(IDXPersonalInfoHistory)
                    .where(
                        and_(
                            IDXPersonalInfoHistory.issuer_address == _issuer_address,
                            IDXPersonalInfoHistory.account_address
                            == _test_account_address,
                        )
                    )
                    .limit(1)
                )
            ).first()
            assert _personal_info_history.id is not None
            assert _personal_info_history.issuer_address == _issuer_address
            assert _personal_info_history.account_address == _test_account_address
            assert _personal_info_history.personal_info == {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "address": "test_address",
                "postal_code": "test_postal_code",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }

    # <Normal_2_1>
    # Optional items
    @pytest.mark.asyncio
    async def test_normal_2_1(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = (
            "personal_info_contract_address"
        )
        IbetStraightBondContract_get = patch(
            target="app.model.ibet.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract,
        )
        PersonalInfoContract_init = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.__init__",
            return_value=None,
        )
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value=None,
        )

        with (
            IbetStraightBondContract_get,
            PersonalInfoContract_init,
            PersonalInfoContract_register_info,
        ):
            # request target API
            req_param = {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
            }
            resp = await async_client.post(
                self.test_url.format(_token_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 200
            assert resp.json() is None
            PersonalInfoContract.register_info.assert_called_with(
                account_address=_test_account_address,
                data={
                    "key_manager": "test_key_manager",
                    "name": None,
                    "postal_code": None,
                    "address": None,
                    "email": None,
                    "birth": None,
                    "is_corporate": None,
                    "tax_category": None,
                },
                default_value=None,
            )

    # <Normal_2_2>
    # Nullable items
    @pytest.mark.asyncio
    async def test_normal_2_2(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = (
            "personal_info_contract_address"
        )
        IbetStraightBondContract_get = patch(
            target="app.model.ibet.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract,
        )
        PersonalInfoContract_init = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.__init__",
            return_value=None,
        )
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value=None,
        )

        with (
            IbetStraightBondContract_get,
            PersonalInfoContract_init,
            PersonalInfoContract_register_info,
        ):
            # request target API
            req_param = {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": None,
                "postal_code": None,
                "address": None,
                "email": None,
                "birth": None,
                "is_corporate": None,
                "tax_category": None,
            }
            resp = await async_client.post(
                self.test_url.format(_token_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 200
            assert resp.json() is None
            PersonalInfoContract.register_info.assert_called_with(
                account_address=_test_account_address,
                data={
                    "key_manager": "test_key_manager",
                    "name": None,
                    "postal_code": None,
                    "address": None,
                    "email": None,
                    "birth": None,
                    "is_corporate": None,
                    "tax_category": None,
                },
                default_value=None,
            )

    # <Normal_3>
    # Authorization by auth token
    @pytest.mark.asyncio
    async def test_normal_3(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = _issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        async_db.add(auth_token)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = (
            "personal_info_contract_address"
        )
        IbetStraightBondContract_get = patch(
            target="app.model.ibet.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract,
        )
        PersonalInfoContract_init = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.__init__",
            return_value=None,
        )
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value=None,
        )

        with (
            IbetStraightBondContract_get,
            PersonalInfoContract_init,
            PersonalInfoContract_register_info,
        ):
            # request target API
            req_param = {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
            resp = await async_client.post(
                self.test_url.format(_token_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "auth-token": "test_auth_token",
                },
            )

            # assertion
            assert resp.status_code == 200
            assert resp.json() is None
            PersonalInfoContract.register_info.assert_called_with(
                account_address=_test_account_address,
                data={
                    "key_manager": "test_key_manager",
                    "name": "test_name",
                    "postal_code": "test_postal_code",
                    "address": "test_address",
                    "email": "test_email",
                    "birth": "test_birth",
                    "is_corporate": False,
                    "tax_category": 10,
                },
                default_value=None,
            )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError
    # headers and body required
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        resp = await async_client.post(self.test_url.format(_token_address))

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_1_2>
    # RequestValidationError
    # personal_info
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "account_address": None,
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["body", "key_manager"],
                    "msg": "Input should be a valid string",
                    "type": "string_type",
                },
            ],
        }

    # <Error_1_3>
    # RequestValidationError
    # personal_info.account_address is invalid
    @pytest.mark.asyncio
    async def test_error_1_3(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "account_address": "test",
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": "test",
                    "loc": ["body", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_1_4>
    # RequestValidationError
    # issuer_address
    @pytest.mark.asyncio
    async def test_error_1_4(self, async_client, async_db):
        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": "test_issuer_address",
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test_issuer_address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_1_5>
    # RequestValidationError
    # eoa-password not encrypted
    @pytest.mark.asyncio
    async def test_error_1_5(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": "not_encrypted_password",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "not_encrypted_password",
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                }
            ],
        }

    # <Error_1_6>
    # RequestValidationError
    # data_source
    @pytest.mark.asyncio
    async def test_error_1_6(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
            "data_source": "invalid_data_source",
        }
        resp = await async_client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["body", "data_source"],
                    "msg": "Input should be 'on-chain' or 'off-chain'",
                    "input": "invalid_data_source",
                    "ctx": {"expected": "'on-chain' or 'off-chain'"},
                }
            ],
        }

    # <Error_2_1>
    # AuthorizationError
    # issuer does not exist
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_2_2>
    # AuthorizationError
    # password mismatch
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("mismatch_password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_3>
    # HTTPException 404
    # token not found
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # <Error_4>
    # InvalidParameterError
    # processing token
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.token_status = 0
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "account_address": _test_account_address,
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10,
        }
        resp = await async_client.post(
            self.test_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # <Error_5>
    # SendTransactionError
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = (
            "personal_info_contract_address"
        )
        IbetStraightBondContract_get = patch(
            target="app.model.ibet.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract,
        )
        PersonalInfoContract_init = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.__init__",
            return_value=None,
        )
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            side_effect=SendTransactionError(),
        )

        with (
            IbetStraightBondContract_get,
            PersonalInfoContract_init,
            PersonalInfoContract_register_info,
        ):
            # request target API
            req_param = {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
            resp = await async_client.post(
                self.test_url.format(_token_address, _test_account_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 503
            assert resp.json() == {
                "meta": {"code": 2, "title": "SendTransactionError"},
                "detail": "failed to register personal information",
            }

    # <Error_6>
    # PersonalInfoExceedsSizeLimit
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        _issuer_account = default_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = default_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_09
        async_db.add(token)

        await async_db.commit()

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = (
            "personal_info_contract_address"
        )
        IbetStraightBondContract_get = patch(
            target="app.model.ibet.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract,
        )
        PersonalInfoContract_init = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.__init__",
            return_value=None,
        )
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            side_effect=SendTransactionError(),
        )

        with (
            IbetStraightBondContract_get,
            PersonalInfoContract_init,
            PersonalInfoContract_register_info,
        ):
            # request target API
            req_param = {
                "account_address": _test_account_address,
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address" * 100,  # Too long value
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10,
            }
            resp = await async_client.post(
                self.test_url.format(_token_address, _test_account_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 400
            assert resp.json() == {
                "meta": {"code": 11, "title": "PersonalInfoExceedsSizeLimit"}
            }
