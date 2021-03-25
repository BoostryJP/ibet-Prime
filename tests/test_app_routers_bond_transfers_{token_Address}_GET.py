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
from app.model.db import Token, TokenType, IDXTransfer


class TestAppRoutersBondTransfersGET:

    # target API endpoint
    base_url = "/bond/transfers/{}"

    test_transaction_hash = "test_transaction_hash"
    test_issuer_address = "test_issuer_address"
    test_token_address = "test_token_address"
    test_transfer_from = "test_transfer_from"
    test_transfer_to = "test_transfer_to"
    test_block_timestamp = datetime(year=2019, month=9, day=2)
    test_block_timestamp_str = "2019/09/02 00:00:00"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.transfer_from = self.test_transfer_from
            _idx_transfer.transfer_to = self.test_transfer_to
            _idx_transfer.amount = i
            _idx_transfer.block_timestamp = self.test_block_timestamp
            db.add(_idx_transfer)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address)
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 2,
                    "block_timestamp": self.test_block_timestamp_str
                }, {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 1,
                    "block_timestamp": self.test_block_timestamp_str
                }, {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 0,
                    "block_timestamp": self.test_block_timestamp_str
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_2>
    # offset, limit
    def test_normal_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.transfer_from = self.test_transfer_from
            _idx_transfer.transfer_to = self.test_transfer_to
            _idx_transfer.amount = i
            _idx_transfer.block_timestamp = self.test_block_timestamp
            db.add(_idx_transfer)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address) + "?offset=1&limit=1"
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": 1,
                "limit": 1,
                "total": 3
            },
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 1,
                    "block_timestamp": self.test_block_timestamp_str
                }
            ]
        }
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # token not found
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address)
        )

        # assertion
        assert resp.status_code == 404
        assumed_response = {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
        }
        assert resp.json() == assumed_response
