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


class TestAppRoutersBondTransferApprovalsGET:
    # target API endpoint
    base_url = "/bond/transfer_approvals"

    test_transaction_hash = "test_transaction_hash"

    test_issuer_address_1 = "test_issuer_address_1"
    test_issuer_address_2 = "test_issuer_address_2"
    test_token_address_1 = "test_token_address_1"
    test_token_address_2 = "test_token_address_2"
    test_token_address_3 = "test_token_address_3"
    test_exchange_address = "test_exchange_address_1"
    test_from_address = "test_from_address"
    test_to_address = "test_to_address"
    test_application_datetime = datetime(year=2019, month=9, day=1)
    test_application_datetime_str = timezone("UTC").localize(test_application_datetime).astimezone(local_tz).isoformat()
    test_application_blocktimestamp = datetime(year=2019, month=9, day=2)
    test_application_blocktimestamp_str = timezone("UTC").localize(test_application_blocktimestamp).astimezone(
        local_tz).isoformat()
    test_approval_datetime = datetime(year=2019, month=9, day=3)
    test_approval_datetime_str = timezone("UTC").localize(test_approval_datetime).astimezone(local_tz).isoformat()
    test_approval_blocktimestamp = datetime(year=2019, month=9, day=4)
    test_approval_blocktimestamp_str = timezone("UTC").localize(test_approval_blocktimestamp).astimezone(
        local_tz).isoformat()

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # no data
    def test_normal_1(self, client, db):
        # prepare data: Token(failed)
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        _token.token_status = 2
        db.add(_token)

        # prepare data: Token(share)
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(failed token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(share token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(no token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_3
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0
            },
            "transfer_approval_history": []
        }
        assert resp.json() == assumed_response

    # <Normal_2_1>
    # issuer address is specified
    def test_normal_2_1(self, client, db):
        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-2)
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_2
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(issuer-1 token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-2 token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 11
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 11
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            headers={
                "issuer-address": self.test_issuer_address_1,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1
            },
            "transfer_approval_history": [
                {
                    "id": 1,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_2_2>
    # issuer address is not specified
    # Multiple records
    def test_normal_2_2(self, client, db):
        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-2)
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_2
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-2)
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_2
        _token.token_address = self.test_token_address_3
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(issuer-1 token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-2 token-1)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 11
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 11
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 12
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 12
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 13
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 13
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 14
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 14
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-2 token-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_3
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 21
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 21
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 6,
                "offset": None,
                "limit": None,
                "total": 6
            },
            "transfer_approval_history": [
                {
                    "id": 1,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
                {
                    "id": 5,
                    "token_address": self.test_token_address_2,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 14,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 14,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": True,
                    "transfer_approved": True,
                    "is_issuer_cancelable": False
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address_2,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 13,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 13,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": True,
                    "transfer_approved": True,
                    "is_issuer_cancelable": False
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address_2,
                    "exchange_address": None,
                    "application_id": 12,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 12,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": True,
                    "transfer_approved": True,
                    "is_issuer_cancelable": True
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address_2,
                    "exchange_address": None,
                    "application_id": 11,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 11,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": True,
                    "transfer_approved": True,
                    "is_issuer_cancelable": True
                },
                {
                    "id": 6,
                    "token_address": self.test_token_address_3,
                    "exchange_address": None,
                    "application_id": 21,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 21,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": True,
                    "transfer_approved": True,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_3>
    # offset - limit
    def test_normal_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 4
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 4
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "limit": 2,
                "offset": 1,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 2,
                "offset": 1,
                "limit": 2,
                "total": 4
            },
            "transfer_approval_history": [
                {
                    "id": 3,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_1>
    # filter
    # token_address
    def test_normal_4_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_3
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(token-1)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(token-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(token-3)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_3
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "token_address": self.test_token_address_2,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address_2,
                    "exchange_address": None,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_2>
    # filter
    # from_address
    def test_normal_4_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address + "1"
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address + "2"
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address + "3"
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "from_address": self.test_from_address + "2",
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 2,
                    "from_address": self.test_from_address + "2",
                    "to_address": self.test_to_address,
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_3>
    # filter
    # to_address
    def test_normal_4_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "1"
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "2"
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "3"
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "to_address": self.test_to_address + "2",
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address + "2",
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_4_1>
    # filter
    # status
    # 0: unapproved
    def test_normal_4_4_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        # unapproved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # approved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # transferred
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # canceled
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 4
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 4
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # unapproved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 5
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 5
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # unapproved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 6
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 6
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # unapproved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 7
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 7
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "status": 0,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 7
            },
            "transfer_approval_history": [
                {
                    "id": 7,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 7,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 7,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
                {
                    "id": 6,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 6,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 6,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
                {
                    "id": 5,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 5,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 5,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_4_2>
    # filter
    # status
    # 1: approved
    def test_normal_4_4_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        # unapproved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # approved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # transferred
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # canceled
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 4
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 4
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "status": 1,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 4
            },
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": False,
                    "transfer_approved": True,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_4_3>
    # filter
    # status
    # 2: transferred
    def test_normal_4_4_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        # unapproved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # approved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # transferred
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # canceled
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 4
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 4
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "status": 2,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 4
            },
            "transfer_approval_history": [
                {
                    "id": 3,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": True,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_4_4>
    # filter
    # status
    # 3: canceled
    def test_normal_4_4_4(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        # unapproved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # approved
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # transferred
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # canceled
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 4
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 4
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "status": 3,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 4
            },
            "transfer_approval_history": [
                {
                    "id": 4,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 4,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 4,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": True,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_5_1>
    # filter
    # is_issuer_cancelable
    # true
    def test_normal_4_5_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "1"
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "2"
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "3"
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "is_issuer_cancelable": True,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address_1,
                    "exchange_address": None,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address + "2",
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": True
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_5_2>
    # filter
    # is_issuer_cancelable
    # false
    def test_normal_4_5_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "1"
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 2
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "2"
        _idx_transfer_approval.amount = 2
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 3
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address + "3"
        _idx_transfer_approval.amount = 3
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "is_issuer_cancelable": False,
            }
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 3
            },
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address_1,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address + "2",
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                    "is_issuer_cancelable": False
                },
            ]
        }
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # validation error
    # type_error
    def test_error_1_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
            params={
                "status": "a",
                "is_issuer_cancelable": "b",
                "offset": "c",
                "limit": "d",
            }
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["query", "status"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer",
                },
                {
                    "loc": ["query", "is_issuer_cancelable"],
                    "msg": "value could not be parsed to a boolean",
                    "type": "type_error.bool",
                },
                {
                    "loc": ["query", "offset"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer",
                },
                {
                    "loc": ["query", "limit"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer",
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Error_1_2>
    # validation error
    # min value
    def test_error_1_2(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
            params={
                "status": -1,
            }
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["query", "status"],
                    "ctx": {"limit_value": 0},
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge",
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Error_1_3>
    # validation error
    # max value
    def test_error_1_3(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
            params={
                "status": 4,
            }
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["query", "status"],
                    "ctx": {"limit_value": 3},
                    "msg": "ensure this value is less than or equal to 3",
                    "type": "value_error.number.not_le",
                },
            ]
        }
        assert resp.json() == assumed_response
