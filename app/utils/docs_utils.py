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
from typing import (
    List,
    Dict,
    Any
)

from pydantic import BaseModel
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError

from app.exceptions import (
    InvalidParameterError,
    SendTransactionError,
    AuthorizationError,
    ServiceUnavailableError
)


class MetaModel(BaseModel):
    code: int
    title: str


class Error400MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 1
            properties["title"]["example"] = "InvalidParameterError"


class Error400Model(BaseModel):
    meta: Error400MetaModel
    detail: str


class Error401MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 1
            properties["title"]["example"] = "AuthorizationError"


class Error401Model(BaseModel):
    meta: Error401MetaModel
    detail: str


class Error404MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 1
            properties["title"]["example"] = "NotFound"


class Error404Model(BaseModel):
    meta: Error404MetaModel
    detail: str


class Error405MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 1
            properties["title"]["example"] = "MethodNotAllowed"


class Error405Model(BaseModel):
    meta: Error405MetaModel
    detail: str


class Error422MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 1
            properties["title"]["example"] = "RequestValidationError"


class Error422DetailModel(BaseModel):
    loc: List[str]
    msg: str
    type: str

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["loc"]["example"] = ["header", "issuer-address"]
            properties["msg"]["example"] = "field required"
            properties["type"]["example"] = "value_error.missing"


class Error422Model(BaseModel):
    meta: Error422MetaModel
    detail: List[Error422DetailModel]


class Error503MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 1
            properties["title"]["example"] = "ServiceUnavailableError"


class Error503Model(BaseModel):
    meta: Error503MetaModel
    detail: str


DEFAULT_RESPONSE = {
    400: {
        "description": "Invalid Parameter Error / Send Transaction Error",
        "model": Error400Model
    },
    401: {
        "description": "Authorization Error",
        "model": Error401Model
    },
    404: {
        "description": "Not Found Error",
        "model": Error404Model
    },
    405: {
        "description": "Method Not Allowed",
        "model": Error405Model
    },
    422: {
        "description": "Validation Error",
        "model": Error422Model
    },
    503: {
        "description": "Service Unavailable Error",
        "model": Error503Model
    }
}


def get_routers_responses(*args):
    responses = {}
    for arg in args:
        if isinstance(arg, int):
            responses[arg] = DEFAULT_RESPONSE.get(arg, {})
        elif arg == InvalidParameterError:
            responses[400] = DEFAULT_RESPONSE[400]
        elif arg == SendTransactionError:
            responses[400] = DEFAULT_RESPONSE[400]
        elif arg == AuthorizationError:
            responses[401] = DEFAULT_RESPONSE[401]
        elif arg == RequestValidationError:
            responses[422] = DEFAULT_RESPONSE[422]
        elif arg == ServiceUnavailableError:
            responses[503] = DEFAULT_RESPONSE[503]

    return responses


def custom_openapi(app):
    def openapi():
        openapi_schema = app.openapi_schema
        if openapi_schema is None:
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                routes=app.routes,
                tags=app.openapi_tags,
                servers=app.servers,
            )

        def _get(src: dict, *keys):
            tmp_src = src
            for key in keys:
                tmp_src = tmp_src.get(key)
                if tmp_src is None:
                    return None
            return tmp_src

        # Remove Default Validation Error Response Structure
        # NOTE:
        # HTTPValidationError is automatically added to APIs docs that have path, header, query, and body parameters.
        # But HTTPValidationError does not have 'meta',
        # and some APIs do not generate a Validation Error(API with no-required string parameter only, etc).
        paths = _get(openapi_schema, "paths")
        if paths is not None:
            for path_info in paths.values():
                for router in path_info.values():
                    resp_422 = _get(router, "responses", "422")
                    if resp_422 is not None:
                        ref = _get(resp_422, "content", "application/json", "schema", "$ref")
                        if ref == "#/components/schemas/HTTPValidationError":
                            router["responses"].pop("422")

        return openapi_schema

    return openapi
