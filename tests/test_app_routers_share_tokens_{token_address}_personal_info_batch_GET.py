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

from unittest import mock

from app.model.db import (
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressPersonalInfoBatchGET:
    # target API endpoint
    base_url = "/share/tokens/{}/personal_info/batch"

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",
        "0e778f46-864e-4ec0-b566-21bd31cf63ff",
        "0f33d48f-9e6e-4a36-a55e-5bbcbda69c80",
        "1c961f7d-e1ad-40e5-988b-cca3d6009643",
        "1e778f46-864e-4ec0-b566-21bd31cf63ff",
        "1f33d48f-9e6e-4a36-a55e-5bbcbda69c80",
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # 0 record
    def test_normal_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data: token issued by issuer_address
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_22_12
        db.add(token)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "uploads": [],
        }

    # Normal_2
    # multi records
    def test_normal_2(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data: token issued by issuer_address
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_22_12
        db.add(token)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.DONE.value
        db.add(batch_register_upload)

        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[1]
        batch_register_upload.status = (
            BatchRegisterPersonalInfoUploadStatus.PENDING.value
        )
        db.add(batch_register_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]),
            headers={"issuer-address": _issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "uploads": [
                {
                    "batch_id": self.upload_id_list[1],
                    "status": BatchRegisterPersonalInfoUploadStatus.PENDING.value,
                    "created": mock.ANY,
                },
                {
                    "batch_id": self.upload_id_list[0],
                    "status": BatchRegisterPersonalInfoUploadStatus.DONE.value,
                    "created": mock.ANY,
                },
            ],
        }

    # Normal_3
    # filter by status
    def test_normal_3(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data: token issued by issuer_address
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_22_12
        db.add(token)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.DONE.value
        db.add(batch_register_upload)

        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[1]
        batch_register_upload.status = (
            BatchRegisterPersonalInfoUploadStatus.PENDING.value
        )
        db.add(batch_register_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]),
            headers={"issuer-address": _issuer_address},
            params={"status": BatchRegisterPersonalInfoUploadStatus.DONE.value},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "uploads": [
                {
                    "batch_id": self.upload_id_list[0],
                    "status": BatchRegisterPersonalInfoUploadStatus.DONE.value,
                    "created": mock.ANY,
                }
            ],
        }

    # Normal_4
    # pagination
    def test_normal_4(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data: token issued by issuer_address
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_22_12
        db.add(token)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.DONE.value
        db.add(batch_register_upload)

        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[1]
        batch_register_upload.status = (
            BatchRegisterPersonalInfoUploadStatus.PENDING.value
        )
        db.add(batch_register_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]),
            headers={"issuer-address": _issuer_address},
            params={"offset": 0, "limit": 1},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": 0, "limit": 1, "total": 2},
            "uploads": [
                {
                    "batch_id": self.upload_id_list[1],
                    "status": BatchRegisterPersonalInfoUploadStatus.PENDING.value,
                    "created": mock.ANY,
                }
            ],
        }

    # Normal_5
    # sort
    def test_normal_5(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data: token issued by issuer_address
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_22_12
        db.add(token)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.DONE.value
        db.add(batch_register_upload)

        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address
        batch_register_upload.upload_id = self.upload_id_list[1]
        batch_register_upload.status = (
            BatchRegisterPersonalInfoUploadStatus.PENDING.value
        )
        db.add(batch_register_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]),
            headers={"issuer-address": _issuer_address},
            params={"sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "uploads": [
                {
                    "batch_id": self.upload_id_list[0],
                    "status": BatchRegisterPersonalInfoUploadStatus.DONE.value,
                    "created": mock.ANY,
                },
                {
                    "batch_id": self.upload_id_list[1],
                    "status": BatchRegisterPersonalInfoUploadStatus.PENDING.value,
                    "created": mock.ANY,
                },
            ],
        }

    #########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # RequestValidationError: issuer_address
    def test_error_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data: token issued by issuer_address
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_22_12
        db.add(token)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]), headers={}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # Error_2
    # NotFound
    # token not found
    def test_error_2(self, client, db):
        _issuer_account_1 = config_eth_account("user1")
        _issuer_address_1 = _issuer_account_1["address"]

        _issuer_account_2 = config_eth_account("user2")
        _issuer_address_2 = _issuer_account_2["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data: token issued by issuer_address_2
        token = Token()
        token.type = TokenType.IBET_SHARE.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address_2
        token.token_address = _token_address
        token.abi = ""
        token.version = TokenVersion.V_22_12
        db.add(token)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _issuer_address_2
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.DONE.value
        db.add(batch_register_upload)

        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address, self.upload_id_list[0]),
            headers={"issuer-address": _issuer_address_1},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }
