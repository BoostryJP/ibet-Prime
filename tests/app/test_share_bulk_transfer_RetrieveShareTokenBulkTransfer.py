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

import pytest

from app.model.db import (
    Account,
    BulkTransfer,
    BulkTransferUpload,
    IDXPersonalInfo,
    PersonalInfoDataSource,
    TokenType,
)
from tests.account_config import default_eth_account


class TestAppRoutersShareBulkTransferGET:
    # target API endpoint
    test_url = "/share/bulk_transfer/{}"

    upload_issuer_list = [
        {
            "address": default_eth_account("user1")["address"],
            "keyfile": default_eth_account("user1")["keyfile_json"],
        },
        {
            "address": default_eth_account("user2")["address"],
            "keyfile": default_eth_account("user2")["keyfile_json"],
        },
        {
            "address": default_eth_account("user3")["address"],
            "keyfile": default_eth_account("user3")["keyfile_json"],
        },
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",  # 0: under progress
        "de778f46-864e-4ec0-b566-21bd31cf63ff",  # 1: succeeded
        "cf33d48f-9e6e-4a36-a55e-5bbcbda69c80",  # 2: failed
    ]

    bulk_transfer_token = "0xbB4138520af85fAfdDAACc7F0AabfE188334D0ca"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Header: issuer-address is set
    # - Personal information is not set
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        # prepare data : Account(Issuer)
        for _issuer in self.upload_issuer_list:
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            async_db.add(account)

        for i in range(0, 3):
            # prepare data : BulkTransferUpload
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE
            bulk_transfer_upload.status = i
            async_db.add(bulk_transfer_upload)

            # prepare data : BulkTransfer
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer.upload_id = self.upload_id_list[i]
            bulk_transfer.token_type = TokenType.IBET_SHARE
            bulk_transfer.token_address = self.bulk_transfer_token
            bulk_transfer.from_address = self.upload_issuer_list[1]["address"]
            bulk_transfer.to_address = self.upload_issuer_list[2]["address"]
            bulk_transfer.amount = 10 + i
            bulk_transfer.status = i
            async_db.add(bulk_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.test_url.format(self.upload_id_list[1]),
            headers={"issuer-address": self.upload_issuer_list[1]["address"]},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "bulk_transfer_upload_records": [
                {
                    "issuer_address": self.upload_issuer_list[1]["address"],
                    "token_type": TokenType.IBET_SHARE,
                    "upload_id": self.upload_id_list[1],
                    "token_address": self.bulk_transfer_token,
                    "from_address": self.upload_issuer_list[1]["address"],
                    "from_address_personal_information": None,
                    "to_address": self.upload_issuer_list[2]["address"],
                    "to_address_personal_information": None,
                    "amount": 11,
                    "status": 1,
                    "transaction_error_code": None,
                    "transaction_error_message": None,
                }
            ],
        }

    # <Normal_1_2>
    # Header: issuer-address is set
    # - Personal information is set
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        # prepare data : Account(Issuer)
        for _issuer in self.upload_issuer_list:
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            async_db.add(account)

        for i in range(0, 3):
            # prepare data : BulkTransferUpload
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE
            bulk_transfer_upload.status = i
            async_db.add(bulk_transfer_upload)

            # prepare data : BulkTransfer
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer.upload_id = self.upload_id_list[i]
            bulk_transfer.token_type = TokenType.IBET_SHARE
            bulk_transfer.token_address = self.bulk_transfer_token
            bulk_transfer.from_address = self.upload_issuer_list[1]["address"]
            bulk_transfer.to_address = self.upload_issuer_list[2]["address"]
            bulk_transfer.amount = 10 + i
            bulk_transfer.status = i
            async_db.add(bulk_transfer)

            # prepare data: IDXPersonalInfo
            _personal_info_from = IDXPersonalInfo()
            _personal_info_from.issuer_address = self.upload_issuer_list[i]["address"]
            _personal_info_from.account_address = self.upload_issuer_list[1]["address"]
            _personal_info_from._personal_info = {
                "key_manager": "key_manager_test1",
                "name": "test_name1",
                "postal_code": "postal_code_test1",
                "address": "address_test1",
                "email": "email_test1",
                "birth": "birth_test1",
                "is_corporate": False,
                "tax_category": 10,
            }
            _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info_from)

            _personal_info_to = IDXPersonalInfo()
            _personal_info_to.issuer_address = self.upload_issuer_list[i]["address"]
            _personal_info_to.account_address = self.upload_issuer_list[2]["address"]
            _personal_info_to._personal_info = {
                "key_manager": "key_manager_test2",
                "name": "test_name2",
                "postal_code": "postal_code_test2",
                "address": "address_test2",
                "email": "email_test2",
                "birth": "birth_test2",
                "is_corporate": False,
                "tax_category": 10,
            }
            _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info_to)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.test_url.format(self.upload_id_list[1]),
            headers={"issuer-address": self.upload_issuer_list[1]["address"]},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "bulk_transfer_upload_records": [
                {
                    "issuer_address": self.upload_issuer_list[1]["address"],
                    "token_type": TokenType.IBET_SHARE,
                    "upload_id": self.upload_id_list[1],
                    "token_address": self.bulk_transfer_token,
                    "from_address": self.upload_issuer_list[1]["address"],
                    "from_address_personal_information": {
                        "key_manager": "key_manager_test1",
                        "name": "test_name1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "to_address": self.upload_issuer_list[2]["address"],
                    "to_address_personal_information": {
                        "key_manager": "key_manager_test2",
                        "name": "test_name2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": "birth_test2",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "amount": 11,
                    "status": 1,
                    "transaction_error_code": None,
                    "transaction_error_message": None,
                }
            ],
        }

    # <Normal_2>
    # Header: issuer-address is not set
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        for i in range(0, 3):
            # prepare data : BulkTransferUpload
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE
            bulk_transfer_upload.status = i
            async_db.add(bulk_transfer_upload)

            # prepare data : BulkTransfer
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer.upload_id = self.upload_id_list[i]
            bulk_transfer.token_type = TokenType.IBET_SHARE
            bulk_transfer.token_address = self.bulk_transfer_token
            bulk_transfer.from_address = self.upload_issuer_list[1]["address"]
            bulk_transfer.to_address = self.upload_issuer_list[2]["address"]
            bulk_transfer.amount = 10 + i
            bulk_transfer.status = i
            async_db.add(bulk_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.test_url.format(self.upload_id_list[0]),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "bulk_transfer_upload_records": [
                {
                    "issuer_address": self.upload_issuer_list[0]["address"],
                    "token_type": TokenType.IBET_SHARE,
                    "upload_id": self.upload_id_list[0],
                    "token_address": self.bulk_transfer_token,
                    "from_address": self.upload_issuer_list[1]["address"],
                    "from_address_personal_information": None,
                    "to_address": self.upload_issuer_list[2]["address"],
                    "to_address_personal_information": None,
                    "amount": 10,
                    "status": 0,
                    "transaction_error_code": None,
                    "transaction_error_message": None,
                }
            ],
        }

    # <Normal_3>
    # Bulk transaction error record
    @pytest.mark.asyncio
    async def test_normal_3(self, async_client, async_db):
        # prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = self.upload_issuer_list[0]["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_SHARE
        bulk_transfer_upload.status = 2
        async_db.add(bulk_transfer_upload)

        # prepare data : BulkTransfer
        bulk_transfer = BulkTransfer()
        bulk_transfer.issuer_address = self.upload_issuer_list[0]["address"]
        bulk_transfer.upload_id = self.upload_id_list[0]
        bulk_transfer.token_type = TokenType.IBET_SHARE
        bulk_transfer.token_address = self.bulk_transfer_token
        bulk_transfer.from_address = self.upload_issuer_list[1]["address"]
        bulk_transfer.to_address = self.upload_issuer_list[2]["address"]
        bulk_transfer.amount = 10
        bulk_transfer.status = 2
        bulk_transfer.transaction_error_code = 110503
        bulk_transfer.transaction_error_message = (
            "Transfer amount is greater than from address balance."
        )
        async_db.add(bulk_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.test_url.format(self.upload_id_list[0]),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "bulk_transfer_upload_records": [
                {
                    "issuer_address": self.upload_issuer_list[0]["address"],
                    "token_type": TokenType.IBET_SHARE,
                    "upload_id": self.upload_id_list[0],
                    "token_address": self.bulk_transfer_token,
                    "from_address": self.upload_issuer_list[1]["address"],
                    "from_address_personal_information": None,
                    "to_address": self.upload_issuer_list[2]["address"],
                    "to_address_personal_information": None,
                    "amount": 10,
                    "status": 2,
                    "transaction_error_code": 110503,
                    "transaction_error_message": "Transfer amount is greater than from address balance.",
                }
            ],
        }

    # <Normal_4>
    # offset / limit
    @pytest.mark.asyncio
    async def test_normal_4(self, async_client, async_db):
        # prepare data : Account(Issuer)
        for _issuer in self.upload_issuer_list:
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            async_db.add(account)

        # prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = self.upload_issuer_list[1]["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[1]
        bulk_transfer_upload.token_type = TokenType.IBET_SHARE
        bulk_transfer_upload.status = 1
        async_db.add(bulk_transfer_upload)

        for i in range(0, 3):
            # prepare data : BulkTransfer
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = self.upload_issuer_list[1]["address"]
            bulk_transfer.upload_id = self.upload_id_list[1]
            bulk_transfer.token_type = TokenType.IBET_SHARE
            bulk_transfer.token_address = self.bulk_transfer_token
            bulk_transfer.from_address = self.upload_issuer_list[1]["address"]
            bulk_transfer.to_address = self.upload_issuer_list[2]["address"]
            bulk_transfer.amount = 10 + i
            bulk_transfer.status = i
            async_db.add(bulk_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.test_url.format(self.upload_id_list[1]),
            headers={"issuer-address": self.upload_issuer_list[1]["address"]},
            params={"offset": 1, "limit": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "bulk_transfer_upload_records": [
                {
                    "issuer_address": self.upload_issuer_list[1]["address"],
                    "token_type": TokenType.IBET_SHARE,
                    "upload_id": self.upload_id_list[1],
                    "token_address": self.bulk_transfer_token,
                    "from_address": self.upload_issuer_list[1]["address"],
                    "from_address_personal_information": None,
                    "to_address": self.upload_issuer_list[2]["address"],
                    "to_address_personal_information": None,
                    "amount": 11,
                    "status": 1,
                    "transaction_error_code": None,
                    "transaction_error_message": None,
                }
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # invalid type : issuer-address
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # request target API
        resp = await async_client.get(
            self.test_url.format(self.upload_id_list[0]),
            headers={"issuer-address": "DUMMY ADDRESS"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "DUMMY ADDRESS",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2>
    # Upload id Not Found
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # request target API
        resp = await async_client.get(self.test_url.format("DUMMY UPLOAD ID"))

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "bulk transfer not found",
        }

    # <Error_3>
    # Upload id Not Found
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        # prepare data : Account(Issuer)
        for _issuer in self.upload_issuer_list:
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            async_db.add(account)

        for i in range(0, 3):
            # prepare data : BulkTransferUpload
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE
            bulk_transfer_upload.status = i
            async_db.add(bulk_transfer_upload)

            # prepare data : BulkTransfer
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer.upload_id = self.upload_id_list[i]
            bulk_transfer.token_type = TokenType.IBET_SHARE
            bulk_transfer.token_address = self.bulk_transfer_token
            bulk_transfer.from_address = self.upload_issuer_list[1]["address"]
            bulk_transfer.to_address = self.upload_issuer_list[2]["address"]
            bulk_transfer.amount = 10 + i
            bulk_transfer.status = i
            async_db.add(bulk_transfer)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.test_url.format(self.upload_id_list[2]),
            headers={"issuer-address": self.upload_issuer_list[0]["address"]},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "bulk transfer not found",
        }
