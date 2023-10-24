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

from app.model.db import IDXPersonalInfo
from tests.account_config import config_eth_account


class TestAppRoutersPersonalInfoGET:
    # target API endpoint
    url = "/personal_info"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal Case 1>
    # 0 record
    def test_normal_1(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]

        # request target API
        resp = client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "limit": None, "offset": None, "total": 0},
            "personal_info": [],
        }

    # <Normal Case 2>
    # 1 record
    def test_normal_2(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(personal_info_idx)

        # request target API
        resp = client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "personal_info": [
                {
                    "id": 1,
                    "account_address": account_address1,
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                }
            ],
        }

    # <Normal_3>
    # Multi record
    def test_normal_3(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(personal_info_idx)

        # request target API
        resp = client.get(
            self.url,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "id": 1,
                    "account_address": account_address1,
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
                {
                    "id": 2,
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
                {
                    "id": 3,
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
            ],
        }

    # <Normal_4>
    # Pagination
    def test_normal_4(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        db.add(personal_info_idx)

        # request target API
        req_param = {"limit": 2, "offset": 1}
        resp = client.get(
            self.url,
            params=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": 2, "offset": 1, "total": 3},
            "personal_info": [
                {
                    "id": 2,
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
                {
                    "id": 3,
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
            ],
        }

    # <Normal_5>
    # Sort
    def test_normal_5(self, client, db):
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        account_address1 = "account_address1"
        account_address2 = "account_address2"
        account_address3 = "account_address3"

        # prepare data
        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address1
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = "2023-10-23 00:00:00"
        db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address2
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            # "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = "2023-10-23 00:00:01"
        db.add(personal_info_idx)

        personal_info_idx = IDXPersonalInfo()
        personal_info_idx.issuer_address = issuer_address
        personal_info_idx.account_address = account_address3
        personal_info_idx.personal_info = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": None,
            "is_corporate": False,
            "tax_category": 10,
        }
        personal_info_idx.created = "2023-10-23 00:00:02"
        db.add(personal_info_idx)

        # request target API
        req_param = {"sort_order": 1}
        resp = client.get(
            self.url,
            params=req_param,
            headers={
                "issuer-address": issuer_address,
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "limit": None, "offset": None, "total": 3},
            "personal_info": [
                {
                    "id": 3,
                    "account_address": account_address3,
                    "personal_info": {
                        "key_manager": "key_manager_test3",
                        "name": "name_test3",
                        "postal_code": "postal_code_test3",
                        "address": "address_test3",
                        "email": "email_test3",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
                {
                    "id": 2,
                    "account_address": account_address2,
                    "personal_info": {
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "address": "address_test2",
                        "email": "email_test2",
                        "birth": None,
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
                {
                    "id": 1,
                    "account_address": account_address1,
                    "personal_info": {
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "address": "address_test1",
                        "email": "email_test1",
                        "birth": "birth_test1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                    "created": mock.ANY,
                },
            ],
        }
