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
import base64

from app.model.db import UploadFile


class TestAppRoutersFilesFileIdDELETE:
    # target API endpoint
    base_url = "/files/{file_id}"
    issuer_address = "0x1234567890123456789012345678900000000001"
    token_address = "0x1234567890123456789012345678900000000011"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
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
        db.add(_upload_file)

        # request target api
        resp = client.delete(
            self.base_url.format(file_id="file_id_1"),
            headers={
                "issuer-address": self.issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _upload_file_list = db.query(UploadFile).all()
        assert len(_upload_file_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    # Required
    # Header
    def test_error_1(self, client, db):
        # request target api
        resp = client.delete(
            self.base_url.format(file_id="file_id_1"),
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_2>
    # Parameter Error
    # Invalid
    def test_error_2(self, client, db):
        # request target api
        resp = client.delete(
            self.base_url.format(file_id="file_id_1"),
            headers={
                "issuer-address": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_3>
    # Not Found
    def test_error_3(self, client, db):
        file_content = """test data
12345 67890
  あいうえお　かきくけこ
    😃😃😃😃
abc def"""

        file_content_bin = file_content.encode()

        # prepare data
        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_1"
        _upload_file.issuer_address = "0x1234567890123456789012345678900000000002"  # not target
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_1"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_1"
        _upload_file.label = "label_1"
        db.add(_upload_file)

        # request target API
        resp = client.delete(
            self.base_url.format(file_id="file_id_1"),
            headers={
                "issuer-address": self.issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "file not found"
        }
