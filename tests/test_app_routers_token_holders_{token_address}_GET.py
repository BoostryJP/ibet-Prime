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

from app.model.db import Token, TokenHolderBatchStatus, TokenHoldersList, TokenType
from tests.account_config import config_eth_account


class TestAppRoutersTokenHoldersGET:
    # target API endpoint
    base_url = "/token/holders/{}/collection"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal Case 1>
    # 0 record
    def test_normal_1(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = ""
        db.add(token)

        # request target API
        resp = client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "limit": None, "offset": None, "total": 0},
            "collections": [],
        }

    # <Normal Case 2>
    # 1 record
    def test_normal_2(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = ""
        db.add(token)

        token_holder_list1 = TokenHoldersList()
        token_holder_list1.token_address = token_address
        token_holder_list1.list_id = str(uuid.uuid4())
        token_holder_list1.block_number = 100
        token_holder_list1.batch_status = TokenHolderBatchStatus.PENDING.value
        db.add(token_holder_list1)

        # request target API
        resp = client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "collections": [
                {
                    "token_address": token_address,
                    "block_number": 100,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.PENDING.value,
                }
            ],
        }

    # <Normal_3_1>
    # Multi record
    def test_normal_3_1(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data

        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = ""
        db.add(token)

        token_holder_list1 = TokenHoldersList()
        token_holder_list1.token_address = token_address
        token_holder_list1.list_id = str(uuid.uuid4())
        token_holder_list1.block_number = 100
        token_holder_list1.batch_status = TokenHolderBatchStatus.PENDING.value
        db.add(token_holder_list1)

        db.commit()

        token_holder_list2 = TokenHoldersList()
        token_holder_list2.token_address = token_address
        token_holder_list2.list_id = str(uuid.uuid4())
        token_holder_list2.block_number = 200
        token_holder_list2.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list2)

        db.commit()

        token_holder_list3 = TokenHoldersList()
        token_holder_list3.token_address = token_address
        token_holder_list3.list_id = str(uuid.uuid4())
        token_holder_list3.block_number = 300
        token_holder_list3.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list3)

        db.commit()

        token_holder_list4 = TokenHoldersList()
        token_holder_list4.token_address = token_address
        token_holder_list4.list_id = str(uuid.uuid4())
        token_holder_list4.block_number = 400
        token_holder_list4.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list4)

        db.commit()

        token_holder_list5 = TokenHoldersList()
        token_holder_list5.token_address = token_address
        token_holder_list5.list_id = str(uuid.uuid4())
        token_holder_list5.block_number = 500
        token_holder_list5.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list5)

        db.commit()

        # request target API
        resp = client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "limit": None, "offset": None, "total": 5},
            "collections": [
                {
                    "token_address": token_address,
                    "block_number": 500,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.DONE.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 400,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.DONE.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 300,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 200,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 100,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.PENDING.value,
                },
            ],
        }

    # <Normal_3_2>
    # Multi record (Issuer specified)
    def test_normal_3_2(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = ""
        db.add(token)

        db.commit()

        token_holder_list1 = TokenHoldersList()
        token_holder_list1.token_address = token_address
        token_holder_list1.list_id = str(uuid.uuid4())
        token_holder_list1.block_number = 100
        token_holder_list1.batch_status = TokenHolderBatchStatus.PENDING.value
        db.add(token_holder_list1)

        db.commit()

        token_holder_list2 = TokenHoldersList()
        token_holder_list2.token_address = token_address
        token_holder_list2.list_id = str(uuid.uuid4())
        token_holder_list2.block_number = 200
        token_holder_list2.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list2)

        db.commit()

        token_holder_list3 = TokenHoldersList()
        token_holder_list3.token_address = token_address
        token_holder_list3.list_id = str(uuid.uuid4())
        token_holder_list3.block_number = 300
        token_holder_list3.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list3)

        db.commit()

        token_holder_list4 = TokenHoldersList()
        token_holder_list4.token_address = token_address
        token_holder_list4.list_id = str(uuid.uuid4())
        token_holder_list4.block_number = 400
        token_holder_list4.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list4)

        db.commit()

        token_holder_list5 = TokenHoldersList()
        token_holder_list5.token_address = token_address
        token_holder_list5.list_id = str(uuid.uuid4())
        token_holder_list5.block_number = 500
        token_holder_list5.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list5)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
            headers={"issuer-address": issuer_address},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "limit": None, "offset": None, "total": 5},
            "collections": [
                {
                    "token_address": token_address,
                    "block_number": 500,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.DONE.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 400,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.DONE.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 300,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 200,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 100,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.PENDING.value,
                },
            ],
        }

    # <Normal_3_3>
    # filter by status
    def test_normal_3_3(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = ""
        db.add(token)

        token_holder_list1 = TokenHoldersList()
        token_holder_list1.token_address = token_address
        token_holder_list1.list_id = str(uuid.uuid4())
        token_holder_list1.block_number = 100
        token_holder_list1.batch_status = TokenHolderBatchStatus.PENDING.value
        db.add(token_holder_list1)

        token_holder_list2 = TokenHoldersList()
        token_holder_list2.token_address = token_address
        token_holder_list2.list_id = str(uuid.uuid4())
        token_holder_list2.block_number = 200
        token_holder_list2.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list2)

        token_holder_list3 = TokenHoldersList()
        token_holder_list3.token_address = token_address
        token_holder_list3.list_id = str(uuid.uuid4())
        token_holder_list3.block_number = 300
        token_holder_list3.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list3)

        token_holder_list4 = TokenHoldersList()
        token_holder_list4.token_address = token_address
        token_holder_list4.list_id = str(uuid.uuid4())
        token_holder_list4.block_number = 400
        token_holder_list4.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list4)

        token_holder_list5 = TokenHoldersList()
        token_holder_list5.token_address = token_address
        token_holder_list5.list_id = str(uuid.uuid4())
        token_holder_list5.block_number = 500
        token_holder_list5.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list5)

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
            headers={"issuer-address": issuer_address},
            params={"status": str(TokenHolderBatchStatus.PENDING.value)},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 5},
            "collections": [
                {
                    "token_address": token_address,
                    "block_number": 100,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.PENDING.value,
                }
            ],
        }

    # <Normal_4>
    # Pagination
    def test_normal_4(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = ""
        db.add(token)

        db.commit()

        token_holder_list1 = TokenHoldersList()
        token_holder_list1.token_address = token_address
        token_holder_list1.list_id = str(uuid.uuid4())
        token_holder_list1.block_number = 100
        token_holder_list1.batch_status = TokenHolderBatchStatus.PENDING.value
        db.add(token_holder_list1)

        db.commit()

        token_holder_list2 = TokenHoldersList()
        token_holder_list2.token_address = token_address
        token_holder_list2.list_id = str(uuid.uuid4())
        token_holder_list2.block_number = 200
        token_holder_list2.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list2)

        db.commit()

        token_holder_list3 = TokenHoldersList()
        token_holder_list3.token_address = token_address
        token_holder_list3.list_id = str(uuid.uuid4())
        token_holder_list3.block_number = 300
        token_holder_list3.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list3)

        token_holder_list4 = TokenHoldersList()
        token_holder_list4.token_address = token_address
        token_holder_list4.list_id = str(uuid.uuid4())
        token_holder_list4.block_number = 400
        token_holder_list4.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list4)

        db.commit()

        token_holder_list5 = TokenHoldersList()
        token_holder_list5.token_address = token_address
        token_holder_list5.list_id = str(uuid.uuid4())
        token_holder_list5.block_number = 500
        token_holder_list5.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list5)

        # request target API
        req_param = {"limit": 2, "offset": 2}
        resp = client.get(self.base_url.format(token_address), params=req_param)

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "limit": 2, "offset": 2, "total": 5},
            "collections": [
                {
                    "token_address": token_address,
                    "block_number": 300,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 200,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
            ],
        }

    # <Normal_5>
    # Sort
    def test_normal_5(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.abi = ""
        db.add(token)

        token_holder_list1 = TokenHoldersList()
        token_holder_list1.token_address = token_address
        token_holder_list1.list_id = str(uuid.uuid4())
        token_holder_list1.block_number = 100
        token_holder_list1.batch_status = TokenHolderBatchStatus.PENDING.value
        db.add(token_holder_list1)

        token_holder_list2 = TokenHoldersList()
        token_holder_list2.token_address = token_address
        token_holder_list2.list_id = str(uuid.uuid4())
        token_holder_list2.block_number = 200
        token_holder_list2.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list2)

        token_holder_list3 = TokenHoldersList()
        token_holder_list3.token_address = token_address
        token_holder_list3.list_id = str(uuid.uuid4())
        token_holder_list3.block_number = 300
        token_holder_list3.batch_status = TokenHolderBatchStatus.FAILED.value
        db.add(token_holder_list3)

        token_holder_list4 = TokenHoldersList()
        token_holder_list4.token_address = token_address
        token_holder_list4.list_id = str(uuid.uuid4())
        token_holder_list4.block_number = 400
        token_holder_list4.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list4)

        token_holder_list5 = TokenHoldersList()
        token_holder_list5.token_address = token_address
        token_holder_list5.list_id = str(uuid.uuid4())
        token_holder_list5.block_number = 500
        token_holder_list5.batch_status = TokenHolderBatchStatus.DONE.value
        db.add(token_holder_list5)

        # request target API
        req_param = {"sort_order": 0}
        resp = client.get(self.base_url.format(token_address), params=req_param)

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "limit": None, "offset": None, "total": 5},
            "collections": [
                {
                    "token_address": token_address,
                    "block_number": 100,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.PENDING.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 200,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 300,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.FAILED.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 400,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.DONE.value,
                },
                {
                    "token_address": token_address,
                    "block_number": 500,
                    "list_id": mock.ANY,
                    "status": TokenHolderBatchStatus.DONE.value,
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
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

    # <Error_2>
    # Token Not Found
    def test_error_2(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]

        # request target API
        resp = client.get(
            self.base_url.format("invalid_address"),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "detail": "token not found",
            "meta": {"code": 1, "title": "NotFound"},
        }

    # <Error_3>
    # Token status pending
    def test_error_3(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        token_address = "token_address_test"

        # prepare data
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = issuer_address
        token.token_address = token_address
        token.token_status = 0
        token.abi = ""
        db.add(token)

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "detail": "this token is temporarily unavailable",
            "meta": {"code": 1, "title": "InvalidParameterError"},
        }
