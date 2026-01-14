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
    Middleware to control caching headers.

    - For 4xx and 5xx responses: enforce no-store/no-cache headers and remove validators.
    - For other responses: mirror incoming request's Cache-Control if present.
    """

    def __init__(self, app: ASGIApp, statuses: tuple[int, ...] | None = None) -> None:
        super().__init__(app)
        # Optional: if specific statuses are provided, they can override the default behavior
        self.statuses = statuses

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        try:
            status_code = response.status_code
            is_error = (self.statuses is None and 400 <= status_code < 600) or (
                self.statuses is not None and status_code in self.statuses
            )

            if is_error:
                # Strongly disable caching on clients/proxies for error responses
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                # Legacy proxies hint
                response.headers["Pragma"] = "no-cache"
                # Remove validators/expiry if present
                if "ETag" in response.headers:
                    del response.headers["ETag"]
                if "Expires" in response.headers:
                    del response.headers["Expires"]
            else:
                # Mirror request Cache-Control if provided, otherwise keep existing response behavior
                req_cache_control = request.headers.get("Cache-Control")
                if req_cache_control is not None:
                    response.headers["Cache-Control"] = req_cache_control
        except Exception:
            # Do not break the response flow even if header manipulation fails
            pass
        return response
