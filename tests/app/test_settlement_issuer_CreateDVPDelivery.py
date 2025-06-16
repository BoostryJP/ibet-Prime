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
import hashlib
import json
import secrets
from unittest import mock

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select

from app.model.blockchain import IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    Account,
    AuthToken,
    DVPAsyncProcess,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


async def deploy_bond_token_contract(
    address,
    private_key,
    personal_info_contract_address,
    tradable_exchange_contract_address=None,
    transfer_approval_required=None,
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
    await bond_contrat.update(
        data=IbetStraightBondUpdateParams(
            transferable=True,
            personal_info_contract_address=personal_info_contract_address,
            tradable_exchange_contract_address=tradable_exchange_contract_address,
            transfer_approval_required=transfer_approval_required,
        ),
        tx_from=address,
        private_key=private_key,
    )

    return ContractUtils.get_contract("IbetStraightBond", token_address)


class TestCreateDVPDelivery:
    # target API endpoint
    base_url = "/settlement/dvp/{exchange_address}/deliveries"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # No data encryption
    # - Authorization by eoa-password
    @pytest.mark.asyncio
    async def test_normal_1_1(
        self,
        ibet_security_token_dvp_contract,
        personal_info_contract,
        async_client,
        async_db,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": token_contract_1.address,
            "buyer_address": user_address_1,
            "amount": 10,
            "agent_address": agent_address,
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list) == 1

        _async_process: DVPAsyncProcess = _async_process_list[0]
        assert _async_process.id == 1
        assert _async_process.issuer_address == issuer_address
        assert _async_process.process_type == "CreateDelivery"
        assert _async_process.process_status == 1
        assert (
            _async_process.dvp_contract_address
            == ibet_security_token_dvp_contract.address
        )
        assert _async_process.token_address == token_contract_1.address
        assert _async_process.seller_address == issuer_address
        assert _async_process.buyer_address == user_address_1
        assert _async_process.amount == 10
        assert _async_process.agent_address == agent_address
        assert (
            _async_process.data
            == '{"encryption_algorithm": null, "encryption_key_ref": null, "settlement_service_type": "test_service", "data": "{}"}'
        )
        assert _async_process.delivery_id is None
        assert _async_process.step == 0
        assert _async_process.step_tx_hash is not None
        assert _async_process.step_tx_status == "done"
        assert _async_process.revert_tx_hash is None
        assert _async_process.revert_tx_status is None

    # <Normal_1_2>
    # No data encryption
    # - Authorization by auth-token
    @pytest.mark.asyncio
    async def test_normal_1_2(
        self,
        ibet_security_token_dvp_contract,
        personal_info_contract,
        async_client,
        async_db,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        auth_token = AuthToken()
        auth_token.issuer_address = issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        async_db.add(auth_token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": token_contract_1.address,
            "buyer_address": user_address_1,
            "amount": 10,
            "agent_address": agent_address,
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "auth-token": "test_auth_token",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list) == 1

        _async_process: DVPAsyncProcess = _async_process_list[0]
        assert _async_process.id == 1
        assert _async_process.issuer_address == issuer_address
        assert _async_process.process_type == "CreateDelivery"
        assert _async_process.process_status == 1
        assert (
            _async_process.dvp_contract_address
            == ibet_security_token_dvp_contract.address
        )
        assert _async_process.token_address == token_contract_1.address
        assert _async_process.seller_address == issuer_address
        assert _async_process.buyer_address == user_address_1
        assert _async_process.amount == 10
        assert _async_process.agent_address == agent_address
        assert (
            _async_process.data
            == '{"encryption_algorithm": null, "encryption_key_ref": null, "settlement_service_type": "test_service", "data": "{}"}'
        )
        assert _async_process.delivery_id is None
        assert _async_process.step == 0
        assert _async_process.step_tx_hash is not None
        assert _async_process.step_tx_status == "done"
        assert _async_process.revert_tx_hash is None
        assert _async_process.revert_tx_status is None

    # <Normal_2>
    # Data encryption
    @pytest.mark.asyncio
    @mock.patch(
        "config.DVP_DATA_ENCRYPTION_MODE",
        "aes-256-cbc",
    )
    @mock.patch(
        "config.DVP_DATA_ENCRYPTION_KEY",
        base64.b64encode(secrets.token_bytes(32)).decode("utf-8"),
    )
    async def test_normal_2(
        self,
        ibet_security_token_dvp_contract,
        personal_info_contract,
        async_client,
        async_db,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": token_contract_1.address,
            "buyer_address": user_address_1,
            "amount": 10,
            "agent_address": agent_address,
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _async_process_list = (await async_db.scalars(select(DVPAsyncProcess))).all()
        assert len(_async_process_list) == 1

        _async_process: DVPAsyncProcess = _async_process_list[0]
        assert _async_process.id == 1
        assert _async_process.issuer_address == issuer_address
        assert _async_process.process_type == "CreateDelivery"
        assert _async_process.process_status == 1
        assert (
            _async_process.dvp_contract_address
            == ibet_security_token_dvp_contract.address
        )
        assert _async_process.token_address == token_contract_1.address
        assert _async_process.seller_address == issuer_address
        assert _async_process.buyer_address == user_address_1
        assert _async_process.amount == 10
        assert _async_process.agent_address == agent_address

        _data = json.loads(_async_process.data)
        assert _data["encryption_algorithm"] == "aes-256-cbc"
        assert _data["encryption_key_ref"] == "local"
        assert _data["settlement_service_type"] == "test_service"
        assert _data["data"] is not None

        assert _async_process.delivery_id is None
        assert _async_process.step == 0
        assert _async_process.step_tx_hash is not None
        assert _async_process.step_tx_status == "done"
        assert _async_process.revert_tx_hash is None
        assert _async_process.revert_tx_status is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: token_address, buyer_address, agent_address
    @pytest.mark.asyncio
    async def test_error_1(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = "0x0000000000000000000000000000000000000000"
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": "0x0",
            "buyer_address": "0x0",
            "agent_address": "0x0",
            "amount": 10,
            "data": "",
            "settlement_service_type": "test_service",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "token_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "0x0",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "buyer_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "0x0",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "agent_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "0x0",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_2>
    # RequestValidationError: amount(min)
    @pytest.mark.asyncio
    async def test_error_2(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = "0x0000000000000000000000000000000000000000"
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "buyer_address": "0x0000000000000000000000000000000000000000",
            "amount": 0,
            "agent_address": "0x0000000000000000000000000000000000000000",
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 1},
                    "input": 0,
                    "loc": ["body", "amount"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "greater_than_equal",
                }
            ],
        }

    # <Error_3>
    # RequestValidationError: amount(max)
    @pytest.mark.asyncio
    async def test_error_3(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # request target API
        req_param = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "buyer_address": "0x0000000000000000000000000000000000000000",
            "amount": 1_000_000_000_001,
            "agent_address": "0x0000000000000000000000000000000000000000",
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"le": 1000000000000},
                    "input": 1000000000001,
                    "loc": ["body", "amount"],
                    "msg": "Input should be less than or equal to 1000000000000",
                    "type": "less_than_equal",
                }
            ],
        }

    # <Error_4>
    # RequestValidationError: headers and body required
    @pytest.mark.asyncio
    async def test_error_4(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        # request target API
        resp = await async_client.post(
            self.base_url.format(
                exchange_address="0x0000000000000000000000000000000000000000"
            )
        )

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

    # <Error_5>
    # RequestValidationError: issuer-address
    @pytest.mark.asyncio
    async def test_error_5(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        # request target API
        req_param = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "buyer_address": "0x0000000000000000000000000000000000000000",
            "amount": 1,
            "agent_address": "0x0000000000000000000000000000000000000000",
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
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

    # <Error_6>
    # RequestValidationError: eoa-password(not decrypt)
    @pytest.mark.asyncio
    async def test_error_6(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "buyer_address": "0x0000000000000000000000000000000000000000",
            "amount": 1,
            "agent_address": "0x0000000000000000000000000000000000000000",
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={"issuer-address": issuer_address, "eoa-password": "password"},
        )

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

    # <Error_7>
    # issuer does not exist
    @pytest.mark.asyncio
    async def test_error_7(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = "0x0000000000000000000000000000000000000000"
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "buyer_address": "0x0000000000000000000000000000000000000000",
            "amount": 1,
            "agent_address": "0x0000000000000000000000000000000000000000",
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
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
    # password mismatch
    @pytest.mark.asyncio
    async def test_error_8(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": "0x0000000000000000000000000000000000000000",
            "buyer_address": "0x0000000000000000000000000000000000000000",
            "amount": 1,
            "agent_address": "0x0000000000000000000000000000000000000000",
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_9>
    # Send Transaction Error
    @pytest.mark.asyncio
    async def test_error_9(
        self,
        async_client,
        async_db,
        ibet_security_token_dvp_contract,
        personal_info_contract,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_address": token_contract_1.address,
            "buyer_address": user_address_1,
            "amount": 1000,
            "agent_address": agent_address,
            "data": json.dumps({}),
            "settlement_service_type": "test_service",
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address
            ),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }
