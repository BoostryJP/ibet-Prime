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

import pytest
from fastapi import status
from fastapi.routing import APIRoute
from httpx import AsyncClient
from pydantic import BaseModel

from app.main import app


class _ResponseValidationSample(BaseModel):
    value: int


@pytest.mark.asyncio
class TestResponseValidationExceptionHandler:
    @staticmethod
    def _register_route(path: str, status_code: int) -> None:
        async def endpoint():
            return {"value": None}

        app.add_api_route(
            path,
            endpoint,
            methods=["GET"],
            response_model=_ResponseValidationSample,
            status_code=status_code,
        )

    @staticmethod
    def _remove_route(path: str) -> None:
        app.router.routes = [
            route
            for route in app.router.routes
            if not (
                isinstance(route, APIRoute)
                and route.path == path
                and route.name == "endpoint"
            )
        ]

    async def test_returns_original_body_when_validation_is_disabled(
        self, async_client: AsyncClient
    ):
        path = "/__test__/response-validation-disabled"
        self._register_route(path, status.HTTP_201_CREATED)
        try:
            with (
                mock.patch("app.main.RESPONSE_VALIDATION_MODE", False),
                mock.patch("app.main.LOG.warning") as warning_mock,
            ):
                response = await async_client.get(path)
        finally:
            self._remove_route(path)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {"value": None}
        warning_mock.assert_called_once()
        assert (
            "Invalid response: path=/__test__/response-validation-disabled, method=GET, detail=[{'type': 'int_type', 'loc': ('response', 'value'), 'msg': 'Input should be a valid integer', 'input': None}]"
            in warning_mock.call_args.args[0]
        )

    async def test_returns_internal_server_error_when_validation_is_enabled(
        self, async_client: AsyncClient
    ):
        path = "/__test__/response-validation-enabled"
        self._register_route(path, status.HTTP_201_CREATED)
        try:
            with mock.patch("app.main.RESPONSE_VALIDATION_MODE", True):
                response = await async_client.get(path)
        finally:
            self._remove_route(path)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"meta": {"code": 1, "title": "InternalServerError"}}
