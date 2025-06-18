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
from datetime import UTC, datetime

import pytest
from eth_keyfile import decode_keyfile_json

from app.model.db import (
    Account,
    AuthToken,
    DeliveryStatus,
    DVPAgentAccount,
    IDXDelivery,
    Token,
    TokenType,
    TokenVersion,
)
from app.model.ibet import IbetStraightBondContract
from app.model.ibet.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import ContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT
from tests.account_config import default_eth_account


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


class TestUpdateDVPDelivery:
    # target API endpoint
    base_url = "/settlement/dvp/{exchange_address}/delivery/{delivery_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Cancel Delivery
    # Authorization by eoa-password
    @pytest.mark.asyncio
    async def test_normal_1_1(
        self,
        ibet_security_token_dvp_contract,
        ibet_personal_info_contract,
        async_client,
        async_db,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = user_3["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
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

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_contract_1.address, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = ibet_security_token_dvp_contract.address
        _idx_delivery.delivery_id = 1
        _idx_delivery.token_address = token_contract_1.address
        _idx_delivery.buyer_address = user_address_1
        _idx_delivery.seller_address = issuer_address
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(
            2024, 1, 1, 0, 0, 0, tzinfo=UTC
        ).replace(tzinfo=None)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED
        async_db.add(_idx_delivery)
        await async_db.commit()

        # request target API
        req_param = {"operation_type": "Cancel"}
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address,
                delivery_id=1,
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

    # <Normal_1_2>
    # Cancel Delivery
    # Authorization by auth-token
    @pytest.mark.asyncio
    async def test_normal_1_2(
        self,
        ibet_security_token_dvp_contract,
        ibet_personal_info_contract,
        async_client,
        async_db,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        user_2 = default_eth_account("user2")
        user_address_1 = user_2["address"]

        user_3 = default_eth_account("user3")
        agent_address = user_3["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = user_3["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
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

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_contract_1.address, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = ibet_security_token_dvp_contract.address
        _idx_delivery.delivery_id = 1
        _idx_delivery.token_address = token_contract_1.address
        _idx_delivery.buyer_address = user_address_1
        _idx_delivery.seller_address = issuer_address
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(
            2024, 1, 1, 0, 0, 0, tzinfo=UTC
        ).replace(tzinfo=None)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED
        async_db.add(_idx_delivery)
        await async_db.commit()

        # request target API
        req_param = {"operation_type": "Cancel"}
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address,
                delivery_id=1,
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

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # RequestValidationError
    # - operation_type
    @pytest.mark.asyncio
    async def test_error_1_1(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # request target API
        req_param = {"operation_type": "invalid_value"}

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
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
                    "type": "literal_error",
                    "loc": ["body", "operation_type"],
                    "msg": "Input should be 'Cancel'",
                    "input": "invalid_value",
                    "ctx": {"expected": "'Cancel'"},
                }
            ],
        }

    # <Error_1_2>
    # RequestValidationError
    # - header: issuer-address
    # - body field
    @pytest.mark.asyncio
    async def test_error_1_2(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        # request target API
        resp = await async_client.post(
            self.base_url.format(
                exchange_address="0x0000000000000000000000000000000000000000",
                delivery_id=1,
            )
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "input": None,
                },
                {
                    "type": "missing",
                    "loc": ["body"],
                    "msg": "Field required",
                    "input": None,
                },
            ],
        }

    # <Error_1_3>
    # RequestValidationError
    # - eoa-password(not decrypt)
    @pytest.mark.asyncio
    async def test_error_1_3(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = default_eth_account("user1")
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
            "operation_type": "Cancel",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
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

    # <Error_2_1>
    # AuthorizationError
    # - issuer does not exist
    @pytest.mark.asyncio
    async def test_error_2_1(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = default_eth_account("user1")
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
            "operation_type": "Cancel",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
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

    # <Error_2_2>
    # AuthorizationError
    # - password mismatch
    @pytest.mark.asyncio
    async def test_error_2_2(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        user_1 = default_eth_account("user1")
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
            "operation_type": "Cancel",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
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

    # <Error_3>
    # NotFound
    # - delivery not found
    @pytest.mark.asyncio
    async def test_error_3(
        self, async_client, async_db, ibet_security_token_dvp_contract
    ):
        issuer = default_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)
        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": "Cancel",
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
            ),
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
            json=req_param,
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "delivery not found",
        }
