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

from pytz import timezone

import config
from app.model.db import (
    Token,
    TokenType,
    IDXIssueRedeem,
    IDXIssueRedeemEventType, IDXIssueRedeemSortItem
)

local_tz = timezone(config.TZ)


class TestAppRoutersBondTokensTokenAddressRedeemGET:

    # target API endpoint
    base_url = "/bond/tokens/{}/redeem"

    test_token_address = "test_token_address"
    test_other_token_address = "test_other_token_address"

    test_event_type = "Issue"
    test_transaction_hash = "test_transaction_hash"
    test_issuer_address = "test_issuer_address"
    test_locked_address = "test_from_address"
    test_target_address = "test_to_address"

    test_amount = [10, 20, 30]

    test_block_timestamp = [
        datetime.strptime("2022/01/02 15:20:30", '%Y/%m/%d %H:%M:%S'),  # JST 2022/01/03
        datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S'),  # JST 2022/01/02
        datetime.strptime("2022/01/02 00:20:30", '%Y/%m/%d %H:%M:%S'),  # JST 2022/01/02
    ]
    test_block_timestamp_str = [
        "2022-01-03T00:20:30+09:00",
        "2022-01-02T00:20:30+09:00",
        "2022-01-02T09:20:30+09:00",
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # 0 record
    def test_normal_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXIssueRedeem
        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_other_token_address  # other token
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[0]
        _record.block_timestamp = self.test_block_timestamp[0]
        db.add(_record)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            'result_set': {
                'count': 0,
                'offset': None,
                'limit': None,
                'total': 0
            },
            'history': []
        }

    # Normal_2
    # multiple records
    def test_normal_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXIssueRedeem
        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[0]
        _record.block_timestamp = self.test_block_timestamp[0]
        db.add(_record)

        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[1]
        _record.block_timestamp = self.test_block_timestamp[1]
        db.add(_record)

        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[2]
        _record.block_timestamp = self.test_block_timestamp[2]
        db.add(_record)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            'result_set': {
                'count': 3,
                'offset': None,
                'limit': None,
                'total': 3
            },
            'history': [
                {
                    'transaction_hash': self.test_transaction_hash,
                    'token_address': self.test_token_address,
                    'locked_address': self.test_locked_address,
                    'target_address': self.test_target_address,
                    'amount': self.test_amount[0],
                    'block_timestamp': self.test_block_timestamp_str[0]
                },
                {
                    'transaction_hash': self.test_transaction_hash,
                    'token_address': self.test_token_address,
                    'locked_address': self.test_locked_address,
                    'target_address': self.test_target_address,
                    'amount': self.test_amount[2],
                    'block_timestamp': self.test_block_timestamp_str[2]
                },
                {
                    'transaction_hash': self.test_transaction_hash,
                    'token_address': self.test_token_address,
                    'locked_address': self.test_locked_address,
                    'target_address': self.test_target_address,
                    'amount': self.test_amount[1],
                    'block_timestamp': self.test_block_timestamp_str[1]
                }
            ]
        }

    # Normal_3
    # sort
    def test_normal_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXIssueRedeem
        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[0]
        _record.block_timestamp = self.test_block_timestamp[0]
        db.add(_record)

        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[1]
        _record.block_timestamp = self.test_block_timestamp[1]
        db.add(_record)

        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[2]
        _record.block_timestamp = self.test_block_timestamp[2]
        db.add(_record)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": IDXIssueRedeemSortItem.BLOCK_TIMESTAMP,
                "sort_order": 0
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            'result_set': {
                'count': 3,
                'offset': None,
                'limit': None,
                'total': 3
            },
            'history': [
                {
                    'transaction_hash': self.test_transaction_hash,
                    'token_address': self.test_token_address,
                    'locked_address': self.test_locked_address,
                    'target_address': self.test_target_address,
                    'amount': self.test_amount[1],
                    'block_timestamp': self.test_block_timestamp_str[1]
                },
                {
                    'transaction_hash': self.test_transaction_hash,
                    'token_address': self.test_token_address,
                    'locked_address': self.test_locked_address,
                    'target_address': self.test_target_address,
                    'amount': self.test_amount[2],
                    'block_timestamp': self.test_block_timestamp_str[2]
                },
                {
                    'transaction_hash': self.test_transaction_hash,
                    'token_address': self.test_token_address,
                    'locked_address': self.test_locked_address,
                    'target_address': self.test_target_address,
                    'amount': self.test_amount[0],
                    'block_timestamp': self.test_block_timestamp_str[0]
                }
            ]
        }

    # Normal_4
    # pagination
    def test_normal_4(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXIssueRedeem
        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[0]
        _record.block_timestamp = self.test_block_timestamp[0]
        db.add(_record)

        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[1]
        _record.block_timestamp = self.test_block_timestamp[1]
        db.add(_record)

        _record = IDXIssueRedeem()
        _record.event_type = IDXIssueRedeemEventType.REDEEM
        _record.transaction_hash = self.test_transaction_hash
        _record.token_address = self.test_token_address
        _record.locked_address = self.test_locked_address
        _record.target_address = self.test_target_address
        _record.amount = self.test_amount[2]
        _record.block_timestamp = self.test_block_timestamp[2]
        db.add(_record)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "offset": 1,
                "limit": 1
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            'result_set': {
                'count': 3,
                'offset': 1,
                'limit': 1,
                'total': 3
            },
            'history': [
                {
                    'transaction_hash': self.test_transaction_hash,
                    'token_address': self.test_token_address,
                    'locked_address': self.test_locked_address,
                    'target_address': self.test_target_address,
                    'amount': self.test_amount[2],
                    'block_timestamp': self.test_block_timestamp_str[2]
                }
            ]
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # NotFound
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address)
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
        }

    # Error_2
    # InvalidParameterError
    # this token is temporarily unavailable
    def test_error_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.token_status = 0
        db.add(_token)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address)
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "this token is temporarily unavailable"
        }

    # Error_3
    # RequestValidationError
    # sort_item
    def test_error_3(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": "block_timestamp12345"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            'meta': {
                'code': 1,
                'title': 'RequestValidationError'
            },
            'detail': [
                {
                    'loc': ['query', 'sort_item'],
                    'msg': "value is not a valid enumeration member; permitted: 'block_timestamp', 'locked_address', 'target_address', 'amount'",
                    'type': 'type_error.enum',
                    'ctx': {
                        'enum_values': [
                            'block_timestamp',
                            'locked_address',
                            'target_address',
                            'amount'
                        ]
                    }
                }
            ]
        }

    # Error_4_1
    # RequestValidationError
    # sort_order(min)
    def test_error_4_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_order": -1
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
                    "ctx": {"limit_value": 0},
                    "loc": ["query", "sort_order"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge"
                }
            ]
        }

    # Error_4_2
    # RequestValidationError
    # sort_order(max)
    def test_error_4_2(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_order": 2
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
                    "ctx": {"limit_value": 1},
                    "loc": ["query", "sort_order"],
                    "msg": "ensure this value is less than or equal to 1",
                    "type": "value_error.number.not_le"
                }
            ]
        }
