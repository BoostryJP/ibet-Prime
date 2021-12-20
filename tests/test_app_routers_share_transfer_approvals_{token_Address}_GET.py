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


class TestAppRoutersShareTransferApprovalsTokenAddressGET:

    # target API endpoint
    base_url = "/share/transfer_approvals/{}"

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

    # <Normal_1_1>
    def test_normal_1_1(self, client, db):
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            if i == 2:
                _idx_transfer_approval.cancelled = True
                _idx_transfer_approval.transfer_approved = True
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
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": None,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": True,
                    "transfer_approved": True,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
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
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": None,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_1_2>
    # unapproved data
    def test_normal_1_2(self, client, db):
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = None
            _idx_transfer_approval.approval_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
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
                    "id": 3,
                    "token_address": self.test_token_address,
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
                    "transfer_approved": False,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
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
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": None,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": False,
                    "transfer_approved": False,
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
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
                    "id": 2,
                    "token_address": self.test_token_address,
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
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_3>
    # set exchange_address
    def test_normal_3(self, client, db):
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
            if i == 1:
                _idx_transfer_approval.exchange_address = self.test_exchange_address + "0"
            else:
                _idx_transfer_approval.exchange_address = self.test_exchange_address + "1"
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
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
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address + "0",
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
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address + "1",
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
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address + "1",
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "transfer_approved": False,
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_1>
    # filter
    # from_address
    def test_normal_4_1(self, client, db):
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address + str(i)
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "from_address": self.test_from_address + "1"
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
                    "token_address": self.test_token_address,
                    "exchange_address": None,
                    "application_id": 1,
                    "from_address": self.test_from_address + "1",
                    "to_address": self.test_to_address,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "is_issuer_cancelable": True,
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_2>
    # filter
    # to_address
    def test_normal_4_2(self, client, db):
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address + str(i)
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "to_address": self.test_to_address + "1"
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
                    "token_address": self.test_token_address,
                    "exchange_address": None,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address + "1",
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "is_issuer_cancelable": True,
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_1>
    # filter
    # status
    # 0: unapproved
    def test_normal_4_3_1(self, client, db):
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            if i == 0:
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
                _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
                _idx_transfer_approval.cancelled = False
            elif i == 1:
                _idx_transfer_approval.cancelled = False
            else:
                _idx_transfer_approval.cancelled = True
            db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "status": 0
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
                    "token_address": self.test_token_address,
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
                    "is_issuer_cancelable": True,
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_2>
    # filter
    # status
    # 1: approved
    def test_normal_4_3_2(self, client, db):
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            if i == 0:
                _idx_transfer_approval.cancelled = False
            elif i == 1:
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
                _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
                _idx_transfer_approval.cancelled = False
            else:
                _idx_transfer_approval.cancelled = True
            db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "status": 1
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
                    "token_address": self.test_token_address,
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
                    "is_issuer_cancelable": True,
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_3>
    # filter
    # status
    # 2: canceled
    def test_normal_4_3_3(self, client, db):
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
            _idx_transfer_approval.exchange_address = None
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            if i == 0:
                _idx_transfer_approval.cancelled = False
            elif i == 1:
                _idx_transfer_approval.cancelled = True
            else:
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
                _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
                _idx_transfer_approval.cancelled = False
            db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "status": 2
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
                    "token_address": self.test_token_address,
                    "exchange_address": None,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancelled": True,
                    "is_issuer_cancelable": True,
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_4_1>
    # filter
    # is_issuer_cancelable
    # true
    def test_normal_4_4_1(self, client, db):
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
            if i != 1:
                _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "is_issuer_cancelable": True
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
                    "token_address": self.test_token_address,
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
                    "is_issuer_cancelable": True,
                }
            ]
        }
        assert resp.json() == assumed_response

    # <Normal_4_4_2>
    # filter
    # is_issuer_cancelable
    # false
    def test_normal_4_4_2(self, client, db):
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
            if i == 1:
                _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
            _idx_transfer_approval.cancelled = False
            db.add(_idx_transfer_approval)

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={
                "is_issuer_cancelable": False
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
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "to_address": self.test_to_address,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancelled": False,
                    "is_issuer_cancelable": False,
                }
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
            self.base_url.format(self.test_token_address),
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
            self.base_url.format(self.test_token_address),
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
            self.base_url.format(self.test_token_address),
            params={
                "status": 3,
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
                    "ctx": {"limit_value": 2},
                    "msg": "ensure this value is less than or equal to 2",
                    "type": "value_error.number.not_le",
                },
            ]
        }
        assert resp.json() == assumed_response

    # <Error_2>
    # token not found
    def test_error_2(self, client, db):
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

    # <Error_3>
    # processing token
    def test_error_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
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
            "detail": "wait for a while as the token is being processed"
        }
