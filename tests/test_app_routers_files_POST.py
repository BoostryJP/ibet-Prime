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
from unittest import mock
import pytz

from config import TZ
from app.model.db import UploadFile

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


class TestAppRoutersFilesPOST:
    # target API endpoint
    base_url = "/files"
    issuer_address = "0x1234567890123456789012345678900000000001"
    token_address = "0x1234567890123456789012345678900000000011"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # text file
    def test_normal_1(self, client, db):
        file_content = """test data
12345 67890
  あいうえお　かきくけこ
    😃😃😃😃
abc def"""

        file_content_bin = file_content.encode()

        # request target api
        req_param = {
            "relation": self.token_address,
            "file_name": "file_name_1",
            "content": base64.b64encode(file_content_bin).decode(),
            "description": "description_1",
            "label": "label_1"
        }
        resp = client.post(
            self.base_url,
            json=req_param,
            headers={
                "issuer-address": self.issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200

        _upload_file = db.query(UploadFile).first()
        assert _upload_file.file_id is not None
        assert _upload_file.issuer_address == self.issuer_address
        assert _upload_file.relation == self.token_address
        assert _upload_file.file_name == req_param["file_name"]
        assert _upload_file.content == file_content_bin
        assert _upload_file.content_size == len(file_content_bin)
        assert _upload_file.description == req_param["description"]
        assert _upload_file.label == req_param["label"]

        assert resp.json() == {
            "file_id": _upload_file.file_id,
            "issuer_address": self.issuer_address,
            "relation": req_param["relation"],
            "file_name": req_param["file_name"],
            "content_size": len(file_content_bin),
            "description": req_param["description"],
            "label": req_param["label"],
            "created": utc_tz.localize(_upload_file.created).astimezone(local_tz).isoformat()
        }

    # <Normal_2>
    # binary file
    def test_normal_2(self, client, db):
        file_content_bin = b'x00x01x02x03x04x05x06x07'

        # request target api
        req_param = {
            "relation": self.token_address,
            "file_name": "file_name_1",
            "content": base64.b64encode(file_content_bin).decode(),
            "description": "description_1",
            "label": "label_1"
        }
        resp = client.post(
            self.base_url,
            json=req_param,
            headers={
                "issuer-address": self.issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200

        _upload_file = db.query(UploadFile).first()
        assert _upload_file.file_id is not None
        assert _upload_file.issuer_address == self.issuer_address
        assert _upload_file.relation == self.token_address
        assert _upload_file.file_name == req_param["file_name"]
        assert _upload_file.content == file_content_bin
        assert _upload_file.content_size == len(file_content_bin)
        assert _upload_file.description == req_param["description"]
        assert _upload_file.label == req_param["label"]

        assert resp.json() == {
            "file_id": _upload_file.file_id,
            "issuer_address": self.issuer_address,
            "relation": req_param["relation"],
            "file_name": req_param["file_name"],
            "content_size": len(file_content_bin),
            "description": req_param["description"],
            "label": req_param["label"],
            "created": utc_tz.localize(_upload_file.created).astimezone(local_tz).isoformat()
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    # Required
    # Header, Body
    def test_error_1(self, client, db):
        # request target api
        resp = client.post(
            self.base_url,
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
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_2>
    # Parameter Error
    # Required
    # Body
    def test_error_2(self, client, db):
        # request target api
        resp = client.post(
            self.base_url,
            json={},
            headers={
                "issuer-address": self.issuer_address,
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
                    "loc": ["body", "file_name"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "content"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_3>
    # Parameter Error
    # Max Length
    # Body
    @mock.patch("app.model.schema.file.MAX_UPLOAD_FILE_SIZE", 6)
    def test_error_3(self, client, db):
        file_content_bin = b'x00x01x02x03x04x05x06x07'

        # request target api
        resp = client.post(
            self.base_url,
            json={
                "relation": "123456789012345678901234567890123456789012345678901",
                "file_name": "12345678901234567890123456789012345678901234567890"
                             "12345678901234567890123456789012345678901234567890"
                             "12345678901234567890123456789012345678901234567890"
                             "12345678901234567890123456789012345678901234567890"
                             "123456789012345678901234567890123456789012345678901234567",
                "content": base64.b64encode(file_content_bin).decode(),
                "description": "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "12345678901234567890123456789012345678901234567890"
                               "123456789012345678901234567890123456789012345678901",
                "label": "12345678901234567890123456789012345678901234567890"
                         "12345678901234567890123456789012345678901234567890"
                         "12345678901234567890123456789012345678901234567890"
                         "123456789012345678901234567890123456789012345678901"
            },
            headers={
                "issuer-address": self.issuer_address,
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
                    "loc": ["body", "relation"],
                    "msg": "ensure this value has at most 50 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 50}
                },
                {
                    "loc": ["body", "file_name"],
                    "msg": "ensure this value has at most 256 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 256}
                },
                {
                    "loc": ["body", "content"],
                    "msg": "file size(Base64-decoded size) must be less than or equal to 6",
                    "type": "value_error",
                },
                {
                    "loc": ["body", "description"],
                    "msg": "ensure this value has at most 1000 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 1000}
                },
                {
                    "loc": ["body", "label"],
                    "msg": "ensure this value has at most 200 characters",
                    "type": "value_error.any_str.max_length",
                    "ctx": {"limit_value": 200}
                },
            ]
        }

    # <Error_4>
    # Parameter Error
    # Not Base64
    def test_error_4(self, client, db):

        # request target api
        req_param = {
            "relation": self.token_address,
            "file_name": "file_name_1",
            "content": "あいう",
            "description": "description_1",
            "label": "label_1",
        }
        resp = client.post(
            self.base_url,
            json=req_param,
            headers={
                "issuer-address": self.issuer_address,
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
                    "loc": ["body", "content"],
                    "msg": "content is not a Base64-encoded string",
                    "type": "value_error",
                },
            ]
        }
