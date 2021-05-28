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
from app.model.db import (
    Token,
    TokenType,
    LedgerTemplate,
    LedgerDetailsTemplate,
    LedgerDetailsDataType
)
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressTemplatePOST:
    # target API endpoint
    base_url = "/ledger/{token_address}/template"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Create
    def test_normal_1(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

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
                }
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
                        }
                    ],
                    "data": {
                        "type": LedgerDetailsDataType.IBET_FIN,
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
                        }
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
                        }
                    ],
                    "data": {
                        "type": LedgerDetailsDataType.DB,
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
                        }
                    ],
                }
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "f-hoge": "aaa",
                    "f-fuga": "bbb",
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        _template = db.query(LedgerTemplate). \
            first()
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
            }
        ]
        assert _template.footers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge": "aaa",
                "f-fuga": "bbb",
            }
        ]
        _details_list = db.query(LedgerDetailsTemplate). \
            order_by(LedgerDetailsTemplate.id). \
            all()
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
            }
        ]
        assert _details.footers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-1": "aaa-1",
                "f-fuga-1": "bbb-1",
            }
        ]
        assert _details.data_type == LedgerDetailsDataType.IBET_FIN
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
            }
        ]
        assert _details.footers == [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-2": "aaa-2",
                "f-fuga-2": "bbb-2",
            }
        ]
        assert _details.data_type == LedgerDetailsDataType.DB
        assert _details.data_source == "data_id_2"

    # <Normal_2>
    # Update
    def test_normal_2(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

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
            }
        ]
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge": "aaa",
                "f-fuga": "bbb",
            }
        ]
        db.add(_template)

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
            }
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-2": "aaa-2",
                "f-fuga-2": "bbb-2",
            }
        ]
        _details_1.data_type = LedgerDetailsDataType.DB
        _details_1.data_source = "data_id_1"
        db.add(_details_1)

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
            }
        ]
        _details_2.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-hoge-3": "aaa-3",
                "f-fuga-3": "bbb-3",
            }
        ]
        _details_2.data_type = LedgerDetailsDataType.DB
        _details_2.data_source = "data_id_2"
        db.add(_details_2)

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
                }
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
                        }
                    ],
                    "data": {
                        "type": LedgerDetailsDataType.IBET_FIN,
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
                        }
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
                        "type": LedgerDetailsDataType.IBET_FIN,
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
                        }
                    ],
                }
            ],
            "footers": [
                {
                    "key_update": "aaa_update",
                    "value_update": "bbb_update",
                },
                {
                    "f-hoge_update": "aaa_update",
                    "f-fuga_update": "bbb_update",
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        _template = db.query(LedgerTemplate). \
            first()
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
            }
        ]
        assert _template.footers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "f-hoge_update": "aaa_update",
                "f-fuga_update": "bbb_update",
            }
        ]
        _details_list = db.query(LedgerDetailsTemplate). \
            order_by(LedgerDetailsTemplate.id). \
            all()
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
            }
        ]
        assert _details.footers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "f-hoge-2_update": "aaa-2_update",
                "f-fuga-2_update": "bbb-2_update",
            }
        ]
        assert _details.data_type == LedgerDetailsDataType.IBET_FIN
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
            }
        ]
        assert _details.footers == [
            {
                "key_update": "aaa_update",
                "value_update": "bbb_update",
            },
            {
                "f-hoge-1": "aaa-1",
                "f-fuga-1": "bbb-1",
            }
        ]
        assert _details.data_type == LedgerDetailsDataType.IBET_FIN
        assert _details.data_source == token_address

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.post(
            self.base_url.format(token_address=token_address),
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_2>
    # Parameter Error(issuer-address)
    def test_error_2(self, client, db):
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
                }
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
                        }
                    ],
                    "data": {
                        "type": LedgerDetailsDataType.IBET_FIN,
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
                        }
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
                        }
                    ],
                    "data": {
                        "type": LedgerDetailsDataType.DB,
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
                        }
                    ],
                }
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "f-hoge": "aaa",
                    "f-fuga": "bbb",
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": "test",
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_3>
    # Parameter Error(body request required)
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        req_param = {
            "dummy": "dummy",
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "token_name"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "details"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_4>
    # Parameter Error(body request)
    def test_error_4(self, client, db):
        user = config_eth_account("user1")
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
                }
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
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "token_name"],
                    "msg": "The length must be less than or equal to 200",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "details"],
                    "msg": "The length must be greater than or equal to 1",
                    "type": "value_error"
                }
            ]
        }

    # <Error_5>
    # Parameter Error(body request:details)
    def test_error_5(self, client, db):
        user = config_eth_account("user1")
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
                }
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
                        }
                    ],
                    "data": {
                        "type": "123456789012345678901",
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
                        }
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
                        }
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
                        }
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
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "details", 0, "token_detail_type"],
                    "msg": "The length must be less than or equal to 100",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "details", 0, "data", "type"],
                    "msg": "The length must be less than or equal to 20",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "details", 0, "data", "source"],
                    "msg": "The length must be less than or equal to 42",
                    "type": "value_error"
                },
                {
                    "loc": ["body", "details", 1, "token_detail_type"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "details", 1, "data"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "details", 2, "data", "type"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_6>
    # Parameter Error(body request:headers/footers json)
    def test_error_6(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

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
                        "type": LedgerDetailsDataType.IBET_FIN,
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
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "headers"],
                    "msg": "value is not a valid list",
                    "type": "type_error.list"
                },
                {
                    "loc": ["body", "details", 0, "headers"],
                    "msg": "value is not a valid list",
                    "type": "type_error.list"
                },
                {
                    "loc": ["body", "details", 0, "footers"],
                    "msg": "value is not a valid list",
                    "type": "type_error.list"
                },
                {
                    "loc": ["body", "footers"],
                    "msg": "value is not a valid list",
                    "type": "type_error.list"
                },
            ]
        }

    # <Error_7>
    # Token Not Found
    def test_error_7(self, client, db):
        user_1 = config_eth_account("user1")
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
                }
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
                        }
                    ],
                    "data": {
                        "type": LedgerDetailsDataType.IBET_FIN,
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
                        }
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
                        }
                    ],
                    "data": {
                        "type": LedgerDetailsDataType.DB,
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
                        }
                    ],
                }
            ],
            "footers": [
                {
                    "key": "aaa",
                    "value": "bbb",
                },
                {
                    "f-hoge": "aaa",
                    "f-fuga": "bbb",
                }
            ],
        }
        resp = client.post(
            self.base_url.format(token_address=token_address),
            json=req_param,
            headers={
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "token does not exist"
        }
