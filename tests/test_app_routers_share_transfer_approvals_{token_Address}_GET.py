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
    IDXTransferApproval
)

local_tz = timezone(config.TZ)


class TestAppRoutersShareTransferApprovalsGET:

    # target API endpoint
    base_url = "/share/transfer_approvals/{}"

    test_transaction_hash = "test_transaction_hash"

    test_issuer_address = "test_issuer_address"
    test_token_address = "test_token_address"
    test_transfer_from = "test_transfer_from"
    test_transfer_to = "test_transfer_to"
    test_application_datetime = datetime(year=2019, month=9, day=1)
    test_application_datetime_str = timezone("UTC").localize(test_application_datetime).astimezone(local_tz).isoformat()
    test_application_blocktimestamp = datetime(year=2019, month=9, day=2)
    test_application_blocktimestamp_str = timezone("UTC").localize(test_application_blocktimestamp).astimezone(local_tz).isoformat()
    test_approval_datetime = datetime(year=2019, month=9, day=3)
    test_approval_datetime_str = timezone("UTC").localize(test_approval_datetime).astimezone(local_tz).isoformat()
    test_approval_blocktimestamp = datetime(year=2019, month=9, day=4)
    test_approval_blocktimestamp_str = timezone("UTC").localize(test_approval_blocktimestamp).astimezone(local_tz).isoformat()

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_transfer_from
            _idx_transfer_approval.to_address = self.test_transfer_to
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            db.add(_idx_transfer_approval)

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
            "transfer_approval_history": [
                {
                    "token_address": self.test_token_address,
                    "application_id": 2,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False
                },
                {
                    "token_address": self.test_token_address,
                    "application_id": 1,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False
                },
                {
                    "token_address": self.test_token_address,
                    "application_id": 0,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_2>
    # offset, limit
    def test_normal_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_transfer_from
            _idx_transfer_approval.to_address = self.test_transfer_to
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            db.add(_idx_transfer_approval)

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
            "transfer_approval_history": [
                {
                    "token_address": self.test_token_address,
                    "application_id": 1,
                    "from_address": self.test_transfer_from,
                    "to_address": self.test_transfer_to,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False
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
