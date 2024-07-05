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

from datetime import UTC, datetime
from unittest import mock
from unittest.mock import ANY, AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.model.blockchain import IbetShareContract
from app.model.db import IDXLock, IDXUnlock, Token, TokenType, TokenVersion


class TestAppRoutersShareLockEvents:
    # target API endpoint
    base_url = "/share/tokens/{token_address}/lock_events"

    issuer_address = "0x1234567890123456789012345678900000000100"

    account_address_1 = "0x1234567890123456789012345678900000000000"
    account_address_2 = "0x1234567890123456789012345678900000000001"

    other_account_address_1 = "0x1234567890123456789012345678911111111111"
    other_account_address_2 = "0x1234567890123456789012345678922222222222"

    lock_address_1 = "0x1234567890123456789012345678900000000100"
    lock_address_2 = "0x1234567890123456789012345678900000000200"

    token_address_1 = "0x1234567890123456789012345678900000000010"
    token_name_1 = "test_share_1"
    token_address_2 = "0x1234567890123456789012345678900000000020"

    def setup_data(self, db: Session, token_status: int = 1):
        # prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address
        _token.type = TokenType.IBET_SHARE.value  # bond
        _token.tx_hash = ""
        _token.abi = ""
        _token.token_status = token_status
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_2
        _token.issuer_address = self.issuer_address
        _token.type = TokenType.IBET_SHARE.value  # bond
        _token.tx_hash = ""
        _token.abi = ""
        _token.token_status = token_status
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = self.account_address_1
        _lock.block_number = 1
        _lock.token_address = self.token_address_1
        _lock.lock_address = self.lock_address_1
        _lock.account_address = self.account_address_1
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_2"
        _lock.msg_sender = self.account_address_2
        _lock.block_number = 2
        _lock.token_address = self.token_address_1
        _lock.lock_address = self.lock_address_2
        _lock.account_address = self.account_address_2
        _lock.value = 1
        _lock.data = {"message": "locked_2"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_3"
        _unlock.msg_sender = self.lock_address_1
        _unlock.block_number = 3
        _unlock.token_address = self.token_address_1
        _unlock.lock_address = self.lock_address_1
        _unlock.account_address = self.account_address_1
        _unlock.recipient_address = self.other_account_address_1
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_unlock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_4"
        _unlock.msg_sender = self.lock_address_2
        _unlock.block_number = 4
        _unlock.token_address = self.token_address_1
        _unlock.lock_address = self.lock_address_2
        _unlock.account_address = self.account_address_2
        _unlock.recipient_address = self.other_account_address_2
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_2"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        db.add(_unlock)

        db.commit()

    @staticmethod
    def get_contract_mock_data(token_name_list: list[str]):
        token_contract_list = []
        for toke_name in token_name_list:
            token = IbetShareContract()
            token.name = toke_name
            token_contract_list.append(token)
        return token_contract_list

    expected_lock_1 = {
        "category": "Lock",
        "transaction_hash": "tx_hash_1",
        "msg_sender": account_address_1,
        "issuer_address": issuer_address,
        "token_address": token_address_1,
        "token_type": TokenType.IBET_SHARE.value,
        "token_name": token_name_1,
        "lock_address": lock_address_1,
        "account_address": account_address_1,
        "recipient_address": None,
        "value": 1,
        "data": {"message": "locked_1"},
        "block_timestamp": ANY,
    }
    expected_lock_2 = {
        "category": "Lock",
        "transaction_hash": "tx_hash_2",
        "msg_sender": account_address_2,
        "issuer_address": issuer_address,
        "token_address": token_address_1,
        "token_type": TokenType.IBET_SHARE.value,
        "token_name": token_name_1,
        "lock_address": lock_address_2,
        "account_address": account_address_2,
        "recipient_address": None,
        "value": 1,
        "data": {"message": "locked_2"},
        "block_timestamp": ANY,
    }
    expected_unlock_1 = {
        "category": "Unlock",
        "transaction_hash": "tx_hash_3",
        "msg_sender": lock_address_1,
        "issuer_address": issuer_address,
        "token_address": token_address_1,
        "token_type": TokenType.IBET_SHARE.value,
        "token_name": token_name_1,
        "lock_address": lock_address_1,
        "account_address": account_address_1,
        "recipient_address": other_account_address_1,
        "value": 1,
        "data": {"message": "unlocked_1"},
        "block_timestamp": ANY,
    }
    expected_unlock_2 = {
        "category": "Unlock",
        "transaction_hash": "tx_hash_4",
        "msg_sender": lock_address_2,
        "issuer_address": issuer_address,
        "token_address": token_address_1,
        "token_type": TokenType.IBET_SHARE.value,
        "token_name": token_name_1,
        "lock_address": lock_address_2,
        "account_address": account_address_2,
        "recipient_address": other_account_address_2,
        "value": 1,
        "data": {"message": "unlocked_2"},
        "block_timestamp": ANY,
    }

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # 0 record
    def test_normal_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.token_address = self.token_address_1
        _token.issuer_address = self.issuer_address
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = ""
        _token.abi = ""
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0,
            },
            "events": [],
        }

    # Normal_2
    # Multiple record
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_2(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db)

        # mock
        mock_IbetShareContract_get.side_effect = self.get_contract_mock_data(
            [self.token_name_1, self.token_name_1, self.token_name_1, self.token_name_1]
        )

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "events": [
                self.expected_unlock_2,
                self.expected_unlock_1,
                self.expected_lock_2,
                self.expected_lock_1,
            ],
        }

    # Normal_3
    # Records not subject to extraction
    # token_status
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_3(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db, token_status=2)

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "events": [],
        }

    # Normal_4
    # issuer_address is not None
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_4(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db)

        # mock
        mock_IbetShareContract_get.side_effect = self.get_contract_mock_data(
            [self.token_name_1, self.token_name_1, self.token_name_1, self.token_name_1]
        )

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
            headers={"issuer-address": self.issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "events": [
                self.expected_unlock_2,
                self.expected_unlock_1,
                self.expected_lock_2,
                self.expected_lock_1,
            ],
        }

    # Normal_5_1
    # Search filter: category
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_5_1(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db)

        # mock
        mock_IbetShareContract_get.side_effect = self.get_contract_mock_data(
            [self.token_name_1, self.token_name_1]
        )

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
            params={"category": "Lock"},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 4},
            "events": [self.expected_lock_2, self.expected_lock_1],
        }

    # Normal_5_2
    # Search filter: account_address
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_5_2(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db)

        # mock
        mock_IbetShareContract_get.side_effect = self.get_contract_mock_data(
            [self.token_name_1, self.token_name_1]
        )

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
            params={"account_address": self.account_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 4},
            "events": [self.expected_unlock_1, self.expected_lock_1],
        }

    # Normal_5_3
    # Search filter: lock_address
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_5_3(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db)

        # mock
        mock_IbetShareContract_get.side_effect = self.get_contract_mock_data(
            [self.token_name_1, self.token_name_1]
        )

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
            params={"lock_address": self.lock_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 4},
            "events": [self.expected_unlock_1, self.expected_lock_1],
        }

    # Normal_5_4
    # Search filter: recipient_address
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_5_4(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db)

        # mock
        mock_IbetShareContract_get.side_effect = self.get_contract_mock_data(
            [self.token_name_1]
        )

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
            params={"recipient_address": self.other_account_address_2},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 4},
            "events": [self.expected_unlock_2],
        }

    # Normal_6
    # Sort
    @pytest.mark.parametrize(
        "sort_item, sort_order, data, expect",
        [
            # (
            #     "{sort_item}", {sort_order},
            #     {data used to contract mock},
            #     {expected result}
            # ),
            (
                "account_address",
                0,
                get_contract_mock_data(
                    [token_name_1, token_name_1, token_name_1, token_name_1]
                ),
                [
                    expected_unlock_1,
                    expected_lock_1,
                    expected_unlock_2,
                    expected_lock_2,
                ],
            ),
            (
                "lock_address",
                0,
                get_contract_mock_data(
                    [token_name_1, token_name_1, token_name_1, token_name_1]
                ),
                [
                    expected_unlock_1,
                    expected_lock_1,
                    expected_unlock_2,
                    expected_lock_2,
                ],
            ),
            (
                "recipient_address",
                0,
                get_contract_mock_data(
                    [token_name_1, token_name_1, token_name_1, token_name_1]
                ),
                [
                    expected_unlock_1,
                    expected_unlock_2,
                    expected_lock_2,
                    expected_lock_1,
                ],
            ),
            (
                "recipient_address",
                1,
                get_contract_mock_data(
                    [token_name_1, token_name_1, token_name_1, token_name_1]
                ),
                [
                    expected_lock_2,
                    expected_lock_1,
                    expected_unlock_2,
                    expected_unlock_1,
                ],
            ),
            (
                "value",
                0,
                get_contract_mock_data(
                    [token_name_1, token_name_1, token_name_1, token_name_1]
                ),
                [
                    expected_unlock_2,
                    expected_unlock_1,
                    expected_lock_2,
                    expected_lock_1,
                ],
            ),
        ],
    )
    def test_normal_6(self, sort_item, sort_order, data, expect, client, db):
        # prepare data
        self.setup_data(db=db)

        # request target api
        with mock.patch(
            "app.model.blockchain.token.IbetShareContract.get",
            AsyncMock(side_effect=data),
        ):
            resp = client.get(
                self.base_url.format(token_address=self.token_address_1),
                params={"sort_item": sort_item, "sort_order": sort_order},
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "events": expect,
        }

    # Normal_7
    # Pagination
    @mock.patch("app.model.blockchain.token.IbetShareContract.get")
    def test_normal_7(self, mock_IbetShareContract_get, client, db):
        # prepare data
        self.setup_data(db=db)

        # mock
        mock_IbetShareContract_get.side_effect = self.get_contract_mock_data(
            [self.token_name_1]
        )

        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
            params={"offset": 1, "limit": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": 1, "limit": 1, "total": 4},
            "events": [self.expected_unlock_1],
        }

    # ###########################################################################
    # # Error Case
    # ###########################################################################

    # Error_1_1
    # RequestValidationError
    # header
    def test_error_1_1(self, client, db):
        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
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

    # Error_1_2
    # RequestValidationError
    # query(invalid value)
    def test_error_1_2(self, client, db):
        # request target api
        resp = client.get(
            self.base_url.format(token_address=self.token_address_1),
            params={
                "category": "test",
                "sort_item": "test",
                "offset": "test",
                "limit": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "test",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                },
                {
                    "ctx": {"expected": "'Lock' or 'Unlock'"},
                    "input": "test",
                    "loc": ["query", "category"],
                    "msg": "Input should be 'Lock' or 'Unlock'",
                    "type": "enum",
                },
                {
                    "ctx": {
                        "expected": "'account_address', 'lock_address', "
                        "'recipient_address', 'value' or "
                        "'block_timestamp'"
                    },
                    "input": "test",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'account_address', 'lock_address', "
                    "'recipient_address', 'value' or 'block_timestamp'",
                    "type": "enum",
                },
            ],
        }
