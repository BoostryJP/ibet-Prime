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

from app.model.db import Account, ChildAccount, IDXPersonalInfo, PersonalInfoDataSource


class TestListAllChildAccount:
    issuer_address = "0x89082C5dEcB1Ad23eda99B692A9B594F7044B846"

    child_account_address = [
        "0x9f07d281F2f78891637cD72C7a4a1b5da309449A",
        "0xfc4c13C222ddc98E9b409a543a725fe99911f978",
        "0xD4E5978FA40AC5f7aFe0E5E592B6408DfaEeA8b5",
        "0x36d82Ff9b5B9865F7a7Db7089833F098EC734d8d",
        "0xA59c9Ca97Fb946A0b61A1E86dC2c6918A47E2656",
    ]

    # Target API endpoint
    base_url = "/accounts/{}/child_accounts"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Normal search
    # - Personal information is not set
    def test_normal_1_1(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        db.add(_account)

        for i in range(1, 6):
            _child_account = ChildAccount()
            _child_account.issuer_address = self.issuer_address
            _child_account.child_account_index = i
            _child_account.child_account_address = self.child_account_address[i - 1]
            db.add(_child_account)

        db.commit()

        # Call API
        resp = client.get(self.base_url.format(self.issuer_address), params=None)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "offset": None, "limit": None, "total": 5},
            "child_accounts": [
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 1,
                    "child_account_address": self.child_account_address[0],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 2,
                    "child_account_address": self.child_account_address[1],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 3,
                    "child_account_address": self.child_account_address[2],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 4,
                    "child_account_address": self.child_account_address[3],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 5,
                    "child_account_address": self.child_account_address[4],
                    "personal_information": None,
                },
            ],
        }

    # <Normal_1_2>
    # Normal search
    # - Personal information is set
    def test_normal_1_2(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        db.add(_account)

        for i in range(1, 4):
            _child_account = ChildAccount()
            _child_account.issuer_address = self.issuer_address
            _child_account.child_account_index = i
            _child_account.child_account_address = self.child_account_address[i - 1]
            db.add(_child_account)

            _off_personal_info = IDXPersonalInfo()
            _off_personal_info.issuer_address = self.issuer_address
            _off_personal_info.account_address = self.child_account_address[i - 1]
            _off_personal_info.personal_info = {
                "key_manager": "SELF",
                "name": f"name_test_{i}",
                "postal_code": f"postal_code_test_{i}",
                "address": f"address_test_{i}",
                "email": f"email_test_{i}",
                "birth": f"birth_test_{i}",
                "is_corporate": False,
                "tax_category": i,
            }
            _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
            db.add(_off_personal_info)

        db.commit()

        # Call API
        resp = client.get(self.base_url.format(self.issuer_address), params=None)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "child_accounts": [
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 1,
                    "child_account_address": self.child_account_address[0],
                    "personal_information": {
                        "key_manager": "SELF",
                        "name": "name_test_1",
                        "postal_code": "postal_code_test_1",
                        "address": "address_test_1",
                        "email": "email_test_1",
                        "birth": "birth_test_1",
                        "is_corporate": False,
                        "tax_category": 1,
                    },
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 2,
                    "child_account_address": self.child_account_address[1],
                    "personal_information": {
                        "key_manager": "SELF",
                        "name": "name_test_2",
                        "postal_code": "postal_code_test_2",
                        "address": "address_test_2",
                        "email": "email_test_2",
                        "birth": "birth_test_2",
                        "is_corporate": False,
                        "tax_category": 2,
                    },
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 3,
                    "child_account_address": self.child_account_address[2],
                    "personal_information": {
                        "key_manager": "SELF",
                        "name": "name_test_3",
                        "postal_code": "postal_code_test_3",
                        "address": "address_test_3",
                        "email": "email_test_3",
                        "birth": "birth_test_3",
                        "is_corporate": False,
                        "tax_category": 3,
                    },
                },
            ],
        }

    # <Normal_2>
    # Sort order
    def test_normal_2(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        db.add(_account)

        for i in range(1, 6):
            _child_account = ChildAccount()
            _child_account.issuer_address = self.issuer_address
            _child_account.child_account_index = i
            _child_account.child_account_address = self.child_account_address[i - 1]
            db.add(_child_account)

        db.commit()

        # Call API
        resp = client.get(
            self.base_url.format(self.issuer_address), params={"sort_order": 1}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "offset": None, "limit": None, "total": 5},
            "child_accounts": [
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 5,
                    "child_account_address": self.child_account_address[4],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 4,
                    "child_account_address": self.child_account_address[3],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 3,
                    "child_account_address": self.child_account_address[2],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 2,
                    "child_account_address": self.child_account_address[1],
                    "personal_information": None,
                },
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 1,
                    "child_account_address": self.child_account_address[0],
                    "personal_information": None,
                },
            ],
        }

    # <Normal_3>
    # Offset / Limit
    def test_normal_3(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        db.add(_account)

        for i in range(1, 6):
            _child_account = ChildAccount()
            _child_account.issuer_address = self.issuer_address
            _child_account.child_account_index = i
            _child_account.child_account_address = self.child_account_address[i - 1]
            db.add(_child_account)

        db.commit()

        # Call API
        resp = client.get(
            self.base_url.format(self.issuer_address), params={"offset": 2, "limit": 1}
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "offset": 2, "limit": 1, "total": 5},
            "child_accounts": [
                {
                    "issuer_address": self.issuer_address,
                    "child_account_index": 3,
                    "child_account_address": self.child_account_address[2],
                    "personal_information": None,
                },
            ],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # 404: Issuer does not exist
    def test_error_1(self, client, db):
        # Prepare data
        for i in range(1, 6):
            _child_account = ChildAccount()
            _child_account.issuer_address = self.issuer_address
            _child_account.child_account_index = i
            _child_account.child_account_address = self.child_account_address[i - 1]
            db.add(_child_account)

        db.commit()

        # Call API
        resp = client.get(self.base_url.format(self.issuer_address), params=None)

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }
