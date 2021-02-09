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
import time

from app.model.db import Account
from datetime import datetime


class TestAppRoutersAccountAccountPUT:
    # テスト対象API
    apiurl = "/account"

    ###########################################################################
    # 正常系
    ###########################################################################

    # ＜正常系1＞
    def test_normal_1(self, client, db):
        accounts_before = db.query(Account).all()

        resp = client.put(self.apiurl)

        assert resp.status_code == 200
        assert resp.json()["issuer_address"] is not None

        # バックグラウンドタスク待ち合わせ
        time.sleep(60)

        accounts_after = db.query(Account).all()

        assert 0 == len(accounts_before)
        assert 1 == len(accounts_after)
        account_1 = accounts_after[0]
        assert account_1.issuer_address == resp.json()["issuer_address"]
        assert account_1.keyfile is not None
        assert account_1.rsa_private_key is not None
        assert account_1.rsa_public_key is not None

    ###########################################################################
    # エラー系
    ###########################################################################
