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

from unittest import mock

import pytest
from sqlalchemy import select

from app.model.db import (
    LedgerDataType,
    LedgerDetailsTemplate,
    LedgerTemplate,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import default_eth_account


class TestCreateUpdateLedgerTemplate:
    # target API endpoint
    base_url = "/ledger/{token_address}/template"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Create
    @mock.patch("app.routers.issuer.ledger.request_ledger_creation")
    @pytest.mark.asyncio
    async def test_normal_1(self, mock_func, async_client, async_db):
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_name": "テスト原簿",
            "headers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-1": "aaa-1",
                            "fuga-1": "bbb-1",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.IBET_FIN,
                        "source": token_address,
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-1": "aaa-1",
                            "f-fuga-1": "bbb-1",
                        },
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-2": "aaa-2",
                            "fuga-2": "bbb-2",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.DB,
                        "source": "data_id_2",
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-2": "aaa-2",
                            "f-fuga-2": "bbb-2",
                        },
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "f-hoge": "aaa",
                    "f-fuga": "bbb",
                },
            ],
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None
        _template = (await async_db.scalars(select(LedgerTemplate).limit(1))).first()
        assert _template.token_address == token_address
        assert _template.issuer_address == issuer_address
        assert _template.token_name == "テスト原簿"
        assert _template.headers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "hoge": "aaa",
                "fuga": "bbb",
            },
        ]
        assert _template.footers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge": "aaa",
                "f-fuga": "bbb",
            },
        ]
        _details_list = (
            await async_db.scalars(
                select(LedgerDetailsTemplate).order_by(LedgerDetailsTemplate.id)
            )
        ).all()
        assert len(_details_list) == 2
        _details = _details_list[0]
        assert _details.id == 1
        assert _details.token_address == token_address
        assert _details.token_detail_type == "権利_test_1"
        assert _details.headers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "hoge-1": "aaa-1",
                "fuga-1": "bbb-1",
            },
        ]
        assert _details.footers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-1": "aaa-1",
                "f-fuga-1": "bbb-1",
            },
        ]
        assert _details.data_type == LedgerDataType.IBET_FIN
        assert _details.data_source == token_address
        _details = _details_list[1]
        assert _details.id == 2
        assert _details.token_address == token_address
        assert _details.token_detail_type == "権利_test_2"
        assert _details.headers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "hoge-2": "aaa-2",
                "fuga-2": "bbb-2",
            },
        ]
        assert _details.footers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-2": "aaa-2",
                "f-fuga-2": "bbb-2",
            },
        ]
        assert _details.data_type == LedgerDataType.DB
        assert _details.data_source == "data_id_2"

    # <Normal_2>
    # Update
    @mock.patch("app.routers.issuer.ledger.request_ledger_creation")
    @pytest.mark.asyncio
    async def test_normal_2(self, mock_func, async_client, async_db):
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.token_name = "テスト原簿"
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "hoge": "aaa",
                "fuga": "bbb",
            },
        ]
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge": "aaa",
                "f-fuga": "bbb",
            },
        ]
        async_db.add(_template)

        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address
        _details_1.token_detail_type = "権利_test_2"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "hoge-2": "aaa-2",
                "fuga-2": "bbb-2",
            },
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-2": "aaa-2",
                "f-fuga-2": "bbb-2",
            },
        ]
        _details_1.data_type = LedgerDataType.DB
        _details_1.data_source = "data_id_1"
        async_db.add(_details_1)

        _details_2 = LedgerDetailsTemplate()
        _details_2.token_address = token_address
        _details_2.token_detail_type = "権利_test_3"
        _details_2.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "hoge-3": "aaa-3",
                "fuga-3": "bbb-3",
            },
        ]
        _details_2.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-3": "aaa-3",
                "f-fuga-3": "bbb-3",
            },
        ]
        _details_2.data_type = LedgerDataType.DB
        _details_2.data_source = "data_id_2"
        async_db.add(_details_2)

        await async_db.commit()

        # request target API
        req_param = {
            "token_name": "テスト原簿_update",
            "headers": [
                {
                    "key_update": "aaa_update",
                    "value_update": "bbb_update",
                },
                {
                    "hoge_update": "aaa_update",
                    "fuga_update": "bbb_update",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key_update": "aaa_update",
                            "value_update": "bbb_update",
                        },
                        {
                            "hoge-1": "aaa-1",
                            "fuga-1": "bbb-1",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.IBET_FIN,
                        "source": token_address,
                    },
                    "footers": [
                        {
                            "key_update": "aaa_update",
                            "value_update": "bbb_update",
                        },
                        {
                            "f-hoge-1": "aaa-1",
                            "f-fuga-1": "bbb-1",
                        },
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key_update": "aaa_update",
                            "value_update": "bbb_update",
                        },
                        {
                            "hoge-2_update": "aaa-2_update",
                            "fuga-2_update": "bbb-2_update",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.IBET_FIN,
                        "source": token_address,
                    },
                    "footers": [
                        {
                            "key_update": "aaa_update",
                            "value_update": "bbb_update",
                        },
                        {
                            "f-hoge-2_update": "aaa-2_update",
                            "f-fuga-2_update": "bbb-2_update",
                        },
                    ],
                },
            ],
            "footers": [
                {
                    "key_update": "aaa_update",
                    "value_update": "bbb_update",
                },
                {
                    "f-hoge_update": "aaa_update",
                    "f-fuga_update": "bbb_update",
                },
            ],
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        _template = (await async_db.scalars(select(LedgerTemplate).limit(1))).first()
        assert _template.token_address == token_address
        assert _template.issuer_address == issuer_address
        assert _template.token_name == "テスト原簿_update"
        assert _template.headers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "hoge_update": "aaa_update",
                "fuga_update": "bbb_update",
            },
        ]
        assert _template.footers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "f-hoge_update": "aaa_update",
                "f-fuga_update": "bbb_update",
            },
        ]
        _details_list = (
            await async_db.scalars(
                select(LedgerDetailsTemplate).order_by(LedgerDetailsTemplate.id)
            )
        ).all()
        assert len(_details_list) == 2
        _details = _details_list[0]
        assert _details.id == 1
        assert _details.token_address == token_address
        assert _details.token_detail_type == "権利_test_2"
        assert _details.headers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "hoge-2_update": "aaa-2_update",
                "fuga-2_update": "bbb-2_update",
            },
        ]
        assert _details.footers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "f-hoge-2_update": "aaa-2_update",
                "f-fuga-2_update": "bbb-2_update",
            },
        ]
        assert _details.data_type == LedgerDataType.IBET_FIN
        assert _details.data_source == token_address
        _details = _details_list[1]
        assert _details.id == 3
        assert _details.token_address == token_address
        assert _details.token_detail_type == "権利_test_1"
        assert _details.headers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "hoge-1": "aaa-1",
                "fuga-1": "bbb-1",
            },
        ]
        assert _details.footers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "f-hoge-1": "aaa-1",
                "f-fuga-1": "bbb-1",
            },
        ]
        assert _details.data_type == LedgerDataType.IBET_FIN
        assert _details.data_source == token_address

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
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

    # <Error_2>
    # Parameter Error(issuer-address)
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "token_name": "テスト原簿",
            "headers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-1": "aaa-1",
                            "fuga-1": "bbb-1",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.IBET_FIN,
                        "source": token_address,
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-1": "aaa-1",
                            "f-fuga-1": "bbb-1",
                        },
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-2": "aaa-2",
                            "fuga-2": "bbb-2",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.DB,
                        "source": "data_id_2",
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-2": "aaa-2",
                            "f-fuga-2": "bbb-2",
                        },
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "f-hoge": "aaa",
                    "f-fuga": "bbb",
                },
            ],
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_3>
    # Parameter Error(body request required)
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "dummy": "dummy",
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": {"dummy": "dummy"},
                    "loc": ["body", "token_name"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {"dummy": "dummy"},
                    "loc": ["body", "details"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_4>
    # Parameter Error(body request)
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "token_name": "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
            "1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
            "1",
            "headers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
            "details": [],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"max_length": 200},
                    "input": mock.ANY,
                    "loc": ["body", "token_name"],
                    "msg": "String should have at most 200 characters",
                    "type": "string_too_long",
                },
                {
                    "ctx": {"error": {}},
                    "input": [],
                    "loc": ["body", "details"],
                    "msg": "Value error, The length must be greater than or equal to 1",
                    "type": "value_error",
                },
            ],
        }

    # <Error_5>
    # Parameter Error(body request:details)
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "token_name": "テスト原簿",
            "headers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-1": "aaa-1",
                            "fuga-1": "bbb-1",
                        },
                    ],
                    "data": {
                        "type": "ibetfina",
                        "source": "1234567890123456789012345678901234567890123",
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-1": "d-aaa-1",
                            "f-fuga-1": "d-bbb-1",
                        },
                    ],
                },
                {
                    "dummy": "dummy",
                },
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-1": "aaa-1",
                            "fuga-1": "bbb-1",
                        },
                    ],
                    "data": {
                        "dummy": "dummy",
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-1": "aaa-1",
                            "f-fuga-1": "bbb-1",
                        },
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"max_length": 100},
                    "input": "12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901",
                    "loc": ["body", "details", 0, "token_detail_type"],
                    "msg": "String should have at most 100 characters",
                    "type": "string_too_long",
                },
                {
                    "ctx": {"expected": "'ibetfin' or 'db'"},
                    "input": "ibetfina",
                    "loc": ["body", "details", 0, "data", "type"],
                    "msg": "Input should be 'ibetfin' or 'db'",
                    "type": "enum",
                },
                {
                    "ctx": {"max_length": 42},
                    "input": "1234567890123456789012345678901234567890123",
                    "loc": ["body", "details", 0, "data", "source"],
                    "msg": "String should have at most 42 characters",
                    "type": "string_too_long",
                },
                {
                    "input": {"dummy": "dummy"},
                    "loc": ["body", "details", 1, "token_detail_type"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {"dummy": "dummy"},
                    "loc": ["body", "details", 1, "data"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {"dummy": "dummy"},
                    "loc": ["body", "details", 2, "data", "type"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_6>
    # Parameter Error(body request:headers/footers json)
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_name": "テスト原簿",
            "headers": {
                "hoge": "aaa",
                "fuga": "bbb",
            },
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": {
                        "hoge": "aaa",
                        "fuga": "bbb",
                    },
                    "data": {
                        "type": LedgerDataType.IBET_FIN,
                        "source": token_address,
                    },
                    "footers": {
                        "hoge": "aaa",
                        "fuga": "bbb",
                    },
                },
            ],
            "footers": {
                "hoge": "aaa",
                "fuga": "bbb",
            },
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": {"fuga": "bbb", "hoge": "aaa"},
                    "loc": ["body", "headers"],
                    "msg": "Input should be a valid list",
                    "type": "list_type",
                },
                {
                    "input": {"fuga": "bbb", "hoge": "aaa"},
                    "loc": ["body", "details", 0, "headers"],
                    "msg": "Input should be a valid list",
                    "type": "list_type",
                },
                {
                    "input": {"fuga": "bbb", "hoge": "aaa"},
                    "loc": ["body", "details", 0, "footers"],
                    "msg": "Input should be a valid list",
                    "type": "list_type",
                },
                {
                    "input": {"fuga": "bbb", "hoge": "aaa"},
                    "loc": ["body", "footers"],
                    "msg": "Input should be a valid list",
                    "type": "list_type",
                },
            ],
        }

    # <Error_7>
    # Token Not Found
    @pytest.mark.asyncio
    async def test_error_7(self, async_client, async_db):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "token_name": "テスト原簿",
            "headers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-1": "aaa-1",
                            "fuga-1": "bbb-1",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.IBET_FIN,
                        "source": token_address,
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-1": "aaa-1",
                            "f-fuga-1": "bbb-1",
                        },
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-2": "aaa-2",
                            "fuga-2": "bbb-2",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.DB,
                        "source": "data_id_2",
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-2": "aaa-2",
                            "f-fuga-2": "bbb-2",
                        },
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "f-hoge": "aaa",
                    "f-fuga": "bbb",
                },
            ],
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token does not exist",
        }

    # <Error_8>
    # Processing Token
    @pytest.mark.asyncio
    async def test_error_8(self, async_client, async_db):
        user_1 = default_eth_account("user1")
        issuer_address = user_1["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        req_param = {
            "token_name": "テスト原簿",
            "headers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "hoge": "aaa",
                    "fuga": "bbb",
                },
            ],
            "details": [
                {
                    "token_detail_type": "権利_test_1",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-1": "aaa-1",
                            "fuga-1": "bbb-1",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.IBET_FIN,
                        "source": token_address,
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-1": "aaa-1",
                            "f-fuga-1": "bbb-1",
                        },
                    ],
                },
                {
                    "token_detail_type": "権利_test_2",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "hoge-2": "aaa-2",
                            "fuga-2": "bbb-2",
                        },
                    ],
                    "data": {
                        "type": LedgerDataType.DB,
                        "source": "data_id_2",
                    },
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "f-hoge-2": "aaa-2",
                            "f-fuga-2": "bbb-2",
                        },
                    ],
                },
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "f-hoge": "aaa",
                    "f-fuga": "bbb",
                },
            ],
        }
        resp = await async_client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
