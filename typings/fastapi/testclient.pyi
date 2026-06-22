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

from typing import Any, Literal

import httpx

class TestClient:
    def __init__(
        self,
        app: Any,
        base_url: str = ...,
        raise_server_exceptions: bool = ...,
        root_path: str = ...,
        backend: Literal["asyncio", "trio"] = ...,
        backend_options: dict[str, Any] | None = ...,
        cookies: Any = ...,
        headers: dict[str, str] | None = ...,
        follow_redirects: bool = ...,
        client: tuple[str, int] = ...,
    ) -> None: ...
    def request(
        self,
        method: str,
        url: Any,
        **kwargs: Any,
    ) -> httpx.Response: ...
    def get(self, url: Any, **kwargs: Any) -> httpx.Response: ...
    def options(self, url: Any, **kwargs: Any) -> httpx.Response: ...
    def head(self, url: Any, **kwargs: Any) -> httpx.Response: ...
    def post(self, url: Any, **kwargs: Any) -> httpx.Response: ...
    def put(self, url: Any, **kwargs: Any) -> httpx.Response: ...
    def patch(self, url: Any, **kwargs: Any) -> httpx.Response: ...
    def delete(self, url: Any, **kwargs: Any) -> httpx.Response: ...
