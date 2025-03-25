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

from app.model.blockchain import IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import Account, DVPAgentAccount, Token, TokenType, TokenVersion
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


class TestUpdateDVPDelivery:
    # target API endpoint
    base_url = "/settlement/dvp/agent/{exchange_address}/delivery/{delivery_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Finish Delivery
    @pytest.mark.asyncio
    async def test_normal_1(
        self,
        ibet_security_token_dvp_contract,
        personal_info_contract,
        async_client,
        async_db,
    ):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )

        user = config_eth_account("user2")
        user_address_1 = user["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user["keyfile_json"], password="password".encode("utf-8")
        )

        agent = config_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

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
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address,
                delivery_id=1,
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_2>
    # Abort Delivery
    @pytest.mark.asyncio
    async def test_normal_2(
        self,
        ibet_security_token_dvp_contract,
        personal_info_contract,
        async_client,
        async_db,
    ):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )

        user = config_eth_account("user2")
        user_address_1 = user["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user["keyfile_json"], password="password".encode("utf-8")
        )

        agent = config_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

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
            "operation_type": "Abort",
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = await async_client.post(
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
    # DVP agent account not found
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    async def test_error_1(
        self, operation_type, async_client, async_db, ibet_security_token_dvp_contract
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
            "operation_type": operation_type,
            "account_address": "0x0000000000000000000000000000000000000000",
            "eoa_password": "password",
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
            ),
            json=req_param,
        )

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "agent account is not exists",
        }

    # <Error_2>
    # DVP agent password mismatch
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    async def test_error_2(
        self,
        operation_type,
        async_client,
        async_db,
        ibet_security_token_dvp_contract,
        personal_info_contract,
    ):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )

        agent = config_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

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
            "operation_type": operation_type,
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("invalid_password"),
        }

        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address, delivery_id=1
            ),
            json=req_param,
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "password mismatch",
        }

    # <Error_3>
    # Send Transaction Error
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    async def test_error_3(
        self,
        operation_type,
        async_client,
        async_db,
        ibet_security_token_dvp_contract,
        personal_info_contract,
    ):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )

        user_1 = config_eth_account("user2")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        agent = config_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

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
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=ibet_security_token_dvp_contract.address,
                delivery_id=2,
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": f"failed to {operation_type.lower()} delivery",
        }
