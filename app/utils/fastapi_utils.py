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

import decimal
from typing import Any

import orjson
from fastapi.responses import ORJSONResponse

from app.exceptions import Integer64bitLimitExceededError
from config import RESPONSE_VALIDATION_MODE


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


class CustomORJSONResponse(ORJSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        try:
            result = orjson.dumps(
                content,
                option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
                default=decimal_default,
            )
            return result
        except TypeError as e:
            if e.args[0] == "Integer exceeds 64-bit range":
                raise Integer64bitLimitExceededError(
                    "Response data includes integer which exceeds 64-bit range"
                ) from None
            raise


def json_response(content: dict | list):
    if RESPONSE_VALIDATION_MODE:
        return content
    else:
        return CustomORJSONResponse(content=content)
