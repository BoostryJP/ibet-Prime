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


class TestOpenAPIDoc:
    # テスト対象API
    apiurl_base = "/openapi.json"

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client):
        apiurl = self.apiurl_base
        resp = await async_client.get(apiurl)

        assert resp.status_code == 200
        assert resp.json()["openapi"] == "3.1.0"
        assert resp.json()["info"]["title"] == "ibet Prime"
