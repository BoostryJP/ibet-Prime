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

from collections.abc import Generator
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import SendTransactionError
from app.model.db import Account, AccountRsaStatus, DVPAgentAccount
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import default_eth_account

DVP_CONTRACT_ADDRESS = "0x1111111111111111111111111111111111111111"


@pytest.fixture(autouse=True)
def settlement_blockchain_mocks() -> Generator[None, None, None]:
    async def finish_delivery(
        *, tx_params: object, **_: object
    ) -> tuple[str, MagicMock]:
        if getattr(tx_params, "delivery_id", 0) == 2:
            raise SendTransactionError("finish transaction error")
        return "finish_tx_hash", MagicMock()

    async def abort_delivery(
        *, tx_params: object, **_: object
    ) -> tuple[str, MagicMock]:
        if getattr(tx_params, "delivery_id", 0) == 2:
            raise SendTransactionError("abort transaction error")
        return "abort_tx_hash", MagicMock()

    with (
        patch(
            "app.routers.misc.settlement_agent.IbetSecurityTokenDVP.finish_delivery",
            new=AsyncMock(side_effect=finish_delivery),
        ),
        patch(
            "app.routers.misc.settlement_agent.IbetSecurityTokenDVP.abort_delivery",
            new=AsyncMock(side_effect=abort_delivery),
        ),
    ):
        yield


class TestUpdateDVPAgentDelivery:
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
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        issuer = default_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        agent = default_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": "Finish",
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=DVP_CONTRACT_ADDRESS,
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
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        issuer = default_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        agent = default_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": "Abort",
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=DVP_CONTRACT_ADDRESS,
                delivery_id=1,
            ),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

    # <Normal_3>
    # DEDICATED_DVP_AGENT_MODE = True
    @pytest.mark.asyncio
    @mock.patch("app.routers.misc.settlement_agent.DEDICATED_DVP_AGENT_MODE", True)
    @mock.patch(
        "app.routers.misc.settlement_agent.DEDICATED_DVP_AGENT_ID", "test_agent_0"
    )
    async def test_normal_3(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        issuer = default_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        agent = default_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        dvp_agent_account.dedicated_agent_id = "test_agent_0"
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": "Finish",
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=DVP_CONTRACT_ADDRESS,
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

    # <Error_1_1>
    # Invalid operation_type value
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_1(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": "InvalidOperation",  # invalid value
            "account_address": "0x0000000000000000000000000000000000000000",
            "eoa_password": E2EEUtils.encrypt("password"),
        }

        resp = await async_client.post(
            self.base_url.format(exchange_address=DVP_CONTRACT_ADDRESS, delivery_id=1),
            json=req_param,
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "literal_error",
                    "loc": ["body", "FinishDVPDeliveryRequest", "operation_type"],
                    "msg": "Input should be 'Finish'",
                    "input": "InvalidOperation",
                    "ctx": {"expected": "'Finish'"},
                },
                {
                    "type": "literal_error",
                    "loc": ["body", "AbortDVPDeliveryRequest", "operation_type"],
                    "msg": "Input should be 'Abort'",
                    "input": "InvalidOperation",
                    "ctx": {"expected": "'Abort'"},
                },
            ],
        }

    # <Error_1_2>
    @pytest.mark.asyncio
    async def test_error_1_2(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": "Finish",
            "account_address": "invalid_address",  # invalid address
            "eoa_password": E2EEUtils.encrypt("password"),
        }

        resp = await async_client.post(
            self.base_url.format(exchange_address=DVP_CONTRACT_ADDRESS, delivery_id=1),
            json=req_param,
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "FinishDVPDeliveryRequest", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
                {
                    "type": "literal_error",
                    "loc": ["body", "AbortDVPDeliveryRequest", "operation_type"],
                    "msg": "Input should be 'Abort'",
                    "input": "Finish",
                    "ctx": {"expected": "'Abort'"},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "AbortDVPDeliveryRequest", "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "invalid_address",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_1_3>
    # Not encrypted value for eoa_password
    # -> RequestValidationError
    @pytest.mark.asyncio
    async def test_error_1_3(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": "Finish",
            "account_address": "0x0000000000000000000000000000000000000000",
            "eoa_password": "password",  # not encrypted value
        }

        resp = await async_client.post(
            self.base_url.format(exchange_address=DVP_CONTRACT_ADDRESS, delivery_id=1),
            json=req_param,
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "FinishDVPDeliveryRequest", "eoa_password"],
                    "msg": "Value error, eoa_password is not a Base64-encoded encrypted data",
                    "input": "password",
                    "ctx": {"error": {}},
                },
                {
                    "type": "literal_error",
                    "loc": ["body", "AbortDVPDeliveryRequest", "operation_type"],
                    "msg": "Input should be 'Abort'",
                    "input": "Finish",
                    "ctx": {"expected": "'Abort'"},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "AbortDVPDeliveryRequest", "eoa_password"],
                    "msg": "Value error, eoa_password is not a Base64-encoded encrypted data",
                    "input": "password",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_2>
    # DVP agent account not found
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    async def test_error_2(
        self,
        operation_type: str,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        _keyfile = user_1["keyfile_json"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": operation_type,
            "account_address": "0x0000000000000000000000000000000000000000",
            "eoa_password": E2EEUtils.encrypt("password"),
        }

        resp = await async_client.post(
            self.base_url.format(exchange_address=DVP_CONTRACT_ADDRESS, delivery_id=1),
            json=req_param,
        )

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "agent account is not exists",
        }

    # <Error_3>
    # DVP agent password mismatch
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    async def test_error_3(
        self,
        operation_type: str,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        issuer = default_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        agent = default_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": operation_type,
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("invalid_password"),
        }

        resp = await async_client.post(
            self.base_url.format(exchange_address=DVP_CONTRACT_ADDRESS, delivery_id=1),
            json=req_param,
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "password mismatch",
        }

    # <Error_4>
    # Send Transaction Error
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation_type",
        ["Finish", "Abort"],
    )
    async def test_error_4(
        self,
        operation_type: str,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        issuer = default_eth_account("user1")
        issuer_address = issuer["address"]
        _keyfile = issuer["keyfile_json"]
        agent = default_eth_account("user3")
        agent_address = agent["address"]

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        dvp_agent_account = DVPAgentAccount()
        dvp_agent_account.account_address = agent_address
        dvp_agent_account.keyfile = agent["keyfile_json"]
        dvp_agent_account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(dvp_agent_account)

        await async_db.commit()

        # request target API
        req_param = {
            "operation_type": operation_type,
            "account_address": agent_address,
            "eoa_password": E2EEUtils.encrypt("password"),
        }
        resp = await async_client.post(
            self.base_url.format(
                exchange_address=DVP_CONTRACT_ADDRESS,
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
