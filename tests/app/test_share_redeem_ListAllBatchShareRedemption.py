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

import uuid
from unittest import mock

import pytest

from app.model.db import (
    BatchIssueRedeemProcessingCategory,
    BatchIssueRedeemUpload,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import default_eth_account


class TestListAllBatchShareRedemption:
    # target API endpoint
    base_url = "/share/tokens/{}/redeem/batch"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal Case 1>
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "limit": None, "offset": None, "total": 0},
            "uploads": [],
        }

    # <Normal Case 2>
    # 1 record
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        redeem_upload1 = BatchIssueRedeemUpload()
        redeem_upload1.upload_id = str(uuid.uuid4())
        redeem_upload1.token_address = token_address
        redeem_upload1.issuer_address = issuer_address
        redeem_upload1.token_type = TokenType.IBET_SHARE
        redeem_upload1.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload1.processed = False
        async_db.add(redeem_upload1)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                }
            ],
        }

    # <Normal_3_1>
    # Multi record
    @pytest.mark.asyncio
    async def test_normal_3_1(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        redeem_upload1 = BatchIssueRedeemUpload()
        redeem_upload1.upload_id = str(uuid.uuid4())
        redeem_upload1.token_address = token_address
        redeem_upload1.issuer_address = issuer_address
        redeem_upload1.token_type = TokenType.IBET_SHARE
        redeem_upload1.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload1.processed = True
        async_db.add(redeem_upload1)

        redeem_upload2 = BatchIssueRedeemUpload()
        redeem_upload2.upload_id = str(uuid.uuid4())
        redeem_upload2.token_address = token_address
        redeem_upload2.issuer_address = issuer_address
        redeem_upload2.token_type = TokenType.IBET_SHARE
        redeem_upload2.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload2.processed = False
        async_db.add(redeem_upload2)

        redeem_upload3 = BatchIssueRedeemUpload()
        redeem_upload3.upload_id = str(uuid.uuid4())
        redeem_upload3.token_address = token_address
        redeem_upload3.issuer_address = issuer_address
        redeem_upload3.token_type = TokenType.IBET_SHARE
        redeem_upload3.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload3.processed = False
        async_db.add(redeem_upload3)

        redeem_upload4 = BatchIssueRedeemUpload()
        redeem_upload4.upload_id = str(uuid.uuid4())
        redeem_upload4.token_address = token_address
        redeem_upload4.issuer_address = issuer_address
        redeem_upload4.token_type = TokenType.IBET_SHARE
        redeem_upload4.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload4.processed = False
        async_db.add(redeem_upload4)

        redeem_upload5 = BatchIssueRedeemUpload()
        redeem_upload5.upload_id = str(uuid.uuid4())
        redeem_upload5.token_address = "other_token"
        redeem_upload5.issuer_address = issuer_address
        redeem_upload5.token_type = TokenType.IBET_SHARE
        redeem_upload5.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload5.processed = False
        async_db.add(redeem_upload5)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "limit": None, "offset": None, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": True,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
            ],
        }

    # <Normal_3_2>
    # Multi record (Issuer specified)
    @pytest.mark.asyncio
    async def test_normal_3_2(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        redeem_upload1 = BatchIssueRedeemUpload()
        redeem_upload1.upload_id = str(uuid.uuid4())
        redeem_upload1.token_address = token_address
        redeem_upload1.issuer_address = issuer_address
        redeem_upload1.token_type = TokenType.IBET_SHARE
        redeem_upload1.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload1.processed = True
        async_db.add(redeem_upload1)

        redeem_upload2 = BatchIssueRedeemUpload()
        redeem_upload2.upload_id = str(uuid.uuid4())
        redeem_upload2.token_address = token_address
        redeem_upload2.issuer_address = issuer_address
        redeem_upload2.token_type = TokenType.IBET_SHARE
        redeem_upload2.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload2.processed = False
        async_db.add(redeem_upload2)

        redeem_upload3 = BatchIssueRedeemUpload()
        redeem_upload3.upload_id = str(uuid.uuid4())
        redeem_upload3.token_address = token_address
        redeem_upload3.issuer_address = "other_issuer"
        redeem_upload3.token_type = TokenType.IBET_SHARE
        redeem_upload3.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload3.processed = False
        async_db.add(redeem_upload3)

        redeem_upload4 = BatchIssueRedeemUpload()
        redeem_upload4.upload_id = str(uuid.uuid4())
        redeem_upload4.token_address = token_address
        redeem_upload4.issuer_address = "other_issuer"
        redeem_upload4.token_type = TokenType.IBET_SHARE
        redeem_upload4.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload4.processed = False
        async_db.add(redeem_upload4)

        redeem_upload5 = BatchIssueRedeemUpload()
        redeem_upload5.upload_id = str(uuid.uuid4())
        redeem_upload5.token_address = "other_token"
        redeem_upload5.issuer_address = issuer_address
        redeem_upload5.token_type = TokenType.IBET_SHARE
        redeem_upload5.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload5.processed = False
        async_db.add(redeem_upload5)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(token_address),
            headers={"issuer-address": issuer_address},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 2},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": True,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
            ],
        }

    # <Normal_3_3>
    # Multi record (status)
    @pytest.mark.asyncio
    async def test_normal_3_3(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        redeem_upload1 = BatchIssueRedeemUpload()
        redeem_upload1.upload_id = str(uuid.uuid4())
        redeem_upload1.token_address = token_address
        redeem_upload1.issuer_address = issuer_address
        redeem_upload1.token_type = TokenType.IBET_SHARE
        redeem_upload1.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload1.processed = True
        async_db.add(redeem_upload1)

        redeem_upload2 = BatchIssueRedeemUpload()
        redeem_upload2.upload_id = str(uuid.uuid4())
        redeem_upload2.token_address = token_address
        redeem_upload2.issuer_address = issuer_address
        redeem_upload2.token_type = TokenType.IBET_SHARE
        redeem_upload2.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload2.processed = False
        async_db.add(redeem_upload2)

        redeem_upload3 = BatchIssueRedeemUpload()
        redeem_upload3.upload_id = str(uuid.uuid4())
        redeem_upload3.token_address = token_address
        redeem_upload3.issuer_address = issuer_address
        redeem_upload3.token_type = TokenType.IBET_SHARE
        redeem_upload3.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload3.processed = False
        async_db.add(redeem_upload3)

        redeem_upload4 = BatchIssueRedeemUpload()
        redeem_upload4.upload_id = str(uuid.uuid4())
        redeem_upload4.token_address = token_address
        redeem_upload4.issuer_address = issuer_address
        redeem_upload4.token_type = TokenType.IBET_SHARE
        redeem_upload4.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload4.processed = False
        async_db.add(redeem_upload4)

        redeem_upload5 = BatchIssueRedeemUpload()
        redeem_upload5.upload_id = str(uuid.uuid4())
        redeem_upload5.token_address = "other_token"
        redeem_upload5.issuer_address = issuer_address
        redeem_upload5.token_type = TokenType.IBET_SHARE
        redeem_upload5.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload5.processed = False
        async_db.add(redeem_upload5)

        await async_db.commit()

        # request target API
        req_param = {"processed": False}
        resp = await async_client.get(
            self.base_url.format(token_address), params=req_param
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
            ],
        }

    # <Normal_4>
    # Pagination
    @pytest.mark.asyncio
    async def test_normal_4(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        redeem_upload1 = BatchIssueRedeemUpload()
        redeem_upload1.upload_id = str(uuid.uuid4())
        redeem_upload1.token_address = token_address
        redeem_upload1.issuer_address = issuer_address
        redeem_upload1.token_type = TokenType.IBET_SHARE
        redeem_upload1.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload1.processed = True
        async_db.add(redeem_upload1)

        redeem_upload2 = BatchIssueRedeemUpload()
        redeem_upload2.upload_id = str(uuid.uuid4())
        redeem_upload2.token_address = token_address
        redeem_upload2.issuer_address = issuer_address
        redeem_upload2.token_type = TokenType.IBET_SHARE
        redeem_upload2.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload2.processed = False
        async_db.add(redeem_upload2)

        redeem_upload3 = BatchIssueRedeemUpload()
        redeem_upload3.upload_id = str(uuid.uuid4())
        redeem_upload3.token_address = token_address
        redeem_upload3.issuer_address = issuer_address
        redeem_upload3.token_type = TokenType.IBET_SHARE
        redeem_upload3.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload3.processed = False
        async_db.add(redeem_upload3)

        redeem_upload4 = BatchIssueRedeemUpload()
        redeem_upload4.upload_id = str(uuid.uuid4())
        redeem_upload4.token_address = token_address
        redeem_upload4.issuer_address = issuer_address
        redeem_upload4.token_type = TokenType.IBET_SHARE
        redeem_upload4.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload4.processed = False
        async_db.add(redeem_upload4)

        redeem_upload5 = BatchIssueRedeemUpload()
        redeem_upload5.upload_id = str(uuid.uuid4())
        redeem_upload5.token_address = "other_token"
        redeem_upload5.issuer_address = issuer_address
        redeem_upload5.token_type = TokenType.IBET_SHARE
        redeem_upload5.category = BatchIssueRedeemProcessingCategory.REDEEM
        redeem_upload5.processed = False
        async_db.add(redeem_upload5)

        await async_db.commit()

        # request target API
        req_param = {"limit": 2, "offset": 2}
        resp = await async_client.get(
            self.base_url.format(token_address), params=req_param
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "limit": 2, "offset": 2, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": True,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
            ],
        }

    # <Normal_5>
    # Sort
    @pytest.mark.asyncio
    async def test_normal_5(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        additional_issue_upload1 = BatchIssueRedeemUpload()
        additional_issue_upload1.upload_id = str(uuid.uuid4())
        additional_issue_upload1.token_address = token_address
        additional_issue_upload1.issuer_address = issuer_address
        additional_issue_upload1.token_type = TokenType.IBET_SHARE
        additional_issue_upload1.category = BatchIssueRedeemProcessingCategory.REDEEM
        additional_issue_upload1.processed = True
        async_db.add(additional_issue_upload1)

        additional_issue_upload2 = BatchIssueRedeemUpload()
        additional_issue_upload2.upload_id = str(uuid.uuid4())
        additional_issue_upload2.token_address = token_address
        additional_issue_upload2.issuer_address = issuer_address
        additional_issue_upload2.token_type = TokenType.IBET_SHARE
        additional_issue_upload2.category = BatchIssueRedeemProcessingCategory.REDEEM
        additional_issue_upload2.processed = False
        async_db.add(additional_issue_upload2)

        additional_issue_upload3 = BatchIssueRedeemUpload()
        additional_issue_upload3.upload_id = str(uuid.uuid4())
        additional_issue_upload3.token_address = token_address
        additional_issue_upload3.issuer_address = issuer_address
        additional_issue_upload3.token_type = TokenType.IBET_SHARE
        additional_issue_upload3.category = BatchIssueRedeemProcessingCategory.REDEEM
        additional_issue_upload3.processed = True
        async_db.add(additional_issue_upload3)

        additional_issue_upload4 = BatchIssueRedeemUpload()
        additional_issue_upload4.upload_id = str(uuid.uuid4())
        additional_issue_upload4.token_address = token_address
        additional_issue_upload4.issuer_address = issuer_address
        additional_issue_upload4.token_type = TokenType.IBET_SHARE
        additional_issue_upload4.category = BatchIssueRedeemProcessingCategory.REDEEM
        additional_issue_upload4.processed = False
        async_db.add(additional_issue_upload4)

        additional_issue_upload5 = BatchIssueRedeemUpload()
        additional_issue_upload5.upload_id = str(uuid.uuid4())
        additional_issue_upload5.token_address = "other_token"
        additional_issue_upload5.issuer_address = issuer_address
        additional_issue_upload5.token_type = TokenType.IBET_SHARE
        additional_issue_upload5.category = BatchIssueRedeemProcessingCategory.REDEEM
        additional_issue_upload5.processed = False
        async_db.add(additional_issue_upload5)

        await async_db.commit()

        # request target API
        req_param = {"sort_order": 0}
        resp = await async_client.get(
            self.base_url.format(token_address), params=req_param
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "limit": None, "offset": None, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "processed": True,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": True,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "processed": False,
                    "token_address": "token_address_test",
                    "token_type": "IbetShare",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # query(invalid value)
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        issuer_account = default_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = {}
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # request target API
        req_param = {"processed": "invalid_value"}
        resp = await async_client.get(
            self.base_url.format(token_address), params=req_param
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "input": "invalid_value",
                    "loc": ["query", "processed"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "type": "bool_parsing",
                }
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }
