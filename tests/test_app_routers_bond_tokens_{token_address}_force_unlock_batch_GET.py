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

from app.model.db import BatchForceUnlockUpload, Token, TokenType
from tests.account_config import config_eth_account


class TestAppRoutersBondTokensTokenAddressForceUnlockBatchGET:
    # target API endpoint
    base_url = "/bond/tokens/{}/force_unlock/batch"

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
            "uploads": [],
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

        force_unlock_upload1 = BatchForceUnlockUpload()
        force_unlock_upload1.batch_id = str(uuid.uuid4())
        force_unlock_upload1.token_address = token_address
        force_unlock_upload1.issuer_address = issuer_address
        force_unlock_upload1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload1.status = 0
        db.add(force_unlock_upload1)

        # request target API
        resp = client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "uploads": [
                {
                    "batch_id": mock.ANY,
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "created": mock.ANY,
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

        force_unlock_upload1 = BatchForceUnlockUpload()
        force_unlock_upload1.batch_id = str(uuid.uuid4())
        force_unlock_upload1.token_address = token_address
        force_unlock_upload1.issuer_address = issuer_address
        force_unlock_upload1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload1.status = 1
        db.add(force_unlock_upload1)

        force_unlock_upload2 = BatchForceUnlockUpload()
        force_unlock_upload2.batch_id = str(uuid.uuid4())
        force_unlock_upload2.token_address = token_address
        force_unlock_upload2.issuer_address = issuer_address
        force_unlock_upload2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload2.status = 0
        db.add(force_unlock_upload2)

        force_unlock_upload3 = BatchForceUnlockUpload()
        force_unlock_upload3.batch_id = str(uuid.uuid4())
        force_unlock_upload3.token_address = token_address
        force_unlock_upload3.issuer_address = issuer_address
        force_unlock_upload3.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload3.status = 0
        db.add(force_unlock_upload3)

        force_unlock_upload4 = BatchForceUnlockUpload()
        force_unlock_upload4.batch_id = str(uuid.uuid4())
        force_unlock_upload4.token_address = token_address
        force_unlock_upload4.issuer_address = issuer_address
        force_unlock_upload4.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload4.status = 0
        db.add(force_unlock_upload4)

        force_unlock_upload5 = BatchForceUnlockUpload()
        force_unlock_upload5.batch_id = str(uuid.uuid4())
        force_unlock_upload5.token_address = "other_token"
        force_unlock_upload5.issuer_address = issuer_address
        force_unlock_upload5.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload5.status = 0
        db.add(force_unlock_upload5)

        # request target API
        resp = client.get(self.base_url.format(token_address), headers={})

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "limit": None, "offset": None, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 1,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
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

        force_unlock_upload1 = BatchForceUnlockUpload()
        force_unlock_upload1.batch_id = str(uuid.uuid4())
        force_unlock_upload1.token_address = token_address
        force_unlock_upload1.issuer_address = issuer_address
        force_unlock_upload1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload1.status = 1
        db.add(force_unlock_upload1)

        force_unlock_upload2 = BatchForceUnlockUpload()
        force_unlock_upload2.batch_id = str(uuid.uuid4())
        force_unlock_upload2.token_address = token_address
        force_unlock_upload2.issuer_address = issuer_address
        force_unlock_upload2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload2.status = 0
        db.add(force_unlock_upload2)

        force_unlock_upload3 = BatchForceUnlockUpload()
        force_unlock_upload3.batch_id = str(uuid.uuid4())
        force_unlock_upload3.token_address = token_address
        force_unlock_upload3.issuer_address = "other_issuer"
        force_unlock_upload3.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload3.status = 0
        db.add(force_unlock_upload3)

        force_unlock_upload4 = BatchForceUnlockUpload()
        force_unlock_upload4.batch_id = str(uuid.uuid4())
        force_unlock_upload4.token_address = token_address
        force_unlock_upload4.issuer_address = "other_issuer"
        force_unlock_upload4.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload4.status = 0
        db.add(force_unlock_upload4)

        force_unlock_upload5 = BatchForceUnlockUpload()
        force_unlock_upload5.batch_id = str(uuid.uuid4())
        force_unlock_upload5.token_address = "other_token"
        force_unlock_upload5.issuer_address = issuer_address
        force_unlock_upload5.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload5.status = 0
        db.add(force_unlock_upload5)

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
            headers={"issuer-address": issuer_address},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 2},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 1,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
            ],
        }

    # <Normal_3_3>
    # Multi record (status)
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

        force_unlock_upload1 = BatchForceUnlockUpload()
        force_unlock_upload1.batch_id = str(uuid.uuid4())
        force_unlock_upload1.token_address = token_address
        force_unlock_upload1.issuer_address = issuer_address
        force_unlock_upload1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload1.status = 1
        db.add(force_unlock_upload1)

        force_unlock_upload2 = BatchForceUnlockUpload()
        force_unlock_upload2.batch_id = str(uuid.uuid4())
        force_unlock_upload2.token_address = token_address
        force_unlock_upload2.issuer_address = issuer_address
        force_unlock_upload2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload2.status = 0
        db.add(force_unlock_upload2)

        force_unlock_upload3 = BatchForceUnlockUpload()
        force_unlock_upload3.batch_id = str(uuid.uuid4())
        force_unlock_upload3.token_address = token_address
        force_unlock_upload3.issuer_address = issuer_address
        force_unlock_upload3.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload3.status = 0
        db.add(force_unlock_upload3)

        force_unlock_upload4 = BatchForceUnlockUpload()
        force_unlock_upload4.batch_id = str(uuid.uuid4())
        force_unlock_upload4.token_address = token_address
        force_unlock_upload4.issuer_address = issuer_address
        force_unlock_upload4.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload4.status = 0
        db.add(force_unlock_upload4)

        force_unlock_upload5 = BatchForceUnlockUpload()
        force_unlock_upload5.batch_id = str(uuid.uuid4())
        force_unlock_upload5.token_address = "other_token"
        force_unlock_upload5.issuer_address = issuer_address
        force_unlock_upload5.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload5.status = 0
        db.add(force_unlock_upload5)

        # request target API
        req_param = {"status": 0}
        resp = client.get(self.base_url.format(token_address), params=req_param)

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
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

        force_unlock_upload1 = BatchForceUnlockUpload()
        force_unlock_upload1.batch_id = str(uuid.uuid4())
        force_unlock_upload1.token_address = token_address
        force_unlock_upload1.issuer_address = issuer_address
        force_unlock_upload1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload1.status = 1
        db.add(force_unlock_upload1)

        force_unlock_upload2 = BatchForceUnlockUpload()
        force_unlock_upload2.batch_id = str(uuid.uuid4())
        force_unlock_upload2.token_address = token_address
        force_unlock_upload2.issuer_address = issuer_address
        force_unlock_upload2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload2.status = 0
        db.add(force_unlock_upload2)

        force_unlock_upload3 = BatchForceUnlockUpload()
        force_unlock_upload3.batch_id = str(uuid.uuid4())
        force_unlock_upload3.token_address = token_address
        force_unlock_upload3.issuer_address = issuer_address
        force_unlock_upload3.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload3.status = 0
        db.add(force_unlock_upload3)

        force_unlock_upload4 = BatchForceUnlockUpload()
        force_unlock_upload4.batch_id = str(uuid.uuid4())
        force_unlock_upload4.token_address = token_address
        force_unlock_upload4.issuer_address = issuer_address
        force_unlock_upload4.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload4.status = 0
        db.add(force_unlock_upload4)

        force_unlock_upload5 = BatchForceUnlockUpload()
        force_unlock_upload5.batch_id = str(uuid.uuid4())
        force_unlock_upload5.token_address = "other_token"
        force_unlock_upload5.issuer_address = issuer_address
        force_unlock_upload5.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload5.status = 0
        db.add(force_unlock_upload5)

        # request target API
        req_param = {"limit": 2, "offset": 2}
        resp = client.get(self.base_url.format(token_address), params=req_param)

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "limit": 2, "offset": 2, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 1,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
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

        force_unlock_upload1 = BatchForceUnlockUpload()
        force_unlock_upload1.batch_id = str(uuid.uuid4())
        force_unlock_upload1.token_address = token_address
        force_unlock_upload1.issuer_address = issuer_address
        force_unlock_upload1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload1.status = 1
        db.add(force_unlock_upload1)

        force_unlock_upload2 = BatchForceUnlockUpload()
        force_unlock_upload2.batch_id = str(uuid.uuid4())
        force_unlock_upload2.token_address = token_address
        force_unlock_upload2.issuer_address = issuer_address
        force_unlock_upload2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload2.status = 0
        db.add(force_unlock_upload2)

        force_unlock_upload3 = BatchForceUnlockUpload()
        force_unlock_upload3.batch_id = str(uuid.uuid4())
        force_unlock_upload3.token_address = token_address
        force_unlock_upload3.issuer_address = issuer_address
        force_unlock_upload3.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload3.status = 1
        db.add(force_unlock_upload3)

        force_unlock_upload4 = BatchForceUnlockUpload()
        force_unlock_upload4.batch_id = str(uuid.uuid4())
        force_unlock_upload4.token_address = token_address
        force_unlock_upload4.issuer_address = issuer_address
        force_unlock_upload4.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload4.status = 0
        db.add(force_unlock_upload4)

        force_unlock_upload5 = BatchForceUnlockUpload()
        force_unlock_upload5.batch_id = str(uuid.uuid4())
        force_unlock_upload5.token_address = "other_token"
        force_unlock_upload5.issuer_address = issuer_address
        force_unlock_upload5.token_type = TokenType.IBET_STRAIGHT_BOND.value
        force_unlock_upload5.status = 0
        db.add(force_unlock_upload5)

        # request target API
        req_param = {"sort_order": 0}
        resp = client.get(self.base_url.format(token_address), params=req_param)

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "limit": None, "offset": None, "total": 4},
            "uploads": [
                {
                    "issuer_address": issuer_address,
                    "status": 1,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 1,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
                    "batch_id": mock.ANY,
                    "created": mock.ANY,
                },
                {
                    "issuer_address": issuer_address,
                    "status": 0,
                    "token_address": "token_address_test",
                    "token_type": "IbetStraightBond",
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
    def test_error_1(self, client, db):
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
        req_param = {"status": "invalid_value"}
        resp = client.get(self.base_url.format(token_address), params=req_param)

        assert resp.status_code == 422
        assert resp.json() == {
            "detail": [
                {
                    "loc": ["query", "status"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer",
                }
            ],
            "meta": {"code": 1, "title": "RequestValidationError"},
        }
