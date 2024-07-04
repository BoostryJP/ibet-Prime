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

from app.model.db import Ledger, Token, TokenType, TokenVersion
from tests.account_config import config_eth_account


class TestAppRoutersLedgerTokenAddressHistoryGET:
    # target API endpoint
    base_url = "/ledger/{token_address}/history"

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

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_1.ledger = {}
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_ledger_1)

        _ledger_2 = Ledger()
        _ledger_2.token_address = token_address
        _ledger_2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_2.ledger = {}
        _ledger_2.ledger_created = datetime.strptime(
            "2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_ledger_2)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "ledgers": [
                {
                    "id": 2,
                    "token_address": token_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "created": "2022-01-02T09:20:30+09:00",
                },
                {
                    "id": 1,
                    "token_address": token_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "created": "2022-01-02T00:20:30+09:00",
                },
            ],
        }

    # <Normal_1_2>
    # unset issuer-address
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

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_1.ledger = {}
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_ledger_1)

        _ledger_2 = Ledger()
        _ledger_2.token_address = token_address
        _ledger_2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_2.ledger = {}
        _ledger_2.ledger_created = datetime.strptime(
            "2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_ledger_2)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(token_address=token_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "ledgers": [
                {
                    "id": 2,
                    "token_address": token_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "created": "2022-01-02T09:20:30+09:00",
                },
                {
                    "id": 1,
                    "token_address": token_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "created": "2022-01-02T00:20:30+09:00",
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

        _ledger_1 = Ledger()
        _ledger_1.token_address = token_address
        _ledger_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_1.ledger = {}
        _ledger_1.ledger_created = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_ledger_1)

        _ledger_2 = Ledger()
        _ledger_2.token_address = token_address
        _ledger_2.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_2.ledger = {}
        _ledger_2.ledger_created = datetime.strptime(
            "2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        db.add(_ledger_2)

        _ledger_3 = Ledger()
        _ledger_3.token_address = token_address
        _ledger_3.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_3.ledger = {}
        _ledger_3.ledger_created = datetime.strptime(
            "2022/01/02 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_ledger_3)

        _ledger_4 = Ledger()
        _ledger_4.token_address = token_address
        _ledger_4.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _ledger_4.ledger = {}
        _ledger_4.ledger_created = datetime.strptime(
            "2022/01/03 00:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/03
        db.add(_ledger_4)

        db.commit()

        # request target API
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
            "ledgers": [
                {
                    "id": 3,
                    "token_address": token_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "created": "2022-01-03T00:20:30+09:00",
                },
                {
                    "id": 2,
                    "token_address": token_address,
                    "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                    "created": "2022-01-02T09:20:30+09:00",
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
