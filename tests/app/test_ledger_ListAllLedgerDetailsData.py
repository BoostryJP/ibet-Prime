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

from datetime import datetime

from app.model.db import LedgerDetailsData, Token, TokenType, TokenVersion
from tests.account_config import config_eth_account


class TestListAllLedgerDetailsData:
    # target API endpoint
    base_url = "/ledger/{token_address}/details_data"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # set issuer-address
    def test_normal_1_1(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _details_data_1_1 = LedgerDetailsData()
        _details_data_1_1.token_address = token_address
        _details_data_1_1.data_id = "data_id_1"
        _details_data_1_1.data_created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_1_1)

        _details_data_2_1 = LedgerDetailsData()
        _details_data_2_1.token_address = token_address
        _details_data_2_1.data_id = "data_id_2"
        _details_data_2_1.data_created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_2_1)

        _details_data_2_2 = LedgerDetailsData()
        _details_data_2_2.token_address = token_address
        _details_data_2_2.data_id = "data_id_2"
        _details_data_2_2.data_created = datetime.strptime(
            "2022/01/02 00:20:30.000002", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_2_2)

        _details_data_3_1 = LedgerDetailsData()
        _details_data_3_1.token_address = token_address
        _details_data_3_1.data_id = "data_id_3"
        _details_data_3_1.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000010", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_1)

        _details_data_3_2 = LedgerDetailsData()
        _details_data_3_2.token_address = token_address
        _details_data_3_2.data_id = "data_id_3"
        _details_data_3_2.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000009", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_2)

        _details_data_3_3 = LedgerDetailsData()
        _details_data_3_3.token_address = token_address
        _details_data_3_3.data_id = "data_id_3"
        _details_data_3_3.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000008", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_3)

        _details_data_4_1 = LedgerDetailsData()
        _details_data_4_1.token_address = token_address
        _details_data_4_1.data_id = "data_id_4"
        _details_data_4_1.data_created = datetime.strptime(
            "2022/01/03 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_4_1)

        # Not Target
        _details_data_5_1 = LedgerDetailsData()
        _details_data_5_1.token_address = "test"
        _details_data_5_1.data_id = "dummy"
        db.add(_details_data_5_1)

        db.commit()

        resp = client.get(
            self.base_url.format(token_address=token_address),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "details_data": [
                {
                    "data_id": "data_id_1",
                    "count": 1,
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
                {
                    "data_id": "data_id_2",
                    "count": 2,
                    "created": "2022-01-02T09:20:30.000002+09:00",
                },
                {
                    "data_id": "data_id_3",
                    "count": 3,
                    "created": "2022-01-03T00:20:30.000010+09:00",
                },
                {
                    "data_id": "data_id_4",
                    "count": 1,
                    "created": "2022-01-03T09:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_1_2>
    # set issuer-address
    def test_normal_1_2(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _details_data_1_1 = LedgerDetailsData()
        _details_data_1_1.token_address = token_address
        _details_data_1_1.data_id = "data_id_1"
        _details_data_1_1.data_created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_1_1)

        _details_data_2_1 = LedgerDetailsData()
        _details_data_2_1.token_address = token_address
        _details_data_2_1.data_id = "data_id_2"
        _details_data_2_1.data_created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_2_1)

        _details_data_2_2 = LedgerDetailsData()
        _details_data_2_2.token_address = token_address
        _details_data_2_2.data_id = "data_id_2"
        _details_data_2_2.data_created = datetime.strptime(
            "2022/01/02 00:20:30.000002", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_2_2)

        _details_data_3_1 = LedgerDetailsData()
        _details_data_3_1.token_address = token_address
        _details_data_3_1.data_id = "data_id_3"
        _details_data_3_1.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000010", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_1)

        _details_data_3_2 = LedgerDetailsData()
        _details_data_3_2.token_address = token_address
        _details_data_3_2.data_id = "data_id_3"
        _details_data_3_2.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000009", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_2)

        _details_data_3_3 = LedgerDetailsData()
        _details_data_3_3.token_address = token_address
        _details_data_3_3.data_id = "data_id_3"
        _details_data_3_3.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000008", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_3)

        _details_data_4_1 = LedgerDetailsData()
        _details_data_4_1.token_address = token_address
        _details_data_4_1.data_id = "data_id_4"
        _details_data_4_1.data_created = datetime.strptime(
            "2022/01/03 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_4_1)

        # Not Target
        _details_data_5_1 = LedgerDetailsData()
        _details_data_5_1.token_address = "test"
        _details_data_5_1.data_id = "dummy"
        db.add(_details_data_5_1)

        db.commit()

        resp = client.get(
            self.base_url.format(token_address=token_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "details_data": [
                {
                    "data_id": "data_id_1",
                    "count": 1,
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
                {
                    "data_id": "data_id_2",
                    "count": 2,
                    "created": "2022-01-02T09:20:30.000002+09:00",
                },
                {
                    "data_id": "data_id_3",
                    "count": 3,
                    "created": "2022-01-03T00:20:30.000010+09:00",
                },
                {
                    "data_id": "data_id_4",
                    "count": 1,
                    "created": "2022-01-03T09:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_2>
    # limit-offset
    def test_normal_2(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _details_data_1_1 = LedgerDetailsData()
        _details_data_1_1.token_address = token_address
        _details_data_1_1.data_id = "data_id_1"
        _details_data_1_1.data_created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_1_1)

        _details_data_2_1 = LedgerDetailsData()
        _details_data_2_1.token_address = token_address
        _details_data_2_1.data_id = "data_id_2"
        _details_data_2_1.data_created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_2_1)

        _details_data_2_2 = LedgerDetailsData()
        _details_data_2_2.token_address = token_address
        _details_data_2_2.data_id = "data_id_2"
        _details_data_2_2.data_created = datetime.strptime(
            "2022/01/02 00:20:30.000002", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_details_data_2_2)

        _details_data_3_1 = LedgerDetailsData()
        _details_data_3_1.token_address = token_address
        _details_data_3_1.data_id = "data_id_3"
        _details_data_3_1.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000010", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_1)

        _details_data_3_2 = LedgerDetailsData()
        _details_data_3_2.token_address = token_address
        _details_data_3_2.data_id = "data_id_3"
        _details_data_3_2.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000009", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_2)

        _details_data_3_3 = LedgerDetailsData()
        _details_data_3_3.token_address = token_address
        _details_data_3_3.data_id = "data_id_3"
        _details_data_3_3.data_created = datetime.strptime(
            "2022/01/02 15:20:30.000008", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_3_3)

        _details_data_4_1 = LedgerDetailsData()
        _details_data_4_1.token_address = token_address
        _details_data_4_1.data_id = "data_id_4"
        _details_data_4_1.data_created = datetime.strptime(
            "2022/01/03 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_details_data_4_1)

        # Not Target
        _details_data_5_1 = LedgerDetailsData()
        _details_data_5_1.token_address = "test"
        _details_data_5_1.data_id = "dummy"
        db.add(_details_data_5_1)

        db.commit()

        resp = client.get(
            self.base_url.format(token_address=token_address),
            params={"offset": 1, "limit": 2},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": 1, "limit": 2, "total": 4},
            "details_data": [
                {
                    "data_id": "data_id_2",
                    "count": 2,
                    "created": "2022-01-02T09:20:30.000002+09:00",
                },
                {
                    "data_id": "data_id_3",
                    "count": 3,
                    "created": "2022-01-03T00:20:30.000010+09:00",
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error(issuer-address)
    def test_error_1(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
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

    # <Error_2_1>
    # Token Not Found
    # set issuer-address
    def test_error_2_1(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = (
            "0x1234567890123456789012345678901234567899"  # not target
        )
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 2
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
            params={
                "offset": 2,
                "limit": 3,
            },
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

    # <Error_2_2>
    # Token Not Found
    # unset issuer-address
    def test_error_2_2(self, client, db):
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
            params={
                "offset": 2,
                "limit": 3,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token does not exist",
        }

    # <Error_3>
    # Processing Token
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
            params={
                "offset": 2,
                "limit": 3,
            },
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
