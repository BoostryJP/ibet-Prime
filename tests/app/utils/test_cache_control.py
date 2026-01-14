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


class TestCacheControl:
    @pytest.mark.asyncio
    async def test_success_mirror_request_headers(self, async_client):
        headers = {
            "Cache-Control": "max-age=60, public",
        }
        resp = await async_client.get("/e2ee", headers=headers)

        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "max-age=60, public"

    @pytest.mark.asyncio
    async def test_404_enforce_no_store(self, async_client):
        resp = await async_client.get("/not-found-path")

        assert resp.status_code == 404  # Not Found
        assert (
            resp.headers.get("Cache-Control")
            == "no-store, no-cache, must-revalidate, max-age=0"
        )
        assert resp.headers.get("Pragma") == "no-cache"
        assert resp.headers.get("ETag") is None
        assert resp.headers.get("Last-Modified") is None
        assert resp.headers.get("Expires") is None

    @pytest.mark.asyncio
    async def test_405_enforce_no_store(self, async_client):
        resp = await async_client.post("/e2ee")  # MethodNotAllowed

        assert resp.status_code == 405
        assert (
            resp.headers.get("Cache-Control")
            == "no-store, no-cache, must-revalidate, max-age=0"
        )
        assert resp.headers.get("Pragma") == "no-cache"
        assert resp.headers.get("ETag") is None
        assert resp.headers.get("Last-Modified") is None
        assert resp.headers.get("Expires") is None
