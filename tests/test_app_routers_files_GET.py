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

from app.model.db import UploadFile


class TestAppRoutersFilesGET:
    # target API endpoint
    base_url = "/files"
    issuer_address = "0x1234567890123456789012345678900000000001"
    token_address = "0x1234567890123456789012345678900000000011"
    file_content = """test data
12345 67890
  あいうえお　かきくけこ
    😃😃😃😃
abc def"""

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    def test_normal_1(self, client, db):
        # request target api
        resp = client.get(self.base_url)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "files": [],
        }

    # <Normal_2>
    # 1 record
    def test_normal_2(self, client, db):
        file_content_1_bin = self.file_content.encode()

        # prepare data
        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_1"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_1"
        _upload_file.content = file_content_1_bin
        _upload_file.content_size = len(file_content_1_bin)
        _upload_file.description = "description_1"
        _upload_file.label = "label_1"
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 1},
            "files": [
                {
                    "file_id": "file_id_1",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_1",
                    "content_size": len(file_content_1_bin),
                    "description": "description_1",
                    "label": "label_1",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_3>
    # 2 record
    def test_normal_3(self, client, db):
        file_content_bin = self.file_content.encode()

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
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_2"
        _upload_file.issuer_address = "0x1234567890123456789012345678900000000001"
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_2"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_2"
        _upload_file.label = "label_2"
        _upload_file.created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        # request target api
        resp = client.get(
            self.base_url,
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 2},
            "files": [
                {
                    "file_id": "file_id_2",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_2",
                    "content_size": len(file_content_bin),
                    "description": "description_2",
                    "label": "label_2",
                    "created": "2022-01-02T09:20:30.000001+09:00",
                },
                {
                    "file_id": "file_id_1",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_1",
                    "content_size": len(file_content_bin),
                    "description": "description_1",
                    "label": "label_1",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_4_1>
    # Search Filter
    # issuer_address
    def test_normal_4_1(self, client, db):
        file_content_bin = self.file_content.encode()

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
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_2"
        _upload_file.issuer_address = (
            "0x1234567890123456789012345678900000000002"  # not target
        )
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_2"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_2"
        _upload_file.label = "label_2"
        _upload_file.created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        # request target api
        resp = client.get(
            self.base_url,
            headers={
                "issuer-address": self.issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "files": [
                {
                    "file_id": "file_id_1",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_1",
                    "content_size": len(file_content_bin),
                    "description": "description_1",
                    "label": "label_1",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_4_2>
    # Search Filter
    # relation
    def test_normal_4_2(self, client, db):
        file_content_bin = self.file_content.encode()

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
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_2"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = "uuid_test_foo_bar"  # not target
        _upload_file.file_name = "file_name_2"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_2"
        _upload_file.label = "label_2"
        _upload_file.created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        # request target api
        resp = client.get(
            self.base_url,
            params={
                "relation": self.token_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "files": [
                {
                    "file_id": "file_id_1",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_1",
                    "content_size": len(file_content_bin),
                    "description": "description_1",
                    "label": "label_1",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_4_3>
    # Search Filter
    # file_name
    def test_normal_4_3(self, client, db):
        file_content_bin = self.file_content.encode()

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
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_2"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "test_foo_bar_1"  # not target
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_2"
        _upload_file.label = "label_2"
        _upload_file.created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        # request target api
        resp = client.get(
            self.base_url,
            params={
                "file_name": "name",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 2},
            "files": [
                {
                    "file_id": "file_id_1",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_1",
                    "content_size": len(file_content_bin),
                    "description": "description_1",
                    "label": "label_1",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_4_4_1>
    # Search Filter
    # label: default value
    def test_normal_4_4_1(self, client, db):
        file_content_bin = self.file_content.encode()

        # prepare data
        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_1"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_1"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_1"
        _upload_file.label = ""
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_2"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_2"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_2"
        _upload_file.label = "label_2"  # not null
        _upload_file.created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_3"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_3"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_3"
        _upload_file.label = " "  # half-width space
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_4"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_4"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_4"
        _upload_file.label = "　"  # full-width space
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        # request target api
        resp = client.get(
            self.base_url,
            params={
                "label": "",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 4},
            "files": [
                {
                    "file_id": "file_id_1",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_1",
                    "content_size": len(file_content_bin),
                    "description": "description_1",
                    "label": "",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_4_4_2>
    # Search Filter
    # label
    def test_normal_4_4_2(self, client, db):
        file_content_bin = self.file_content.encode()

        # prepare data
        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_1"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_1"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_1"
        _upload_file.label = "単語label_1"
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        db.commit()

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_2"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_2"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_2"
        _upload_file.label = "label_2"  # not target
        _upload_file.created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        db.commit()

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_3"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_3"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_3"
        _upload_file.label = "label単語_3"
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        db.commit()

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_4"
        _upload_file.issuer_address = self.issuer_address
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_4"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_4"
        _upload_file.label = "label_4単語"
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url,
            params={
                "label": "単語",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 4},
            "files": [
                {
                    "file_id": "file_id_4",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_4",
                    "content_size": len(file_content_bin),
                    "description": "description_4",
                    "label": "label_4単語",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
                {
                    "file_id": "file_id_3",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_3",
                    "content_size": len(file_content_bin),
                    "description": "description_3",
                    "label": "label単語_3",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
                {
                    "file_id": "file_id_1",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_1",
                    "content_size": len(file_content_bin),
                    "description": "description_1",
                    "label": "単語label_1",
                    "created": "2022-01-02T00:20:30.000001+09:00",
                },
            ],
        }

    # <Normal_5>
    # Pagination
    def test_normal_5(self, client, db):
        file_content_bin = self.file_content.encode()

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
        _upload_file.created = datetime.strptime(
            "2022/01/01 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        db.commit()

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_2"
        _upload_file.issuer_address = "0x1234567890123456789012345678900000000001"
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_2"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_2"
        _upload_file.label = "label_2"
        _upload_file.created = datetime.strptime(
            "2022/01/02 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/02
        db.add(_upload_file)

        db.commit()

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_3"
        _upload_file.issuer_address = "0x1234567890123456789012345678900000000001"
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_3"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_3"
        _upload_file.label = "label_3"
        _upload_file.created = datetime.strptime(
            "2022/01/02 15:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_upload_file)

        db.commit()

        _upload_file = UploadFile()
        _upload_file.file_id = "file_id_4"
        _upload_file.issuer_address = "0x1234567890123456789012345678900000000001"
        _upload_file.relation = self.token_address
        _upload_file.file_name = "file_name_4"
        _upload_file.content = file_content_bin
        _upload_file.content_size = len(file_content_bin)
        _upload_file.description = "description_4"
        _upload_file.label = "label_4"
        _upload_file.created = datetime.strptime(
            "2022/01/03 00:20:30.000001", "%Y/%m/%d %H:%M:%S.%f"
        )  # JST 2022/01/03
        db.add(_upload_file)

        db.commit()

        # request target api
        resp = client.get(
            self.base_url,
            params={"offset": 1, "limit": 2},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 4, "offset": 1, "limit": 2, "total": 4},
            "files": [
                {
                    "file_id": "file_id_3",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_3",
                    "content_size": len(file_content_bin),
                    "description": "description_3",
                    "label": "label_3",
                    "created": "2022-01-03T00:20:30.000001+09:00",
                },
                {
                    "file_id": "file_id_2",
                    "issuer_address": self.issuer_address,
                    "relation": self.token_address,
                    "file_name": "file_name_2",
                    "content_size": len(file_content_bin),
                    "description": "description_2",
                    "label": "label_2",
                    "created": "2022-01-02T09:20:30.000001+09:00",
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Parameter Error
    # Query
    def test_error_1(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
            params={"offset": "test", "limit": "test"},
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
            ],
        }

    # <Error_2>
    # Parameter Error
    # Header
    def test_error_2(self, client, db):
        # request target API
        resp = client.get(
            self.base_url,
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
