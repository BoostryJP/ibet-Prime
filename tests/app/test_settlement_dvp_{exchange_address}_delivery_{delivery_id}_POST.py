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

import asyncio
import hashlib

import pytest
from eth_keyfile import decode_keyfile_json

from app.model.blockchain import IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    Account,
    AuthToken,
    DVPAgentAccount,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from config import CHAIN_ID, TX_GAS_LIMIT
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


class TestUpdateDVPDeliveryPOST:
    # target API endpoint
    base_url = "/settlement/dvp/{exchange_address}/delivery/{delivery_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Cancel Delivery
    # Authorization by eoa-password
    def test_normal_1_1(
        self, ibet_security_token_dvp_contract, personal_info_contract, client, db
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = user_3["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        db.add(dvp_agent_account)

        token_contract_1 = asyncio.run(
            deploy_bond_token_contract(
                issuer_address,
                issuer_private_key,
                personal_info_contract.address,
                tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
            )
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

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

        # request target API
        req_param = {"operation_type": "Cancel"}
        resp = client.post(
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
    def test_normal_1_2(
        self, ibet_security_token_dvp_contract, personal_info_contract, client, db
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = user_3["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        db.add(dvp_agent_account)

        token_contract_1 = asyncio.run(
            deploy_bond_token_contract(
                issuer_address,
                issuer_private_key,
                personal_info_contract.address,
                tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
            )
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        auth_token = AuthToken()
        auth_token.issuer_address = issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        db.add(auth_token)

        db.commit()

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

        # request target API
        req_param = {"operation_type": "Cancel"}
        resp = client.post(
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

    # <Normal_2>
    # Finish Delivery
    def test_normal_2(
        self, ibet_security_token_dvp_contract, personal_info_contract, client, db
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = user_3["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        db.add(dvp_agent_account)

        token_contract_1 = asyncio.run(
            deploy_bond_token_contract(
                issuer_address,
                issuer_private_key,
                personal_info_contract.address,
                tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
            )
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

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

        # ConfirmDelivery
        tx = ibet_security_token_dvp_contract.functions.confirmDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # request target API
        req_param = {
            "operation_type": "Finish",
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address,
                delivery_id=1,
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_3>
    # Finish Delivery
    def test_normal_3(
        self, ibet_security_token_dvp_contract, personal_info_contract, client, db
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = user_3["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        db.add(dvp_agent_account)

        token_contract_1 = asyncio.run(
            deploy_bond_token_contract(
                issuer_address,
                issuer_private_key,
                personal_info_contract.address,
                tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
            )
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

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

        # ConfirmDelivery
        tx = ibet_security_token_dvp_contract.functions.confirmDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # request target API
        req_param = {
            "operation_type": "Finish",
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address,
                delivery_id=1,
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError: operation_type
    def test_error_1(self, client, db, ibet_security_token_dvp_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # request target API
        req_param = {"operation_type": "invalid_value"}

        resp = client.post(
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
                    "ctx": {"expected": "'Cancel'"},
                    "input": "invalid_value",
                    "loc": ["body", "CancelDVPDeliveryRequest", "operation_type"],
                    "msg": "Input should be 'Cancel'",
                    "type": "literal_error",
                },
                {
                    "ctx": {"expected": "'Finish'"},
                    "input": "invalid_value",
                    "loc": ["body", "FinishDVPDeliveryRequest", "operation_type"],
                    "msg": "Input should be 'Finish'",
                    "type": "literal_error",
                },
                {
                    "input": {"operation_type": "invalid_value"},
                    "loc": ["body", "FinishDVPDeliveryRequest", "account_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {"operation_type": "invalid_value"},
                    "loc": ["body", "FinishDVPDeliveryRequest", "eoa_password"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "ctx": {"expected": "'Abort'"},
                    "input": "invalid_value",
                    "loc": ["body", "AbortDVPDeliveryRequest", "operation_type"],
                    "msg": "Input should be 'Abort'",
                    "type": "literal_error",
                },
                {
                    "input": {"operation_type": "invalid_value"},
                    "loc": ["body", "AbortDVPDeliveryRequest", "account_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {"operation_type": "invalid_value"},
                    "loc": ["body", "AbortDVPDeliveryRequest", "eoa_password"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_2>
    # RequestValidationError: headers and body required
    def test_error_2(self, client, db, ibet_security_token_dvp_contract):
        # request target API
        resp = client.post(
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
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # <Error_3>
    # RequestValidationError: issuer-address
    def test_error_3(self, client, db, ibet_security_token_dvp_contract):
        test_account = config_eth_account("user1")
        issuer_address = test_account["address"]

        # request target API
        req_param = {
            "operation_type": "Cancel",
        }

        resp = client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
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

    # <Error_4>
    # RequestValidationError: eoa-password(not decrypt)
    def test_error_4(self, client, db, ibet_security_token_dvp_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        db.commit()

        # request target API
        req_param = {
            "operation_type": "Cancel",
        }

        resp = client.post(
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

    # <Error_5>
    # issuer does not exist
    def test_error_5(self, client, db, ibet_security_token_dvp_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = "0x0000000000000000000000000000000000000000"
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # request target API
        req_param = {
            "operation_type": "Cancel",
        }

        resp = client.post(
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

    # <Error_6>
    # password mismatch
    def test_error_6(self, client, db, ibet_security_token_dvp_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        db.commit()

        # request target API
        req_param = {
            "operation_type": "Cancel",
        }

        resp = client.post(
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

    # <Error_7>
    # DVP agent account not found
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    def test_error_7(
        self, operation_type, client, db, ibet_security_token_dvp_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        db.commit()

        # request target API
        req_param = {
            "operation_type": operation_type,
            "account_address": "0x0000000000000000000000000000000000000000",
            "eoa_password": "password",
        }

        resp = client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
            ),
            json=req_param,
        )

        assert resp.status_code == 404, resp.json()
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "agent account is not exists",
        }

    # <Error_8>
    # Send Transaction Error
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    def test_error_8(
        self,
        operation_type,
        client,
        db,
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
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = user_3["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        db.add(dvp_agent_account)

        token_contract_1 = asyncio.run(
            deploy_bond_token_contract(
                issuer_address,
                issuer_private_key,
                personal_info_contract.address,
                tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
            )
        )
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_contract_1.address
        token.abi = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

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

        # ConfirmDelivery
        tx = ibet_security_token_dvp_contract.functions.confirmDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # request target API
        req_param = {
            "operation_type": operation_type,
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address,
                delivery_id=2,
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": f"failed to {operation_type.lower()} delivery",
        }
