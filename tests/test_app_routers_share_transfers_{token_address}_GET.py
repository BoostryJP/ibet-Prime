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
    IDXPersonalInfo,
    IDXTransfer,
    IDXTransferSourceEventType,
    Token,
    TokenType,
    TokenVersion,
)

local_tz = timezone(config.TZ)


class TestAppRoutersShareTransfersGET:
    # target API endpoint
    base_url = "/share/transfers/{}"

    test_transaction_hash = "test_transaction_hash"
    test_issuer_address = "test_issuer_address"
    test_token_address = "test_token_address"
    test_from_address = "test_from_address"
    test_to_address = "test_to_address"
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
    def test_normal_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.from_address = self.test_from_address
            _idx_transfer.to_address = self.test_to_address
            _idx_transfer.amount = i
            _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
            _idx_transfer.data = None
            _idx_transfer.block_timestamp = self.test_block_timestamp[i]
            db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_2_1>
    # offset, limit
    def test_normal_2_1(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_to)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.from_address = self.test_from_address
            _idx_transfer.to_address = self.test_to_address
            _idx_transfer.amount = i
            _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
            _idx_transfer.data = None
            _idx_transfer.block_timestamp = self.test_block_timestamp[i]
            db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(
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
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_2_2>
    # filter: source_event
    def test_normal_2_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_to)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_2"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_2"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_1"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK.value
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={"source_event": IDXTransferSourceEventType.UNLOCK.value},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_history": [
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": "test_from_address_1",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK.value,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_2_3>
    # filter: data
    def test_normal_2_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_to)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_2"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_2"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_1"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK.value
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(
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
                    "from_address": "test_from_address_1",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK.value,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3>
    # sort: block_timestamp ASC
    def test_normal_3(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_to)

        # prepare data: IDXTransfer
        for i in range(0, 3):
            _idx_transfer = IDXTransfer()
            _idx_transfer.transaction_hash = self.test_transaction_hash
            _idx_transfer.token_address = self.test_token_address
            _idx_transfer.from_address = self.test_from_address
            _idx_transfer.to_address = self.test_to_address
            _idx_transfer.amount = i
            _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
            _idx_transfer.data = None
            _idx_transfer.block_timestamp = self.test_block_timestamp[i]
            db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(
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
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4>
    # sort: from_address ASC
    def test_normal_4(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_to)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_2"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_2"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = "test_from_address_1"
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK.value
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(
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
                    "from_address": "test_from_address_1",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK.value,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": "test_from_address_2",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": "test_from_address_2",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5>
    # sort: to_address DESC
    def test_normal_5(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_to)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address
        _idx_transfer.to_address = "test_to_address_2"
        _idx_transfer.amount = 0
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address
        _idx_transfer.to_address = "test_to_address_1"
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address
        _idx_transfer.to_address = "test_to_address_1"
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK.value
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(
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
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": "test_to_address_2",
                    "to_address_personal_information": None,
                    "amount": 0,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": "test_to_address_1",
                    "to_address_personal_information": None,
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK.value,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": "test_to_address_1",
                    "to_address_personal_information": None,
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[1],
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_6>
    # sort: amount DESC
    def test_normal_6(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = self.test_issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = self.test_issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }  # latest data
        db.add(_personal_info_to)

        # prepare data: IDXTransfer
        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 1
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[0]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        _idx_transfer.data = None
        _idx_transfer.block_timestamp = self.test_block_timestamp[1]
        db.add(_idx_transfer)

        _idx_transfer = IDXTransfer()
        _idx_transfer.transaction_hash = self.test_transaction_hash
        _idx_transfer.token_address = self.test_token_address
        _idx_transfer.from_address = self.test_from_address
        _idx_transfer.to_address = self.test_to_address
        _idx_transfer.amount = 2
        _idx_transfer.source_event = IDXTransferSourceEventType.UNLOCK.value
        _idx_transfer.data = {"message": "unlock"}
        _idx_transfer.block_timestamp = self.test_block_timestamp[2]
        db.add(_idx_transfer)

        db.commit()

        # request target API
        resp = client.get(
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
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 1,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
                    "data": None,
                    "block_timestamp": self.test_block_timestamp_str[0],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.UNLOCK.value,
                    "data": {"message": "unlock"},
                    "block_timestamp": self.test_block_timestamp_str[2],
                },
                {
                    "transaction_hash": self.test_transaction_hash,
                    "token_address": self.test_token_address,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 2,
                    "source_event": IDXTransferSourceEventType.TRANSFER.value,
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
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 404
        assumed_response = {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }
        assert resp.json() == assumed_response

    # <Error_2>
    # processing token
    def test_error_2(self, client, db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_SHARE.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_24_06
        db.add(_token)

        db.commit()

        # request target API
        resp = client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # <Error_3>
    # param error: sort_item
    def test_error_3(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "block_timestamp12345"},
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {
                        "expected": "'block_timestamp', 'from_address', "
                        "'to_address' or 'amount'"
                    },
                    "input": "block_timestamp12345",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'block_timestamp', 'from_address', "
                    "'to_address' or 'amount'",
                    "type": "enum",
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Error_4>
    # param error: sort_order(min)
    def test_error_4(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address), params={"sort_order": -1}
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "0 or 1"},
                    "input": -1,
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "type": "enum",
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Error_5>
    # param error: sort_order(max)
    def test_error_5(self, client, db):
        # request target API
        resp = client.get(
            self.base_url.format(self.test_token_address), params={"sort_order": 2}
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "0 or 1"},
                    "input": 2,
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "type": "enum",
                }
            ],
        }
        assert resp.json() == assumed_response
