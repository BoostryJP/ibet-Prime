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
from unittest import mock
from unittest.mock import MagicMock

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import config
from app.exceptions import SendTransactionError
from app.model.blockchain import IbetShareContract
from app.model.db import (
    Account,
    AuthToken,
    Token,
    TokenAttrUpdate,
    TokenType,
    TokenUpdateOperationLog,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


async def deploy_share_token_contract(
    address,
    private_key,
):
    arguments = [
        "token.name",
        "token.symbol",
        20,
        100,
        3,
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        30,
    ]
    share_contract = IbetShareContract()
    token_address, _, _ = await share_contract.create(arguments, address, private_key)

    return ContractUtils.get_contract("IbetShare", token_address)


@mock.patch("app.model.blockchain.token.TX_GAS_LIMIT", 8000000)
class TestAppRoutersShareTokensTokenAddressPOST:
    # target API endpoint
    base_url = "/share/tokens/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_share_token_contract(
            _issuer_address,
            issuer_private_key,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": False,
            "principal_value": 1000,
            "is_canceled": True,
            "memo": "m" * 10000,
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        assert resp.status_code == 200
        assert resp.json() is None

        token_attr_update = (
            await async_db.scalars(
                select(TokenAttrUpdate).where(
                    TokenAttrUpdate.token_address == _token_address
                )
            )
        ).all()
        assert len(token_attr_update) == 1

        operation_log = (
            await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
        ).first()
        assert operation_log.token_address == _token_address
        assert operation_log.issuer_address == _issuer_address
        assert operation_log.type == TokenType.IBET_SHARE
        assert operation_log.original_contents == {
            "cancellation_date": "token.cancellation_date",
            "contact_information": "",
            "contract_name": "IbetShare",
            "dividend_payment_date": "token.dividend_payment_date",
            "dividend_record_date": "token.dividend_record_date",
            "dividends": 3e-13,
            "is_canceled": False,
            "is_offering": False,
            "issue_price": 20,
            "issuer_address": _issuer_address,
            "memo": "",
            "name": "token.name",
            "personal_info_contract_address": "0x0000000000000000000000000000000000000000",
            "require_personal_info_registered": True,
            "principal_value": 30,
            "privacy_policy": "",
            "status": True,
            "symbol": "token.symbol",
            "token_address": _token_address,
            "total_supply": 100,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000000",
            "transfer_approval_required": False,
            "transferable": False,
        }
        assert operation_log.arguments == {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": False,
            "principal_value": 1000,
            "is_canceled": True,
            "memo": "m" * 10000,
        }
        assert operation_log.operation_category == "Update"

    # <Normal_2>
    # No request parameters
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_share_token_contract(
            _issuer_address,
            issuer_private_key,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        token_attr_update = (
            await async_db.scalars(
                select(TokenAttrUpdate)
                .where(TokenAttrUpdate.token_address == _token_address)
                .limit(1)
            )
        ).all()
        assert len(token_attr_update) == 1

        operation_log = (
            await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
        ).first()
        assert operation_log is not None

    # <Normal_3>
    # Authorization by auth-token
    @pytest.mark.asyncio
    async def test_normal_3(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_share_token_contract(
            _issuer_address,
            issuer_private_key,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = _issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        async_db.add(auth_token)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": False,
            "principal_value": 1000,
            "is_canceled": True,
            "memo": "memo_test1",
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "auth-token": "test_auth_token",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        token_attr_update = (
            await async_db.scalars(
                select(TokenAttrUpdate)
                .where(TokenAttrUpdate.token_address == _token_address)
                .limit(1)
            )
        ).all()
        assert len(token_attr_update) == 1

        operation_log = (
            await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
        ).first()
        assert operation_log.token_address == _token_address
        assert operation_log.issuer_address == _issuer_address
        assert operation_log.type == TokenType.IBET_SHARE
        assert operation_log.original_contents == {
            "cancellation_date": "token.cancellation_date",
            "contact_information": "",
            "contract_name": "IbetShare",
            "dividend_payment_date": "token.dividend_payment_date",
            "dividend_record_date": "token.dividend_record_date",
            "dividends": 3e-13,
            "is_canceled": False,
            "is_offering": False,
            "issue_price": 20,
            "issuer_address": _issuer_address,
            "memo": "",
            "name": "token.name",
            "personal_info_contract_address": "0x0000000000000000000000000000000000000000",
            "require_personal_info_registered": True,
            "principal_value": 30,
            "privacy_policy": "",
            "status": True,
            "symbol": "token.symbol",
            "token_address": _token_address,
            "total_supply": 100,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000000",
            "transfer_approval_required": False,
            "transferable": False,
        }
        assert operation_log.arguments == {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "require_personal_info_registered": False,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": False,
            "principal_value": 1000,
            "is_canceled": True,
            "memo": "memo_test1",
        }
        assert operation_log.operation_category == "Update"

    # <Normal_4_1>
    # YYYYMMDD parameter is not an empty string
    @pytest.mark.asyncio
    async def test_normal_4_1(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_share_token_contract(
            _issuer_address,
            issuer_private_key,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        token_attr_update = (
            await async_db.scalars(
                select(TokenAttrUpdate)
                .where(TokenAttrUpdate.token_address == _token_address)
                .limit(1)
            )
        ).all()
        assert len(token_attr_update) == 1

        operation_log = (
            await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
        ).first()
        assert operation_log.token_address == _token_address
        assert operation_log.issuer_address == _issuer_address
        assert operation_log.type == TokenType.IBET_SHARE
        assert operation_log.original_contents == {
            "cancellation_date": "token.cancellation_date",
            "contact_information": "",
            "contract_name": "IbetShare",
            "dividend_payment_date": "token.dividend_payment_date",
            "dividend_record_date": "token.dividend_record_date",
            "dividends": 3e-13,
            "is_canceled": False,
            "is_offering": False,
            "issue_price": 20,
            "issuer_address": _issuer_address,
            "memo": "",
            "name": "token.name",
            "personal_info_contract_address": "0x0000000000000000000000000000000000000000",
            "require_personal_info_registered": True,
            "principal_value": 30,
            "privacy_policy": "",
            "status": True,
            "symbol": "token.symbol",
            "token_address": _token_address,
            "total_supply": 100,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000000",
            "transfer_approval_required": False,
            "transferable": False,
        }
        assert operation_log.arguments == {
            "cancellation_date": "20221231",
            "dividends": 345.67,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
        }
        assert operation_log.operation_category == "Update"

    # <Normal_4_2>
    # YYYYMMDD parameter is an empty string
    @pytest.mark.asyncio
    async def test_normal_4_2(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_share_token_contract(
            _issuer_address,
            issuer_private_key,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "cancellation_date": "",
            "dividends": 345.67,
            "dividend_record_date": "",
            "dividend_payment_date": "",
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        token_attr_update = (
            await async_db.scalars(
                select(TokenAttrUpdate)
                .where(TokenAttrUpdate.token_address == _token_address)
                .limit(1)
            )
        ).all()
        assert len(token_attr_update) == 1

        operation_log = (
            await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
        ).first()
        assert operation_log.token_address == _token_address
        assert operation_log.issuer_address == _issuer_address
        assert operation_log.type == TokenType.IBET_SHARE
        assert operation_log.original_contents == {
            "cancellation_date": "token.cancellation_date",
            "contact_information": "",
            "contract_name": "IbetShare",
            "dividend_payment_date": "token.dividend_payment_date",
            "dividend_record_date": "token.dividend_record_date",
            "dividends": 3e-13,
            "is_canceled": False,
            "is_offering": False,
            "issue_price": 20,
            "issuer_address": _issuer_address,
            "memo": "",
            "name": "token.name",
            "personal_info_contract_address": "0x0000000000000000000000000000000000000000",
            "require_personal_info_registered": True,
            "principal_value": 30,
            "privacy_policy": "",
            "status": True,
            "symbol": "token.symbol",
            "token_address": _token_address,
            "total_supply": 100,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000000",
            "transfer_approval_required": False,
            "transferable": False,
        }
        assert operation_log.arguments == {
            "cancellation_date": "",
            "dividends": 345.67,
            "dividend_record_date": "",
            "dividend_payment_date": "",
        }
        assert operation_log.operation_category == "Update"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: dividends
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "dividends": 0.00000000000001,
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": 1e-14,
                    "loc": ["body", "dividends"],
                    "msg": "Value error, dividends must be rounded to 13 decimal "
                    "places",
                    "type": "value_error",
                }
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_2>
    # RequestValidationError: dividend information all required
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "dividends": 0.01,
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": {"dividends": 0.01},
                    "loc": ["body"],
                    "msg": "Value error, all items are required to update the "
                    "dividend information",
                    "type": "value_error",
                }
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_3>
    # RequestValidationError: tradable_exchange_contract_address
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"tradable_exchange_contract_address": "invalid_address"}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": "invalid_address",
                    "loc": ["body", "tradable_exchange_contract_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_4>
    # RequestValidationError: personal_info_contract_address
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"personal_info_contract_address": "invalid_address"}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": "invalid_address",
                    "loc": ["body", "personal_info_contract_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_5>
    # RequestValidationError: is_canceled
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"is_canceled": False}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": False,
                    "loc": ["body", "is_canceled"],
                    "msg": "Value error, is_canceled cannot be updated to `false`",
                    "type": "value_error",
                }
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_6>
    # RequestValidationError: headers and body required
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        resp = await async_client.post(self.base_url.format(_token_address))

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

    # <Error_7>
    # RequestValidationError: issuer-address
    @pytest.mark.asyncio
    async def test_error_7(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": "issuer_address"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "issuer_address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_8>
    # RequestValidationError: eoa-password(not decrypt)
    @pytest.mark.asyncio
    async def test_error_8(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address, "eoa-password": "password"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "password",
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                }
            ],
        }

    # <Error_9>
    # RequestValidationError: min value
    @pytest.mark.asyncio
    async def test_error_9(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "cancellation_date": "20221231",
            "dividends": -0.01,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": False,
            "principal_value": -1,
            "is_canceled": True,
            "memo": "memo_test1",
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address, "eoa-password": "password"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 0.0},
                    "input": -0.01,
                    "loc": ["body", "dividends"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "principal_value"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
        }

    # <Error_10>
    # RequestValidationError: max value
    @pytest.mark.asyncio
    async def test_error_10(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "cancellation_date": "20221231",
            "dividends": 5_000_000_000.01,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "transferable": False,
            "status": False,
            "is_offering": False,
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": False,
            "principal_value": 5_000_000_001,
            "is_canceled": True,
            "memo": "memo_test1",
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address, "eoa-password": "password"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"le": 5000000000.0},
                    "input": 5000000000.01,
                    "loc": ["body", "dividends"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"le": 5000000000},
                    "input": 5000000001,
                    "loc": ["body", "principal_value"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "type": "less_than_equal",
                },
            ],
        }

    # <Error_11>
    # RequestValidationError
    # YYYYMMDD regex
    @pytest.mark.asyncio
    async def test_error_11(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "cancellation_date": "202112310",
            "dividend_record_date": "202112310",
            "dividend_payment_date": "202112310",
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": _issuer_address},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "202112310",
                    "loc": ["body", "cancellation_date", "constrained-str"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "202112310",
                    "loc": ["body", "cancellation_date", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
                {
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "202112310",
                    "loc": ["body", "dividend_record_date", "constrained-str"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "202112310",
                    "loc": ["body", "dividend_record_date", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
                {
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "202112310",
                    "loc": ["body", "dividend_payment_date", "constrained-str"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "202112310",
                    "loc": ["body", "dividend_payment_date", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
            ],
        }

    # <Error_12>
    # AuthorizationError: issuer does not exist
    @mock.patch("app.model.blockchain.token.IbetShareContract.update")
    @pytest.mark.asyncio
    async def test_error_12(self, IbetShareContract_mock, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # mock
        IbetShareContract_mock.side_effect = [None]

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
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

    # <Error_13>
    # AuthorizationError: password mismatch
    @mock.patch("app.model.blockchain.token.IbetShareContract.update")
    @pytest.mark.asyncio
    async def test_error_13(self, IbetShareContract_mock, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # mock
        IbetShareContract_mock.side_effect = [None]

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_14>
    # token not found
    @mock.patch("app.model.blockchain.token.IbetShareContract.update")
    @pytest.mark.asyncio
    async def test_error_14(self, IbetShareContract_mock, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # mock
        IbetShareContract_mock.side_effect = [None]

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
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

    # <Error_15>
    # Processing Token
    @pytest.mark.asyncio
    async def test_error_15(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.token_status = 0
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
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

    # <Error_16>
    # Send Transaction Error
    @mock.patch(
        "app.model.blockchain.token.IbetShareContract.update",
        MagicMock(side_effect=SendTransactionError()),
    )
    @pytest.mark.asyncio
    async def test_error_16(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {}
        resp = await async_client.post(
            self.base_url.format(_token_address),
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
            "detail": "failed to send transaction",
        }

    # <Error_17>
    # OperationNotSupportedVersionError: v24.6
    @pytest.mark.asyncio
    async def test_error_17(self, async_client, async_db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = {}
        token.token_status = 1
        token.version = TokenVersion.V_22_12
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "require_personal_info_registered": False,
        }
        resp = await async_client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 6, "title": "OperationNotSupportedVersionError"},
            "detail": "the operation is not supported in 22_12",
        }
