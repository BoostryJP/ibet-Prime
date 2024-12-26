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

import pytest
import pytz

from app.model.db import Account, BulkTransfer, BulkTransferUpload, TokenType
from config import TZ
from tests.account_config import config_eth_account

local_tz = pytz.timezone(TZ)


class TestListShareTokenBulkTransfers:
    # target API endpoint
    test_url = "/share/bulk_transfer"

    upload_issuer_list = [
        {
            "address": config_eth_account("user1")["address"],
            "keyfile": config_eth_account("user1")["keyfile_json"],
        },
        {
            "address": config_eth_account("user2")["address"],
            "keyfile": config_eth_account("user2")["keyfile_json"],
        },
        {
            "address": config_eth_account("user3")["address"],
            "keyfile": config_eth_account("user3")["keyfile_json"],
        },
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",  # 0: under progress
        "de778f46-864e-4ec0-b566-21bd31cf63ff",  # 1: succeeded
        "cf33d48f-9e6e-4a36-a55e-5bbcbda69c80",  # 2: failed
    ]

    test_token_address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Search all
    # - Header: issuer address is set
    @pytest.mark.freeze_time("2021-05-20 12:34:56")
    def test_normal_1_1(self, client, db):
        # prepare data : Account(Issuer)
        for _issuer in self.upload_issuer_list:
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            db.add(account)

        # prepare data : BulkTransferUpload
        utc_now = datetime.now(UTC).replace(tzinfo=None)
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
            bulk_transfer_upload.token_address = self.test_token_address
            bulk_transfer_upload.status = i
            bulk_transfer_upload.created = utc_now
            db.add(bulk_transfer_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.test_url,
            headers={"issuer-address": self.upload_issuer_list[1]["address"]},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "bulk_transfer_uploads": [
                {
                    "issuer_address": self.upload_issuer_list[1]["address"],
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_address": self.test_token_address,
                    "upload_id": self.upload_id_list[1],
                    "status": 1,
                    "created": pytz.timezone("UTC")
                    .localize(utc_now)
                    .astimezone(local_tz)
                    .isoformat(),
                }
            ],
        }

    # <Normal_1_2>
    # Search all
    # - Header: issuer address is not set
    @pytest.mark.freeze_time("2021-05-20 12:34:56")
    def test_normal_1_2(self, client, db):
        # prepare data : BulkTransferUpload
        utc_now = datetime.now(UTC).replace(tzinfo=None)
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[i]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
            bulk_transfer_upload.token_address = self.test_token_address
            bulk_transfer_upload.status = i
            bulk_transfer_upload.created = utc_now
            db.add(bulk_transfer_upload)

        db.commit()

        # request target API
        resp = client.get(self.test_url)

        # assertion
        assert resp.status_code == 200
        assert resp.json()["result_set"] == {
            "count": 3,
            "offset": None,
            "limit": None,
            "total": 3,
        }

        assumed_response = []
        for i in range(0, 3):
            assumed_response.append(
                {
                    "issuer_address": self.upload_issuer_list[i]["address"],
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_address": self.test_token_address,
                    "upload_id": self.upload_id_list[i],
                    "status": i,
                    "created": pytz.timezone("UTC")
                    .localize(utc_now)
                    .astimezone(local_tz)
                    .isoformat(),
                }
            )
        sorted_assumed = sorted(assumed_response, key=lambda x: x["upload_id"])
        sorted_resp = sorted(
            resp.json()["bulk_transfer_uploads"], key=lambda x: x["upload_id"]
        )
        assert sorted_resp == sorted_assumed

    # <Normal_2>
    # Search by token_address
    @pytest.mark.freeze_time("2021-05-20 12:34:56")
    def test_normal_2(self, client, db):
        # prepare data : Account(Issuer)
        for _issuer in self.upload_issuer_list:
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            db.add(account)

        # prepare data : BulkTransferUpload
        utc_now = datetime.now(UTC).replace(tzinfo=None)
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[0]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
            bulk_transfer_upload.status = i
            bulk_transfer_upload.created = utc_now
            db.add(bulk_transfer_upload)

        # prepare data : BulkTransfer
        bulk_transfer_0_0 = BulkTransfer()
        bulk_transfer_0_0.issuer_address = self.upload_issuer_list[0]["address"]
        bulk_transfer_0_0.upload_id = self.upload_id_list[0]
        bulk_transfer_0_0.token_type = TokenType.IBET_SHARE.value
        bulk_transfer_0_0.token_address = "test_token_address_1"  # 抽出対象
        bulk_transfer_0_0.from_address = "test_from_address_1"
        bulk_transfer_0_0.to_address = "test_to_address_1"
        bulk_transfer_0_0.amount = 10
        bulk_transfer_0_0.status = 1
        db.add(bulk_transfer_0_0)

        bulk_transfer_0_1 = BulkTransfer()
        bulk_transfer_0_1.issuer_address = self.upload_issuer_list[0]["address"]
        bulk_transfer_0_1.upload_id = self.upload_id_list[0]
        bulk_transfer_0_1.token_type = TokenType.IBET_SHARE.value
        bulk_transfer_0_1.token_address = "test_token_address_1"  # 抽出対象
        bulk_transfer_0_1.from_address = "test_from_address_2"
        bulk_transfer_0_1.to_address = "test_to_address_2"
        bulk_transfer_0_1.amount = 10
        bulk_transfer_0_1.status = 1
        db.add(bulk_transfer_0_1)

        bulk_transfer_1_0 = BulkTransfer()
        bulk_transfer_1_0.issuer_address = self.upload_issuer_list[0]["address"]
        bulk_transfer_1_0.upload_id = self.upload_id_list[1]
        bulk_transfer_1_0.token_type = TokenType.IBET_SHARE.value
        bulk_transfer_1_0.token_address = "test_token_address_other"  # 抽出対象外
        bulk_transfer_1_0.from_address = "test_from_address_2"
        bulk_transfer_1_0.to_address = "test_to_address_2"
        bulk_transfer_1_0.amount = 10
        bulk_transfer_1_0.status = 1
        db.add(bulk_transfer_1_0)

        bulk_transfer_2_0 = BulkTransfer()
        bulk_transfer_2_0.issuer_address = self.upload_issuer_list[0]["address"]
        bulk_transfer_2_0.upload_id = self.upload_id_list[2]
        bulk_transfer_2_0.token_type = TokenType.IBET_SHARE.value
        bulk_transfer_2_0.token_address = "test_token_address_1"  # 抽出対象
        bulk_transfer_2_0.from_address = "test_from_address_3"
        bulk_transfer_2_0.to_address = "test_to_address_3"
        bulk_transfer_2_0.amount = 10
        bulk_transfer_2_0.status = 1
        db.add(bulk_transfer_2_0)

        db.commit()

        # request target API
        resp = client.get(
            self.test_url,
            headers={"issuer-address": self.upload_issuer_list[0]["address"]},
            params={"token_address": "test_token_address_1"},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "bulk_transfer_uploads": [
                {
                    "issuer_address": self.upload_issuer_list[0]["address"],
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_address": None,
                    "upload_id": self.upload_id_list[0],
                    "status": 0,
                    "created": pytz.timezone("UTC")
                    .localize(utc_now)
                    .astimezone(local_tz)
                    .isoformat(),
                },
                {
                    "issuer_address": self.upload_issuer_list[0]["address"],
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_address": None,
                    "upload_id": self.upload_id_list[2],
                    "status": 2,
                    "created": pytz.timezone("UTC")
                    .localize(utc_now)
                    .astimezone(local_tz)
                    .isoformat(),
                },
            ],
        }

    # <Normal_3>
    # offset / limit
    @pytest.mark.freeze_time("2021-05-20 12:34:56")
    def test_normal_3(self, client, db):
        # prepare data : Account(Issuer)
        for _issuer in self.upload_issuer_list:
            account = Account()
            account.issuer_address = _issuer["address"]
            account.keyfile = _issuer["keyfile"]
            db.add(account)

        # prepare data : BulkTransferUpload
        utc_now = datetime.now(UTC).replace(tzinfo=None)
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.upload_issuer_list[1]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
            bulk_transfer_upload.token_address = self.test_token_address
            bulk_transfer_upload.status = i
            bulk_transfer_upload.created = utc_now
            db.add(bulk_transfer_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.test_url,
            headers={"issuer-address": self.upload_issuer_list[1]["address"]},
            params={"offset": 1, "limit": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "bulk_transfer_uploads": [
                {
                    "issuer_address": self.upload_issuer_list[1]["address"],
                    "token_type": TokenType.IBET_SHARE.value,
                    "token_address": self.test_token_address,
                    "upload_id": self.upload_id_list[1],
                    "status": 1,
                    "created": pytz.timezone("UTC")
                    .localize(utc_now)
                    .astimezone(local_tz)
                    .isoformat(),
                }
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # invalid type : issuer-address
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(self.test_url, headers={"issuer-address": "DUMMY ADDRESS"})

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
