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

from app.model.db import Account, ChildAccount, IDXPersonalInfo, PersonalInfoDataSource


class TestRetrieveChildAccount:
    issuer_address = "0x89082C5dEcB1Ad23eda99B692A9B594F7044B846"
    child_account_address = "0x9f07d281F2f78891637cD72C7a4a1b5da309449A"

    # Target API endpoint
    base_url = "/accounts/{}/child_accounts/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Personal information is not set
    def test_normal_1_1(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        db.add(_account)

        _child_account = ChildAccount()
        _child_account.issuer_address = self.issuer_address
        _child_account.child_account_index = 1
        _child_account.child_account_address = self.child_account_address
        db.add(_child_account)

        db.commit()

        # Call API
        resp = client.get(self.base_url.format(self.issuer_address, 1))

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": self.issuer_address,
            "child_account_index": 1,
            "child_account_address": self.child_account_address,
            "personal_information": None,
            "created": None,
            "modified": None,
        }

    # <Normal_1_2>
    # Personal information is set
    @pytest.mark.freeze_time("2024-10-28 12:34:56")
    def test_normal_1_2(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        db.add(_account)

        _child_account = ChildAccount()
        _child_account.issuer_address = self.issuer_address
        _child_account.child_account_index = 1
        _child_account.child_account_address = self.child_account_address
        db.add(_child_account)

        _off_personal_info = IDXPersonalInfo()
        _off_personal_info.issuer_address = self.issuer_address
        _off_personal_info.account_address = self.child_account_address
        _off_personal_info.personal_info = {
            "key_manager": "SELF",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
            "tax_category": 10,
        }
        _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
        db.add(_off_personal_info)

        db.commit()

        # Call API
        resp = client.get(self.base_url.format(self.issuer_address, 1))

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": self.issuer_address,
            "child_account_index": 1,
            "child_account_address": self.child_account_address,
            "personal_information": {
                "key_manager": "SELF",
                "name": "name_test",
                "postal_code": "postal_code_test",
                "address": "address_test",
                "email": "email_test",
                "birth": "birth_test",
                "is_corporate": False,
                "tax_category": 10,
            },
            "created": "2024-10-28T21:34:56+09:00",
            "modified": "2024-10-28T21:34:56+09:00",
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # 404: Issuer does not exist
    def test_error_1(self, client, db):
        # Call API
        resp = client.get(self.base_url.format(self.issuer_address, 1))

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }

    # <Error_2>
    # 404: Issuer does not exist
    def test_error_2(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        db.add(_account)
        db.commit()

        # Call API
        resp = client.get(self.base_url.format(self.issuer_address, 1))

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "child account does not exist",
        }
