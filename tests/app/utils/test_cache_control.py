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
    async def test_success_no_header_when_absent_on_cache_enabled_status(
        self, async_client
    ):
        # No Cache-Control in request: for cache-enabled status (200),
        # middleware should not set any Cache-Control
        resp = await async_client.get("/e2ee")

        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") is None

    @pytest.mark.asyncio
    async def test_success_mirror_request_headers(self, async_client):
        # Cache-Control in request: for cache-enabled status (200),
        # middleware should mirror Cache-Control from request
        headers = {
            "Cache-Control": "max-age=60, public",
        }
        resp = await async_client.get("/e2ee", headers=headers)

        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "max-age=60, public"

    @pytest.mark.asyncio
    async def test_method_not_allowed_without_header(self, async_client):
        # POST to GET-only endpoint returns 405 (Method not allowed).
        # Without request header, Cache-Control should not be set.
        resp = await async_client.post("/e2ee")

        assert resp.status_code == 405
        assert resp.headers.get("Cache-Control") is None

    @pytest.mark.asyncio
    async def test_method_not_allowed_with_header_mirrored(self, async_client):
        # 405 (Method not allowed) should mirror Cache-Control from request when provided
        headers = {"Cache-Control": "private, max-age=10"}
        resp = await async_client.post("/e2ee", headers=headers)

        assert resp.status_code == 405
        assert resp.headers.get("Cache-Control") == "private, max-age=10"

    @pytest.mark.asyncio
    async def test_error_cache_disabled_on_service_unavailable(self, async_client):
        # Trigger 503 on /healthcheck by mocking DB connection error
        from unittest import mock

        with mock.patch(
            "sqlalchemy.ext.asyncio.AsyncSession.connection",
            mock.MagicMock(side_effect=Exception()),
        ):
            resp = await async_client.get("/healthcheck")

        assert resp.status_code == 503
        assert (
            resp.headers.get("Cache-Control")
            == "no-store, no-cache, must-revalidate, max-age=0"
        )
        assert resp.headers.get("Pragma") == "no-cache"
        assert resp.headers.get("ETag") is None
        assert resp.headers.get("Expires") is None
