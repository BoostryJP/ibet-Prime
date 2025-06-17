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
from unittest.mock import ANY

import pytest

from app.model.db import IDXLock, IDXUnlock, Token, TokenType, TokenVersion
from app.model.ibet import IbetShareContract, IbetStraightBondContract


class TestListAccountLockUnlockEvents:
    # target API endpoint
    base_url = "/positions/{account_address}/lock/events"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        # prepare data: Token
        _token = Token()
        _token.token_address = "0x1234567890123456789012345678900000000010"
        _token.issuer_address = "0x1234567890123456789012345678900000000100"
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
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

    # Normal_2_1
    # Bond
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_2_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        _lock.is_forced = True
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        _unlock.is_forced = True
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Unlock",
                    "is_forced": True,
                    "transaction_hash": "tx_hash_2",
                    "msg_sender": lock_address_1,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": other_account_address,
                    "value": 1,
                    "data": {"message": "unlocked_1"},
                    "block_timestamp": ANY,
                },
                {
                    "category": "Lock",
                    "is_forced": True,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_1"},
                    "block_timestamp": ANY,
                },
            ],
        }

    # Normal_2_2
    # Share
    @mock.patch("app.model.ibet.token.IbetShareContract.get")
    @pytest.mark.asyncio
    async def test_normal_2_2(self, mock_IbetShareContract_get, async_client, async_db):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_share_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        share_1 = IbetShareContract()
        share_1.name = token_name_1
        mock_IbetShareContract_get.side_effect = [share_1, share_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Unlock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_2",
                    "msg_sender": lock_address_1,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": other_account_address,
                    "value": 1,
                    "data": {"message": "unlocked_1"},
                    "block_timestamp": ANY,
                },
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_SHARE,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_1"},
                    "block_timestamp": ANY,
                },
            ],
        }

    # Normal_3_1
    # Records not subject to extraction
    # account_address
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_3_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = other_account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = other_account_address  # others
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = other_account_address  # others
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "events": [],
        }

    # Normal_3_2
    # Records not subject to extraction
    # token_status
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_3_2(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.token_status = 2
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "events": [],
        }

    # Normal_4
    # issuer_address is not None
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_4(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"
        other_issuer_address = "0x1234567890123456789012345678900000000200"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = other_issuer_address  # others
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_3"
        _lock.msg_sender = account_address
        _lock.block_number = 3
        _lock.token_address = token_address_2  # others
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_2  # others
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Unlock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_2",
                    "msg_sender": lock_address_1,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": other_account_address,
                    "value": 1,
                    "data": {"message": "unlocked_1"},
                    "block_timestamp": ANY,
                },
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_1"},
                    "block_timestamp": ANY,
                },
            ],
        }

    # Normal_5_1
    # Search filter: category
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_5_1(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"category": "Unlock"},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Unlock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_2",
                    "msg_sender": lock_address_1,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": other_account_address,
                    "value": 1,
                    "data": {"message": "unlocked_1"},
                    "block_timestamp": ANY,
                }
            ],
        }

    # Normal_5_2
    # Search filter: token_address
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_5_2(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_2
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"token_address": token_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_1"},
                    "block_timestamp": ANY,
                }
            ],
        }

    # Normal_5_3
    # Search filter: token_type
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_5_3(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address = "0x1234567890123456789012345678911111111111"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND  # bond
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _token = Token()
        _token.token_address = token_address_2
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_SHARE  # share
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_2
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"token_type": TokenType.IBET_STRAIGHT_BOND},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_1"},
                    "block_timestamp": ANY,
                }
            ],
        }

    # Normal_5_4
    # Search filter: msg_sender
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_5_4(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND  # bond
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXUnlock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = lock_address_1
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1  # lock address 1
        _lock.account_address = account_address
        _lock.recipient_address = lock_address_1
        _lock.value = 1
        _lock.data = {"message": "unlocked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_2"
        _lock.msg_sender = lock_address_2
        _lock.block_number = 2
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_2  # lock address 2
        _lock.account_address = account_address
        _lock.recipient_address = lock_address_2
        _lock.value = 1
        _lock.data = {"message": "unlocked_2"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"msg_sender": lock_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Unlock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": lock_address_1,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": lock_address_1,
                    "value": 1,
                    "data": {"message": "unlocked_1"},
                    "block_timestamp": ANY,
                }
            ],
        }

    # Normal_5_5
    # Search filter: lock_address
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_5_5(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND  # bond
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1  # lock address 1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_2"
        _lock.msg_sender = account_address
        _lock.block_number = 2
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_2  # lock address 2
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_2"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"lock_address": lock_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_1"},
                    "block_timestamp": ANY,
                }
            ],
        }

    # Normal_5_6
    # Search filter: recipient_address
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_5_6(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"
        other_account_address_1 = "0x1234567890123456789012345678911111111111"
        other_account_address_2 = "0x1234567890123456789012345678922222222222"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND  # bond
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_1"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 1
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address_1
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_1"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        _unlock = IDXUnlock()
        _unlock.transaction_hash = "tx_hash_2"
        _unlock.msg_sender = lock_address_1
        _unlock.block_number = 2
        _unlock.token_address = token_address_1
        _unlock.lock_address = lock_address_1
        _unlock.account_address = account_address
        _unlock.recipient_address = other_account_address_2
        _unlock.value = 1
        _unlock.data = {"message": "unlocked_2"}
        _unlock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_unlock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"recipient_address": other_account_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "events": [
                {
                    "category": "Unlock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": lock_address_1,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": other_account_address_1,
                    "value": 1,
                    "data": {"message": "unlocked_1"},
                    "block_timestamp": ANY,
                }
            ],
        }

    # Normal_6
    # Sort
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_6(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"
        lock_address_2 = "0x1234567890123456789012345678900000000002"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_2"
        _lock.msg_sender = account_address
        _lock.block_number = 2
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_2
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_2"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_3"
        _lock.msg_sender = account_address
        _lock.block_number = 3
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_3"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_4"
        _lock.msg_sender = account_address
        _lock.block_number = 4
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_2
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_4"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1, bond_1, bond_1, bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"sort_item": "lock_address", "sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "events": [
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_3",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_3"},
                    "block_timestamp": ANY,
                },
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_1",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_1"},
                    "block_timestamp": ANY,
                },
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_4",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_2,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_4"},
                    "block_timestamp": ANY,
                },
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_2",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_2,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_2"},
                    "block_timestamp": ANY,
                },
            ],
        }

    # Normal_7
    # Pagination
    @mock.patch("app.model.ibet.token.IbetStraightBondContract.get")
    @pytest.mark.asyncio
    async def test_normal_7(
        self, mock_IbetStraightBondContract_get, async_client, async_db
    ):
        issuer_address = "0x1234567890123456789012345678900000000100"

        account_address = "0x1234567890123456789012345678900000000000"

        lock_address_1 = "0x1234567890123456789012345678900000000001"

        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_name_1 = "test_bond_1"

        # prepare data: Token
        _token = Token()
        _token.token_address = token_address_1
        _token.issuer_address = issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: Lock events
        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_1"
        _lock.msg_sender = account_address
        _lock.block_number = 1
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_1"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_2"
        _lock.msg_sender = account_address
        _lock.block_number = 2
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_2"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        _lock = IDXLock()
        _lock.transaction_hash = "tx_hash_3"
        _lock.msg_sender = account_address
        _lock.block_number = 3
        _lock.token_address = token_address_1
        _lock.lock_address = lock_address_1
        _lock.account_address = account_address
        _lock.value = 1
        _lock.data = {"message": "locked_3"}
        _lock.block_timestamp = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_lock)

        await async_db.commit()

        # mock
        bond_1 = IbetStraightBondContract()
        bond_1.name = token_name_1
        mock_IbetStraightBondContract_get.side_effect = [bond_1]

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={"offset": 1, "limit": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "events": [
                {
                    "category": "Lock",
                    "is_forced": False,
                    "transaction_hash": "tx_hash_2",
                    "msg_sender": account_address,
                    "issuer_address": issuer_address,
                    "token_address": token_address_1,
                    "token_type": TokenType.IBET_STRAIGHT_BOND,
                    "token_name": token_name_1,
                    "lock_address": lock_address_1,
                    "account_address": account_address,
                    "recipient_address": None,
                    "value": 1,
                    "data": {"message": "locked_2"},
                    "block_timestamp": ANY,
                }
            ],
        }

    # ###########################################################################
    # # Error Case
    # ###########################################################################

    # Error_1_1
    # RequestValidationError
    # header
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
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
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        account_address = "0x1234567890123456789012345678900000000000"

        # request target api
        resp = await async_client.get(
            self.base_url.format(account_address=account_address),
            params={
                "token_type": "test",
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
                    "ctx": {"expected": "'IbetStraightBond' or 'IbetShare'"},
                    "input": "test",
                    "loc": ["query", "token_type"],
                    "msg": "Input should be 'IbetStraightBond' or 'IbetShare'",
                    "type": "enum",
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
                        "expected": "'token_address', 'lock_address', "
                        "'recipient_address', 'value' or "
                        "'block_timestamp'"
                    },
                    "input": "test",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'token_address', 'lock_address', "
                    "'recipient_address', 'value' or 'block_timestamp'",
                    "type": "enum",
                },
            ],
        }
