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

import pytest
from pytz import timezone

import config
from app.model.db import (
    IDXPersonalInfo,
    IDXTransfer,
    IDXTransferSourceEventType,
    PersonalInfoDataSource,
    Token,
    TokenType,
    TokenVersion,
)

local_tz = timezone(config.TZ)


class TestListShareTokenTransferHistory:
    # target API endpoint
    base_url = "/share/transfers/{}"

    test_transaction_hash = "test_transaction_hash"
    test_issuer_address = "test_issuer_address"
    test_token_address = "test_token_address"

    test_from_address_1 = "test_from_address_1"
    test_from_address_2 = "test_from_address_2"
    test_to_address_1 = "test_to_address_1"
    test_to_address_2 = "test_to_address_2"

    test_block_timestamp = [
        datetime.strptime("2022/01/02 15:20:30", "%Y/%m/%d %H:%M:%S"),  # JST 2022/01/03
        datetime.strptime("2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"),  # JST 2022/01/02
        datetime.strptime("2022/01/02 00:20:30", "%Y/%m/%d %H:%M:%S"),  # JST 2022/01/02
    ]
    test_block_timestamp_str = [
        "2022-01-03T00:20:30+09:00",
        "2022-01-02T00:20:30+09:00",
        "2022-01-02T09:20:30+09:00",
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # default sort
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.from_address = self.test_from_address_1
            _idx_transfer.to_address = self.test_to_address_1
            _idx_transfer.amount = i
            _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
            _idx_transfer.data = None
            _idx_transfer.block_timestamp = self.test_block_timestamp[i]
            async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_2>
    # offset, limit
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address_1
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "テスト太郎1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address_1
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "テスト太郎2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_to)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.from_address = self.test_from_address_1
            _idx_transfer.to_address = self.test_to_address_1
            _idx_transfer.amount = i
            _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
            _idx_transfer.data = None
            _idx_transfer.block_timestamp = self.test_block_timestamp[i]
            async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address) + "?offset=1&limit=1"
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "テスト太郎1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "テスト太郎2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_1>
    # filter: block_timestamp_from
    @pytest.mark.asyncio
    async def test_normal_3_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"block_timestamp_from": "2022-01-02T09:20:30"},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_2>
    # filter: block_timestamp_to
    @pytest.mark.asyncio
    async def test_normal_3_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"block_timestamp_to": "2022-01-02T09:20:30"},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_3>
    # filter: from_address
    @pytest.mark.asyncio
    async def test_normal_3_3(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"from_address": self.test_from_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_4>
    # filter: to_address
    @pytest.mark.asyncio
    async def test_normal_3_4(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_2
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_2
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"to_address": self.test_to_address_1},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_5>
    # filter: from_address_name
    @pytest.mark.asyncio
    async def test_normal_3_5(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address_1
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "テスト太郎1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_from_address_2
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "テスト太郎2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_to)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"from_address_name": "テスト太郎1"},  # test_from_address_1's name
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "テスト太郎1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_6>
    # filter: to_address_name
    @pytest.mark.asyncio
    async def test_normal_3_6(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_2
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_to_address_1
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "テスト太郎1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address_2
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "テスト太郎2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_to)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"to_address_name": "テスト太郎1"},  # test_from_address_1's name
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "テスト太郎1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_7_1>
    # filter: amount (EQUAL)
    @pytest.mark.asyncio
    async def test_normal_3_7_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 10
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 20
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 30
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"amount": 20},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 20,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_7_2>
    # filter: amount (GTE)
    @pytest.mark.asyncio
    async def test_normal_3_7_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 10
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 20
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 30
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"amount": 20, "amount_operator": 1},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 30,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 20,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_7_3>
    # filter: amount (LTE)
    @pytest.mark.asyncio
    async def test_normal_3_7_3(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 10
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 20
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 30
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"amount": 20, "amount_operator": 2},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 10,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 20,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_8>
    # filter: source_event
    @pytest.mark.asyncio
    async def test_normal_3_8(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"source_event": IDXTransferSourceEventType.UNLOCK},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_9>
    # filter: data
    @pytest.mark.asyncio
    async def test_normal_3_9(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"data": "unlo"}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3_10>
    # filter: message
    @pytest.mark.asyncio
    async def test_normal_3_10(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK
        _idx_transfer.data = {"message": "force_unlock"}
        _idx_transfer.message = "force_unlock"
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"message": "force_unlock"},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                    "data": {"message": "force_unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_1>
    # sort: block_timestamp ASC
    @pytest.mark.asyncio
    async def test_normal_4_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.from_address = self.test_from_address_1
            _idx_transfer.to_address = self.test_to_address_1
            _idx_transfer.amount = i
            _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
            _idx_transfer.data = None
            _idx_transfer.block_timestamp = self.test_block_timestamp[i]
            async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": "block_timestamp",
                "sort_order": 0,
            },
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_2>
    # sort: from_address ASC
    @pytest.mark.asyncio
    async def test_normal_4_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": "from_address",
                "sort_order": 0,
            },
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_2,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_2,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_3>
    # sort: to_address DESC
    @pytest.mark.asyncio
    async def test_normal_4_3(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_2
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": "to_address",
                "sort_order": 1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_2,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_4>
    # sort: from_address_name DESC
    @pytest.mark.asyncio
    async def test_normal_4_4(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_2
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address_1
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "テスト太郎1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_from_address_2
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "テスト太郎2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_to)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": "from_address_name",
                "sort_order": 1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_2,
                    "from_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "テスト太郎2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "テスト太郎1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_5>
    # sort: to_address_name DESC
    @pytest.mark.asyncio
    async def test_normal_4_5(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_2
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_to_address_1
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "テスト太郎1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address_2
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "テスト太郎2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info_to)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": "to_address_name",
                "sort_order": 1,
            },
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_2,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "テスト太郎2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "テスト太郎1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_6>
    # sort: amount DESC
    @pytest.mark.asyncio
    async def test_normal_4_6(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        async_db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address_1
        _idx_transfer.to_address = self.test_to_address_1
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        async_db.add(_idx_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "sort_item": "amount",
                "sort_order": 0,
            },
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address_1,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address_1,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # token not found
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 404
        assumed_response = {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }
        assert resp.json() == assumed_response

    # <Error_2>
    # processing token
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # <Error_3>
    # param error: sort_item
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "block_timestamp12345"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "enum",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'block_timestamp', 'from_address', 'to_address', 'from_address_name', 'to_address_name' or 'amount'",
                    "input": "block_timestamp12345",
                    "ctx": {
                        "expected": "'block_timestamp', 'from_address', 'to_address', 'from_address_name', 'to_address_name' or 'amount'"
                    },
                }
            ],
        }

    # <Error_4>
    # param error: sort_order(min)
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"sort_order": -1}
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "0 or 1"},
                    "input": "-1",
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "type": "enum",
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Error_5>
    # param error: sort_order(max)
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"sort_order": 2}
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "0 or 1"},
                    "input": "2",
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "type": "enum",
                }
            ],
        }
        assert resp.json() == assumed_response
