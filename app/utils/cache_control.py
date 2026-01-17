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

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware to control caching headers by whitelist policy.
    - Cache is enabled only for specific status codes.
    - For other status codes, caching is strongly disabled.

    The whitelist of status codes is selected based on RFC7231 semantics
    for cacheable responses in typical scenarios:
      200, 203, 204, 206, 300, 301, 404, 405, 410, 414, 501.
    """

    # Default whitelist: enable cache only for these status codes
    DEFAULT_CACHE_ENABLED_STATUSES: tuple[int, ...] = (
        200,
        203,
        204,
        206,
        300,
        301,
        404,
        405,
        410,
        414,
        501,
    )

    def __init__(
        self,
        app: ASGIApp,
        cache_enabled_statuses: tuple[int, ...] | None = None,
    ) -> None:
        super().__init__(app)
        self.cache_enabled_statuses = (
            cache_enabled_statuses
            if cache_enabled_statuses is not None
            else self.DEFAULT_CACHE_ENABLED_STATUSES
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        try:
            status_code = response.status_code
            cache_enabled = status_code in self.cache_enabled_statuses

            if cache_enabled:
                # Mirror only Cache-Control from request if provided
                req_cache_control = request.headers.get("Cache-Control")
                if req_cache_control is not None:
                    response.headers["Cache-Control"] = req_cache_control
            else:
                # Strongly disable caching for non-whitelisted status codes
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response.headers["Pragma"] = "no-cache"
                if "ETag" in response.headers:
                    del response.headers["ETag"]
                if "Expires" in response.headers:
                    del response.headers["Expires"]
        except Exception:
            # Do not break the response flow even if header manipulation fails
            pass
        return response
