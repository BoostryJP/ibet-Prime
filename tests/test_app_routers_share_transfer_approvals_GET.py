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
    IDXTransferApproval,
    Token,
    TokenType,
    TransferApprovalHistory,
    TransferApprovalOperationType,
)

local_tz = timezone(config.TZ)


class TestAppRoutersShareTransferApprovalsGET:
    # target API endpoint
    base_url = "/share/transfer_approvals"

    test_transaction_hash = "test_transaction_hash"

    test_issuer_address_1 = "test_issuer_address_1"
    test_issuer_address_2 = "test_issuer_address_2"
    test_token_address_1 = "test_token_address_1"
    test_token_address_2 = "test_token_address_2"
    test_token_address_3 = "test_token_address_3"
    test_token_address_4 = "test_token_address_4"
    test_exchange_address = "test_exchange_address_1"
    test_from_address = "test_from_address"
    test_to_address = "test_to_address"
    test_application_datetime = datetime(year=2019, month=9, day=1)
    test_application_datetime_str = (
        timezone("UTC")
        .localize(test_application_datetime)
        .astimezone(local_tz)
        .isoformat()
    )
    test_application_blocktimestamp = datetime(year=2019, month=9, day=2)
    test_application_blocktimestamp_str = (
        timezone("UTC")
        .localize(test_application_blocktimestamp)
        .astimezone(local_tz)
        .isoformat()
    )
    test_approval_datetime = datetime(year=2019, month=9, day=3)
    test_approval_datetime_str = (
        timezone("UTC")
        .localize(test_approval_datetime)
        .astimezone(local_tz)
        .isoformat()
    )
    test_approval_blocktimestamp = datetime(year=2019, month=9, day=4)
    test_approval_blocktimestamp_str = (
        timezone("UTC")
        .localize(test_approval_blocktimestamp)
        .astimezone(local_tz)
        .isoformat()
    )

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # no data
    def test_normal_1(self, client, db):
        # prepare data: Token(failed)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        _token.token_status = 2
        db.add(_token)

        # prepare data: Token(bond)
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(failed token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = (
            self.test_approval_blocktimestamp
        )
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(share token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = (
            self.test_approval_blocktimestamp
        )
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(no token)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_3
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = (
            self.test_approval_blocktimestamp
        )
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
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "transfer_approvals": [],
        }
        assert resp.json() == assumed_response

    # <Normal_2>
    # single data
    def test_normal_2(self, client, db):
        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(ApplyFor(unapproved))
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None  # unapproved
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(EscrowFinish(escrow_finished))
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 11
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 11
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True  # escrow_finished
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(Approve(operation completed, event synchronizing))
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 21
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 21
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = (
            self.test_approval_blocktimestamp
        )
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True  # escrow_finished
        _idx_transfer_approval.transfer_approved = None  # event not synchronized
        db.add(_idx_transfer_approval)

        _transfer_approval_history = TransferApprovalHistory()
        _transfer_approval_history.token_address = self.test_token_address_1
        _transfer_approval_history.exchange_address = config.ZERO_ADDRESS
        _transfer_approval_history.application_id = 21
        _transfer_approval_history.operation_type = (
            TransferApprovalOperationType.APPROVE.value
        )
        db.add(_transfer_approval_history)

        # prepare data: IDXTransferApproval(Approve(transferred))
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 31
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 31
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = (
            self.test_approval_blocktimestamp
        )
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True  # escrow_finished
        _idx_transfer_approval.transfer_approved = True  # transferred
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(Cancel(operation completed, event synchronizing))
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 41
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 41
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None  # event not synchronized
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        _transfer_approval_history = TransferApprovalHistory()
        _transfer_approval_history.token_address = self.test_token_address_1
        _transfer_approval_history.exchange_address = config.ZERO_ADDRESS
        _transfer_approval_history.application_id = 41
        _transfer_approval_history.operation_type = (
            TransferApprovalOperationType.CANCEL.value
        )
        db.add(_transfer_approval_history)

        # prepare data: IDXTransferApproval(Cancel(canceled))
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 51
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 51
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True  # cancelled
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "transfer_approvals": [
                {
                    "issuer_address": self.test_issuer_address_1,
                    "token_address": self.test_token_address_1,
                    "application_count": 6,
                    "unapproved_count": 1,
                    "escrow_finished_count": 1,
                    "transferred_count": 2,
                    "canceled_count": 2,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_1>
    # multi data
    # issuer address is specified
    def test_normal_3_1(self, client, db):
        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-2)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_2
        _token.token_address = self.test_token_address_3
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(issuer-1 token-1)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None  # unapproved
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 11
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 11
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True  # escrow_finished
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 12
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 12
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.escrow_finished = True  # escrow_finished
        _idx_transfer_approval.transfer_approved = True  # transferred
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 31
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 31
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True  # cancelled
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-1 token-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None  # unapproved
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_3
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None  # unapproved
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url, headers={"issuer-address": self.test_issuer_address_1}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "transfer_approvals": [
                {
                    "issuer_address": self.test_issuer_address_1,
                    "token_address": self.test_token_address_1,
                    "application_count": 4,
                    "unapproved_count": 1,
                    "escrow_finished_count": 1,
                    "transferred_count": 1,
                    "canceled_count": 1,
                },
                {
                    "issuer_address": self.test_issuer_address_1,
                    "token_address": self.test_token_address_2,
                    "application_count": 1,
                    "unapproved_count": 1,
                    "escrow_finished_count": 0,
                    "transferred_count": 0,
                    "canceled_count": 0,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_2>
    # multi data
    # issuer address is not specified
    def test_normal_3_2(self, client, db):
        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-2)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_2
        _token.token_address = self.test_token_address_3
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(issuer-1 token-1)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None  # unapproved
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 11
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 11
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True  # escrow_finished
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 12
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 12
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.escrow_finished = True  # escrow_finished
        _idx_transfer_approval.transfer_approved = True  # transferred
        db.add(_idx_transfer_approval)

        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 31
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 31
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True  # cancelled
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-1 token-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None  # unapproved
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_3
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None  # unapproved
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_approvals": [
                {
                    "issuer_address": self.test_issuer_address_1,
                    "token_address": self.test_token_address_1,
                    "application_count": 4,
                    "unapproved_count": 1,
                    "escrow_finished_count": 1,
                    "transferred_count": 1,
                    "canceled_count": 1,
                },
                {
                    "issuer_address": self.test_issuer_address_1,
                    "token_address": self.test_token_address_2,
                    "application_count": 1,
                    "unapproved_count": 1,
                    "escrow_finished_count": 0,
                    "transferred_count": 0,
                    "canceled_count": 0,
                },
                {
                    "issuer_address": self.test_issuer_address_2,
                    "token_address": self.test_token_address_3,
                    "application_count": 1,
                    "unapproved_count": 1,
                    "escrow_finished_count": 0,
                    "transferred_count": 0,
                    "canceled_count": 0,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4>
    # offset - limit
    def test_normal_4(self, client, db):
        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_1
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_2
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_3
        _token.abi = {}
        db.add(_token)

        # prepare data: Token(issuer-1)
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address_1
        _token.token_address = self.test_token_address_4
        _token.abi = {}
        db.add(_token)

        # prepare data: IDXTransferApproval(issuer-1 token-1)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_1
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-1 token-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_2
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-1 token-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_3
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # prepare data: IDXTransferApproval(issuer-1 token-2)
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.token_address = self.test_token_address_4
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 1
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 1
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url,
            params={
                "limit": 2,
                "offset": 1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": 1, "limit": 2, "total": 4},
            "transfer_approvals": [
                {
                    "issuer_address": self.test_issuer_address_1,
                    "token_address": self.test_token_address_2,
                    "application_count": 1,
                    "unapproved_count": 1,
                    "escrow_finished_count": 0,
                    "transferred_count": 0,
                    "canceled_count": 0,
                },
                {
                    "issuer_address": self.test_issuer_address_1,
                    "token_address": self.test_token_address_3,
                    "application_count": 1,
                    "unapproved_count": 1,
                    "escrow_finished_count": 0,
                    "transferred_count": 0,
                    "canceled_count": 0,
                },
            ],
        }
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation error
    # type_error
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
            params={
                "offset": "c",
                "limit": "d",
            },
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
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
            ],
        }
        assert resp.json() == assumed_response
