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

from typing import Optional

import pytest
from sqlalchemy import select

from app.model.db import (
    Account,
    BatchIssueRedeem,
    BatchIssueRedeemProcessingCategory,
    BatchIssueRedeemUpload,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressAdditionalIssueBatchPOST:
    # target API endpoint
    base_url = "/share/tokens/{}/additional_issue/batch"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # One data
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        upload: Optional[BatchIssueRedeemUpload] = (
            await async_db.scalars(select(BatchIssueRedeemUpload).limit(1))
        ).first()
        assert upload.issuer_address == issuer_address
        assert upload.token_type == TokenType.IBET_SHARE
        assert upload.token_address == token_address
        assert upload.category == BatchIssueRedeemProcessingCategory.ISSUE
        assert upload.processed is False

        batch_data_list: list[BatchIssueRedeem] = (
            await async_db.scalars(select(BatchIssueRedeem))
        ).all()
        assert len(batch_data_list) == 1

        batch_data_1: BatchIssueRedeem = batch_data_list[0]
        assert batch_data_1.upload_id == upload.upload_id
        assert batch_data_1.account_address == req_param[0]["account_address"]
        assert batch_data_1.amount == req_param[0]["amount"]
        assert batch_data_1.status == 0

        assert resp.status_code == 200
        assert resp.json() == {"batch_id": upload.upload_id}

    # Normal_2
    # Multiple data
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]
        test_account_2 = config_eth_account("user3")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [
            {"account_address": test_account_1, "amount": 10},
            {"account_address": test_account_2, "amount": 20},
        ]
        resp = await async_client.post(
            self.base_url.format(token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        upload: Optional[BatchIssueRedeemUpload] = (
            await async_db.scalars(select(BatchIssueRedeemUpload).limit(1))
        ).first()
        assert upload.issuer_address == issuer_address
        assert upload.token_type == TokenType.IBET_SHARE
        assert upload.token_address == token_address
        assert upload.category == BatchIssueRedeemProcessingCategory.ISSUE
        assert upload.processed is False

        batch_data_list: list[BatchIssueRedeem] = (
            await async_db.scalars(select(BatchIssueRedeem))
        ).all()
        assert len(batch_data_list) == 2

        batch_data_1: BatchIssueRedeem = batch_data_list[0]
        assert batch_data_1.upload_id == upload.upload_id
        assert batch_data_1.account_address == req_param[0]["account_address"]
        assert batch_data_1.amount == req_param[0]["amount"]
        assert batch_data_1.status == 0

        batch_data_2: BatchIssueRedeem = batch_data_list[1]
        assert batch_data_2.upload_id == upload.upload_id
        assert batch_data_2.account_address == req_param[1]["account_address"]
        assert batch_data_2.amount == req_param[1]["amount"]
        assert batch_data_2.status == 0

        assert resp.status_code == 200
        assert resp.json() == {"batch_id": upload.upload_id}

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1_1
    # RequestValidationError: value is not a valid list
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {}  # not a list
        resp = await async_client.post(
            self.base_url.format(token_address),
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
                    "input": {},
                    "loc": ["body"],
                    "msg": "Input should be a valid list",
                    "type": "list_type",
                }
            ],
        }

    # Error_1_2
    # RequestValidationError: account_address is not a valid address
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": "0x0", "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address),
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
                    "ctx": {"error": {}},
                    "input": "0x0",
                    "loc": ["body", 0, "account_address"],
                    "msg": "Value error, invalid ethereum address",
                    "type": "value_error",
                }
            ],
        }

    # Error_1_3_1
    # RequestValidationError: amount is not greater than or equal to 1
    @pytest.mark.asyncio
    async def test_error_1_3_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 0}]
        resp = await async_client.post(
            self.base_url.format(token_address),
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
                    "loc": ["body", 0, "amount"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "greater_than_equal",
                }
            ],
        }

    # Error_1_3_2
    # RequestValidationError: amount is less than or equal to 100000000
    @pytest.mark.asyncio
    async def test_error_1_3_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 1_000_000_000_001}]
        resp = await async_client.post(
            self.base_url.format(token_address),
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
                    "loc": ["body", 0, "amount"],
                    "msg": "Input should be less than or equal to 1000000000000",
                    "type": "less_than_equal",
                }
            ],
        }

    # Error_1_4
    # RequestValidationError: header field is required
    @pytest.mark.asyncio
    async def test_error_1_4(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address), json=req_param, headers=None
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
                }
            ],
        }

    # Error_1_5
    # RequestValidationError: eoa-password is not a Base64-encoded encrypted data
    @pytest.mark.asyncio
    async def test_error_1_5(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address),
            json=req_param,
            headers={"issuer-address": issuer_address, "eoa-password": "password"},
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

    # Error_1_6
    # InvalidParameterError: list length must be at least one
    @pytest.mark.asyncio
    async def test_error_1_6(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = []
        resp = await async_client.post(
            self.base_url.format(token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "list length must be at least one",
        }

    # Error_1_7_1
    # AuthorizationError: issuer does not exist
    @pytest.mark.asyncio
    async def test_error_1_7_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = "different_issuer_address"  # different
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address),
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

    # Error_1_7_2
    # AuthorizationError: password mismatch
    @pytest.mark.asyncio
    async def test_error_1_7_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("wrong_password")  # wrong password
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address),
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

    # Error_1_8_1
    # Check token status
    # NotFound: token not found
    @pytest.mark.asyncio
    async def test_error_1_8_1(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # Error_1_8_2
    # Check token status
    # InvalidParameterError: this token is temporarily unavailable
    @pytest.mark.asyncio
    async def test_error_1_8_2(self, async_client, async_db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]

        test_account_1 = config_eth_account("user2")["address"]

        token_address = "token_address_test"

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.token_status = 0
        token.version = TokenVersion.V_24_09
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = [{"account_address": test_account_1, "amount": 10}]
        resp = await async_client.post(
            self.base_url.format(token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
