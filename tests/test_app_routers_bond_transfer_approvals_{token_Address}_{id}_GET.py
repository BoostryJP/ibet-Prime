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
    IDXTransferApproval,
    TransferApprovalHistory,
    TransferApprovalOperationType
)

local_tz = timezone(config.TZ)


class TestAppRoutersBondTransferApprovalsTokenAddressIdGET:
    # target API endpoint
    base_url = "/bond/transfer_approvals/{}/{}"

    test_transaction_hash = "test_transaction_hash"

    test_issuer_address = "test_issuer_address"
    test_token_address = "test_token_address"
    test_exchange_address = "test_exchange_address"
    test_from_address = "test_from_address"
    test_to_address = "test_to_address"
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
    # unapproved data
    def test_normal_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "token_address": self.test_token_address,
            "exchange_address": config.ZERO_ADDRESS,
            "application_id": 100,
            "from_address": self.test_from_address,
            "to_address": self.test_to_address,
            "amount": 200,
            "application_datetime": self.test_application_datetime_str,
            "application_blocktimestamp": self.test_application_blocktimestamp_str,
            "approval_datetime": None,
            "approval_blocktimestamp": None,
            "cancelled": False,
            "escrow_finished": False,
            "transfer_approved": False,
            "status": 0,
            "issuer_cancelable": True,
        }

    # <Normal_2_1>
    # canceled data
    # operation completed, event synchronizing
    def test_normal_2_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        _cancel_op = TransferApprovalHistory()
        _cancel_op.token_address = self.test_token_address
        _cancel_op.exchange_address = self.test_exchange_address
        _cancel_op.application_id = 100
        _cancel_op.operation_type = TransferApprovalOperationType.CANCEL.value
        db.add(_cancel_op)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "token_address": self.test_token_address,
            "exchange_address": self.test_exchange_address,
            "application_id": 100,
            "from_address": self.test_from_address,
            "to_address": self.test_to_address,
            "amount": 200,
            "application_datetime": self.test_application_datetime_str,
            "application_blocktimestamp": self.test_application_blocktimestamp_str,
            "approval_datetime": None,
            "approval_blocktimestamp": None,
            "cancelled": True,
            "escrow_finished": False,
            "transfer_approved": False,
            "status": 3,
            "issuer_cancelable": False,
        }

    # <Normal_2_2>
    # canceled data
    def test_normal_2_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "token_address": self.test_token_address,
            "exchange_address": self.test_exchange_address,
            "application_id": 100,
            "from_address": self.test_from_address,
            "to_address": self.test_to_address,
            "amount": 200,
            "application_datetime": self.test_application_datetime_str,
            "application_blocktimestamp": self.test_application_blocktimestamp_str,
            "approval_datetime": None,
            "approval_blocktimestamp": None,
            "cancelled": True,
            "escrow_finished": False,
            "transfer_approved": False,
            "status": 3,
            "issuer_cancelable": False,
        }

    # <Normal_3>
    # escrow finished data
    def test_normal_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp =  None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True
        _idx_transfer_approval.transfer_approved = False
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "token_address": self.test_token_address,
            "exchange_address": self.test_exchange_address,
            "application_id": 100,
            "from_address": self.test_from_address,
            "to_address": self.test_to_address,
            "amount": 200,
            "application_datetime": self.test_application_datetime_str,
            "application_blocktimestamp": self.test_application_blocktimestamp_str,
            "approval_datetime": None,
            "approval_blocktimestamp": None,
            "cancelled": False,
            "escrow_finished": True,
            "transfer_approved": False,
            "status": 1,
            "issuer_cancelable": False,
        }

    # <Normal_4_1>
    # transferred data
    # operation completed, event synchronizing
    def test_normal_4_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        _approval_op = TransferApprovalHistory()
        _approval_op.token_address = self.test_token_address
        _approval_op.exchange_address = self.test_exchange_address
        _approval_op.application_id = 100
        _approval_op.operation_type = TransferApprovalOperationType.APPROVE.value
        db.add(_approval_op)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "token_address": self.test_token_address,
            "exchange_address": self.test_exchange_address,
            "application_id": 100,
            "from_address": self.test_from_address,
            "to_address": self.test_to_address,
            "amount": 200,
            "application_datetime": self.test_application_datetime_str,
            "application_blocktimestamp": self.test_application_blocktimestamp_str,
            "approval_datetime": self.test_approval_datetime_str,
            "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
            "cancelled": False,
            "escrow_finished": True,
            "transfer_approved": True,
            "status": 2,
            "issuer_cancelable": False,
        }

    # <Normal_4_2>
    # transferred data
    def test_normal_4_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "id": 10,
            "token_address": self.test_token_address,
            "exchange_address": self.test_exchange_address,
            "application_id": 100,
            "from_address": self.test_from_address,
            "to_address": self.test_to_address,
            "amount": 200,
            "application_datetime": self.test_application_datetime_str,
            "application_blocktimestamp": self.test_application_blocktimestamp_str,
            "approval_datetime": self.test_approval_datetime_str,
            "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
            "cancelled": False,
            "escrow_finished": True,
            "transfer_approved": True,
            "status": 2,
            "issuer_cancelable": False,
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # token not found
    def test_error_1(self, client, db):
        id = 10

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
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

    # <Error_2>
    # processing token
    def test_error_2(self, client, db):
        id = 10

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
            self.base_url.format(self.test_token_address, id)
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

    # <Error_3>
    # transfer approval not found
    def test_error_3(self, client, db):
        id = 10

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.token_status = 1
        db.add(_token)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address, id)
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "transfer approval not found"
        }
