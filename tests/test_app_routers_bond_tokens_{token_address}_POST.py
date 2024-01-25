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
from web3.middleware import geth_poa_middleware

import config
from app.exceptions import SendTransactionError
from app.model.blockchain import IbetStraightBondContract
from app.model.db import (
    Account,
    AuthToken,
    Token,
    TokenAttrUpdate,
    TokenType,
    TokenUpdateOperationLog,
    TokenVersion,
    UpdateToken,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


async def deploy_bond_token_contract(
    address,
    private_key,
):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        "JPY",
        "token.redemption_date",
        30,
        "JPY",
        "token.return_date",
        "token.return_amount",
        "token.purpose",
    ]
    bond_contrat = IbetStraightBondContract()
    token_address, _, _ = await bond_contrat.create(arguments, address, private_key)

    return ContractUtils.get_contract("IbetStraightBond", token_address)


@mock.patch("app.model.blockchain.token.TX_GAS_LIMIT", 8000000)
class TestAppRoutersBondTokensTokenAddressPOST:
    # target API endpoint
    base_url = "/bond/tokens/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    @pytest.mark.asyncio
    async def test_normal_1_1(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_bond_token_contract(
            _issuer_address, issuer_private_key
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "face_value": 10000,
            "face_value_currency": "USD",
            "interest_rate": 0.57,
            "interest_payment_date": ["0101", "0701"],
            "interest_payment_currency": "USD",
            "redemption_value": 11000,
            "redemption_value_currency": "USD",
            "base_fx_rate": 123.456789,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "m" * 10000,
        }
        resp = client.post(
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

        token_attr_update = db.scalars(
            select(TokenAttrUpdate).where(
                TokenAttrUpdate.token_address == _token_address
            )
        ).all()
        assert len(token_attr_update) == 1

        update_token = db.scalars(select(UpdateToken).limit(1)).first()
        assert update_token is None

        operation_log = db.scalars(select(TokenUpdateOperationLog).limit(1)).first()
        assert operation_log.token_address == _token_address
        assert operation_log.issuer_address == _issuer_address
        assert operation_log.type == TokenType.IBET_STRAIGHT_BOND.value
        assert operation_log.original_contents == {
            "contract_name": "IbetStraightBond",
            "token_address": _token_address,
            "issuer_address": _issuer_address,
            "name": "token.name",
            "symbol": "token.symbol",
            "total_supply": 100,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000000",
            "contact_information": "",
            "privacy_policy": "",
            "status": True,
            "personal_info_contract_address": "0x0000000000000000000000000000000000000000",
            "transferable": False,
            "is_offering": False,
            "transfer_approval_required": False,
            "face_value": 20,
            "face_value_currency": "JPY",
            "interest_rate": 0.0,
            "interest_payment_currency": "",
            "redemption_date": "token.redemption_date",
            "redemption_value": 30,
            "redemption_value_currency": "JPY",
            "return_date": "token.return_date",
            "return_amount": "token.return_amount",
            "base_fx_rate": 0.0,
            "purpose": "token.purpose",
            "memo": "",
            "is_redeemed": False,
            "interest_payment_date": ["", "", "", "", "", "", "", "", "", "", "", ""],
        }
        assert operation_log.arguments == {
            "face_value": 10000,
            "face_value_currency": "USD",
            "interest_rate": 0.57,
            "interest_payment_date": ["0101", "0701"],
            "interest_payment_currency": "USD",
            "redemption_value": 11000,
            "redemption_value_currency": "USD",
            "base_fx_rate": 123.456789,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "m" * 10000,
        }
        assert operation_log.operation_category == "Update"

    # <Normal_1_2>
    # Empty str set to currency code
    @pytest.mark.asyncio
    async def test_normal_1_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_bond_token_contract(
            _issuer_address, issuer_private_key
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "face_value": 10000,
            "face_value_currency": "USD",
            "interest_rate": 3.0,
            "interest_payment_date": ["1201"],
            "interest_payment_currency": "JPY",
            "redemption_value": 0,
            "redemption_value_currency": "",
            "base_fx_rate": 123.456789,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "m" * 10000,
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200, resp.json()
        assert resp.json() is None

        token_attr_update = db.scalars(
            select(TokenAttrUpdate).where(
                TokenAttrUpdate.token_address == _token_address
            )
        ).all()
        assert len(token_attr_update) == 1

        update_token = db.scalars(select(UpdateToken).limit(1)).first()
        assert update_token is None

        operation_log = db.scalars(select(TokenUpdateOperationLog).limit(1)).first()
        assert operation_log.token_address == _token_address
        assert operation_log.issuer_address == _issuer_address
        assert operation_log.type == TokenType.IBET_STRAIGHT_BOND.value
        assert operation_log.original_contents == {
            "contract_name": "IbetStraightBond",
            "token_address": _token_address,
            "issuer_address": _issuer_address,
            "name": "token.name",
            "symbol": "token.symbol",
            "total_supply": 100,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000000",
            "contact_information": "",
            "privacy_policy": "",
            "status": True,
            "personal_info_contract_address": "0x0000000000000000000000000000000000000000",
            "transferable": False,
            "is_offering": False,
            "transfer_approval_required": False,
            "face_value": 20,
            "face_value_currency": "JPY",
            "interest_rate": 0,
            "interest_payment_currency": "",
            "redemption_date": "token.redemption_date",
            "redemption_value": 30,
            "redemption_value_currency": "JPY",
            "return_date": "token.return_date",
            "return_amount": "token.return_amount",
            "base_fx_rate": 0.0,
            "purpose": "token.purpose",
            "memo": "",
            "is_redeemed": False,
            "interest_payment_date": ["", "", "", "", "", "", "", "", "", "", "", ""],
        }
        assert operation_log.arguments == {
            "face_value": 10000,
            "face_value_currency": "USD",
            "interest_rate": 3.0,
            "interest_payment_date": ["1201"],
            "interest_payment_currency": "JPY",
            "redemption_value": 0,
            "redemption_value_currency": "",
            "base_fx_rate": 123.456789,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "m" * 10000,
        }
        assert operation_log.operation_category == "Update"

    # <Normal_2>
    # No request parameters
    @pytest.mark.asyncio
    async def test_normal_2(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_bond_token_contract(
            _issuer_address, issuer_private_key
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # request target API
        req_param = {}
        resp = client.post(
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

        token_attr_update = db.scalars(
            select(TokenAttrUpdate).where(
                TokenAttrUpdate.token_address == _token_address
            )
        ).all()
        assert len(token_attr_update) == 1

        operation_log = db.scalars(select(TokenUpdateOperationLog).limit(1)).first()
        assert operation_log is not None

    # <Normal_3>
    # Authorization by auth token
    @pytest.mark.asyncio
    async def test_normal_3(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract = await deploy_bond_token_contract(
            _issuer_address,
            issuer_private_key,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = _issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        db.add(auth_token)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "face_value": 10000,
            "face_value_currency": "USD",
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "interest_payment_currency": "USD",
            "redemption_value": 11000,
            "redemption_value_currency": "USD",
            "base_fx_rate": 123.456789,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "memo_test1",
        }
        resp = client.post(
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

        token_attr_update = db.scalars(
            select(TokenAttrUpdate).where(
                TokenAttrUpdate.token_address == _token_address
            )
        ).all()
        assert len(token_attr_update) == 1

        update_token = db.scalars(select(UpdateToken).limit(1)).first()
        assert update_token is None

        operation_log = db.scalars(select(TokenUpdateOperationLog).limit(1)).first()
        assert operation_log.token_address == _token_address
        assert operation_log.issuer_address == _issuer_address
        assert operation_log.type == TokenType.IBET_STRAIGHT_BOND.value
        assert operation_log.original_contents == {
            "contract_name": "IbetStraightBond",
            "token_address": _token_address,
            "issuer_address": _issuer_address,
            "name": "token.name",
            "symbol": "token.symbol",
            "total_supply": 100,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000000",
            "contact_information": "",
            "privacy_policy": "",
            "status": True,
            "personal_info_contract_address": "0x0000000000000000000000000000000000000000",
            "transferable": False,
            "is_offering": False,
            "transfer_approval_required": False,
            "face_value": 20,
            "face_value_currency": "JPY",
            "interest_rate": 0.0,
            "interest_payment_currency": "",
            "redemption_date": "token.redemption_date",
            "redemption_value": 30,
            "redemption_value_currency": "JPY",
            "return_date": "token.return_date",
            "return_amount": "token.return_amount",
            "base_fx_rate": 0.0,
            "purpose": "token.purpose",
            "memo": "",
            "is_redeemed": False,
            "interest_payment_date": ["", "", "", "", "", "", "", "", "", "", "", ""],
        }
        assert operation_log.arguments == {
            "face_value": 10000,
            "face_value_currency": "USD",
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "interest_payment_currency": "USD",
            "redemption_value": 11000,
            "redemption_value_currency": "USD",
            "base_fx_rate": 123.456789,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "memo_test1",
        }
        assert operation_log.operation_category == "Update"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError: interest_rate
    def test_error_1_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "interest_rate": 0.00001,
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": 1e-05,
                    "loc": ["body", "interest_rate"],
                    "msg": "Value error, interest_rate must be rounded to 4 decimal "
                    "places",
                    "type": "value_error",
                }
            ],
        }

    # <Error_1_2_1>
    # RequestValidationError: interest_payment_date
    # list length of interest_payment_date must be less than 13
    def test_error_1_2_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "interest_payment_date": [
                "0101",
                "0102",
                "0103",
                "0104",
                "0105",
                "0106",
                "0107",
                "0108",
                "0109",
                "0110",
                "0111",
                "0112",
                "0113",
            ],
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": [
                        "0101",
                        "0102",
                        "0103",
                        "0104",
                        "0105",
                        "0106",
                        "0107",
                        "0108",
                        "0109",
                        "0110",
                        "0111",
                        "0112",
                        "0113",
                    ],
                    "loc": ["body", "interest_payment_date"],
                    "msg": "Value error, list length of interest_payment_date must be "
                    "less than 13",
                    "type": "value_error",
                }
            ],
        }

    # <Error_1_2_2>
    # RequestValidationError: interest_payment_date
    # string does not match regex
    def test_error_1_2_2(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "interest_payment_date": ["01010"],
        }
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"pattern": "^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"},
                    "input": "01010",
                    "loc": ["body", "interest_payment_date", 0],
                    "msg": "String should match pattern "
                    "'^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                }
            ],
        }

    # <Error_1_3>
    # RequestValidationError: is_redeemed
    def test_error_1_3(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"is_redeemed": False}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"error": {}},
                    "input": False,
                    "loc": ["body", "is_redeemed"],
                    "msg": "Value error, is_redeemed cannot be updated to `false`",
                    "type": "value_error",
                }
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_1_4>
    # RequestValidationError: tradable_exchange_contract_address
    def test_error_1_4(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"tradable_exchange_contract_address": "invalid_address"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
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

    # <Error_1_5>
    # RequestValidationError: personal_info_contract_address
    def test_error_1_5(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"personal_info_contract_address": "invalid_address"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
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

    # <Error_1_6_1>
    # RequestValidationError: face_value_currency
    # max_length
    def test_error_1_6_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"face_value_currency": "JPYY"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "string_too_long",
                    "loc": ["body", "face_value_currency"],
                    "msg": "String should have at most 3 characters",
                    "input": "JPYY",
                    "ctx": {"max_length": 3},
                }
            ],
        }

    # <Error_1_6_2>
    # RequestValidationError: face_value_currency
    # min_length
    def test_error_1_6_2(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"face_value_currency": "JP"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "string_too_short",
                    "loc": ["body", "face_value_currency"],
                    "msg": "String should have at least 3 characters",
                    "input": "JP",
                    "ctx": {"min_length": 3},
                }
            ],
        }

    # <Error_1_7_1>
    # RequestValidationError: interest_payment_currency
    # max_length
    def test_error_1_7_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"interest_payment_currency": "JPYY"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"max_length": 3},
                    "input": "JPYY",
                    "loc": ["body", "interest_payment_currency", "constrained-str"],
                    "msg": "String should have at most 3 characters",
                    "type": "string_too_long",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "JPYY",
                    "loc": ["body", "interest_payment_currency", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_1_7_2>
    # RequestValidationError: interest_payment_currency
    # min_length
    def test_error_1_7_2(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"interest_payment_currency": "JP"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"min_length": 3},
                    "input": "JP",
                    "loc": ["body", "interest_payment_currency", "constrained-str"],
                    "msg": "String should have at least 3 characters",
                    "type": "string_too_short",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "JP",
                    "loc": ["body", "interest_payment_currency", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_1_8_1>
    # RequestValidationError: redemption_value_currency
    # max_length
    def test_error_1_8_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"redemption_value_currency": "JPYY"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"max_length": 3},
                    "input": "JPYY",
                    "loc": ["body", "redemption_value_currency", "constrained-str"],
                    "msg": "String should have at most 3 characters",
                    "type": "string_too_long",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "JPYY",
                    "loc": ["body", "redemption_value_currency", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_1_8_2>
    # RequestValidationError: redemption_value_currency
    # min_length
    def test_error_1_8_2(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"redemption_value_currency": "JP"}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "ctx": {"min_length": 3},
                    "input": "JP",
                    "loc": ["body", "redemption_value_currency", "constrained-str"],
                    "msg": "String should have at least 3 characters",
                    "type": "string_too_short",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "JP",
                    "loc": ["body", "redemption_value_currency", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }

    # <Error_1_9>
    # RequestValidationError: base_fx_rate
    def test_error_1_9(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {"base_fx_rate": 123.4567899}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": ""},
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "base_fx_rate"],
                    "msg": "Value error, base_fx_rate must be less than or equal to six decimal places",
                    "input": 123.4567899,
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_2>
    # RequestValidationError: headers and body required
    def test_error_2(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        resp = client.post(self.base_url.format(_token_address))

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

    # <Error_3>
    # RequestValidationError: issuer-address
    def test_error_3(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {}
        resp = client.post(
            self.base_url.format(_token_address),
            json=req_param,
            headers={"issuer-address": "issuer-address"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "issuer-address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_4>
    # RequestValidationError: eoa-password((not decrypt))
    def test_error_4(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "face_value": 10000,
            "interest_rate": 0.5,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 11000,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "memo_test1",
        }
        resp = client.post(
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

    # <Error_5>
    # RequestValidationError: min value
    def test_error_5(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "face_value": -1,
            "interest_rate": -0.0001,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": -1,
            "base_fx_rate": -0.000001,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "memo_test1",
        }
        resp = client.post(
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
                    "type": "greater_than_equal",
                    "loc": ["body", "face_value"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -1,
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "interest_rate"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -0.0001,
                    "ctx": {"ge": 0.0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "redemption_value"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -1,
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "base_fx_rate"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -1e-06,
                    "ctx": {"ge": 0.0},
                },
            ],
        }

    # <Error_6>
    # RequestValidationError: max value
    def test_error_6(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        req_param = {
            "face_value": 5_000_000_001,
            "interest_rate": 100.0001,
            "interest_payment_date": ["0101", "0701"],
            "redemption_value": 5_000_000_001,
            "transferable": False,
            "status": False,
            "is_offering": False,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740",
            "personal_info_contract_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a",
            "contact_information": "問い合わせ先test",
            "privacy_policy": "プライバシーポリシーtest",
            "transfer_approval_required": True,
            "memo": "memo_test1",
        }
        resp = client.post(
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
                    "ctx": {"le": 5000000000},
                    "input": 5000000001,
                    "loc": ["body", "face_value"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"le": 100.0},
                    "input": 100.0001,
                    "loc": ["body", "interest_rate"],
                    "msg": "Input should be less than or equal to 100",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"le": 5000000000},
                    "input": 5000000001,
                    "loc": ["body", "redemption_value"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "type": "less_than_equal",
                },
            ],
        }

    # <Error_7>
    # AuthorizationError: issuer does not exist
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.update")
    def test_error_7(self, IbetStraightBondContract_mock, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {}
        resp = client.post(
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

    # <Error_8>
    # AuthorizationError: token not found
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.update")
    def test_error_8(self, IbetStraightBondContract_mock, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {}
        resp = client.post(
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

    # <Error_9>
    # token not found
    @mock.patch("app.model.blockchain.token.IbetStraightBondContract.update")
    def test_error_9(self, IbetStraightBondContract_mock, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        db.commit()

        # mock
        IbetStraightBondContract_mock.side_effect = [None]

        # request target API
        req_param = {}
        resp = client.post(
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

    # <Error_10>
    # Processing Token
    def test_error_10(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # request target API
        req_param = {}
        resp = client.post(
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

    # <Error_11>
    # Send Transaction Error
    @mock.patch(
        "app.model.blockchain.token.IbetStraightBondContract.update",
        MagicMock(side_effect=SendTransactionError()),
    )
    def test_error_11(self, client, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # request target API
        req_param = {}
        resp = client.post(
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
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }
