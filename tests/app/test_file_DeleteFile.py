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
from sqlalchemy import select

from app.model.db import UploadFile


class TestDeleteFile:
    # target API endpoint
    base_url = "/files/{file_id}"
    issuer_address = "0x1234567890123456789012345678900000000001"
    token_address = "0x1234567890123456789012345678900000000011"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        file_content = """test data
12345 67890
  あいうえお　かきくけこ
    😃😃😃😃
abc def"""

        file_content_bin = file_content.encode()

        # prepare data
        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_1"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_1"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_1"
        _upload_file.label = "label_1"
        async_db.add(_upload_file)

        await async_db.commit()

        # request target api
        resp = await async_client.delete(
            self.base_url.format(file_id="file_id_1"),
            headers={
                "issuer-address": self.issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _upload_file_list = (await async_db.scalars(select(UploadFile))).all()
        assert len(_upload_file_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    # Required
    # Header
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # request target api
        resp = await async_client.delete(
            self.base_url.format(file_id="file_id_1"),
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

    # <Error_2>
    # Parameter Error
    # Invalid
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # request target api
        resp = await async_client.delete(
            self.base_url.format(file_id="file_id_1"),
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

    # <Error_3>
    # Not Found
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        file_content = """test data
12345 67890
  あいうえお　かきくけこ
    😃😃😃😃
abc def"""

        file_content_bin = file_content.encode()

        # prepare data
        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_1"
        _upload_file.issuer_address = (
            "0x1234567890123456789012345678900000000002"  # not target
        )
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_1"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_1"
        _upload_file.label = "label_1"
        async_db.add(_upload_file)

        await async_db.commit()

        # request target API
        resp = await async_client.delete(
            self.base_url.format(file_id="file_id_1"),
            headers={
                "issuer-address": self.issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "file not found",
        }
