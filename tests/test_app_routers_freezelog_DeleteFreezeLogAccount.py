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
from sqlalchemy import select

from app.model.db import FreezeLogAccount


class TestDeleteFreezeLogAccount:
    # Target API endpoint
    base_url = "/freeze_log/accounts/"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        test_account_address = "0x1234567890123456789012345678900000000000"

        # Prepare data
        log_account = FreezeLogAccount()
        log_account.account_address = test_account_address
        log_account.keyfile = "test_keyfile_0"
        log_account.eoa_password = "test_password_0"
        db.add(log_account)

        db.commit()

        # Request target api
        resp = client.delete(self.base_url + test_account_address)

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": "0x1234567890123456789012345678900000000000",
            "is_deleted": True,
        }

        log_account_af = db.scalars(
            select(FreezeLogAccount)
            .where(FreezeLogAccount.account_address == test_account_address)
            .limit(1)
        ).first()
        assert log_account_af.is_deleted is True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    def test_error_1(self, client, db):
        test_account_address = "0x1234567890123456789012345678900000000000"

        # Request target api
        resp = client.delete(self.base_url + test_account_address)

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "account is not exists",
        }
