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
from app.model.db import Account, AccountRsaStatus
from tests.account_config import config_eth_account


class TestAppRoutersAccountsIssuerAddressGET:
    # target API endpoint
    base_url = "/accounts/{}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # rsa_public_key is None
    def test_normal_1(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.rsa_status = AccountRsaStatus.UNSET.value
        db.add(account)

        resp = client.get(self.base_url.format(_admin_address))

        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _admin_account["address"],
            "rsa_public_key": None,
            "rsa_status": AccountRsaStatus.UNSET.value,
            "is_deleted": False
        }

    # <Normal_2>
    # rsa_public_key is not None
    def test_normal_2(self, client, db):
        _admin_account = config_eth_account("user1")
        _admin_address = _admin_account["address"]
        _admin_keyfile = _admin_account["keyfile_json"]
        _admin_rsa_public_key = _admin_account["rsa_public_key"]

        # prepare data
        account = Account()
        account.issuer_address = _admin_address
        account.keyfile = _admin_keyfile
        account.rsa_public_key = _admin_rsa_public_key
        account.rsa_status = AccountRsaStatus.CHANGING.value
        db.add(account)

        resp = client.get(self.base_url.format(_admin_address))

        assert resp.status_code == 200
        assert resp.json() == {
            "issuer_address": _admin_account["address"],
            "rsa_public_key": _admin_account["rsa_public_key"],
            "rsa_status": AccountRsaStatus.CHANGING.value,
            "is_deleted": False
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # No data
    def test_error_1(self, client, db):
        resp = client.get(self.base_url.format("non_existent_issuer_address"))

        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1, "title": "NotFound"
            },
            "detail": "issuer does not exist"
        }
