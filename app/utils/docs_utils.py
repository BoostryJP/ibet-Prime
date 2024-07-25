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

from enum import Enum
from functools import lru_cache
from typing import List, Type, Union

from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, create_model

from app.exceptions import AppError


class MetaModel(BaseModel):
    code: int
    title: str


class Error400MetaModel(MetaModel):
    code: int = Field(..., examples=[0, 1, 2, 100001])
    title: str = Field(
        ...,
        examples=[
            "InvalidParameterError",
            "SendTransactionError",
            "ContractRevertError",
        ],
    )


class Error400Model(BaseModel):
    meta: Error400MetaModel
    detail: str = Field(
        ...,
        examples=[
            "this token is temporarily unavailable",
            "failed to register token address token list",
            "The address has already been registered.",
        ],
    )


class Error401MetaModel(MetaModel):
    code: int = Field(..., examples=[1])
    title: str = Field(..., examples=["AuthorizationError"])


class Error401Model(BaseModel):
    meta: Error401MetaModel
    detail: str


class Error404MetaModel(MetaModel):
    code: int = Field(..., examples=[1])
    title: str = Field(..., examples=["NotFound"])


class Error404Model(BaseModel):
    meta: Error404MetaModel
    detail: str


class Error405MetaModel(MetaModel):
    code: int = Field(..., examples=[1])
    title: str = Field(..., examples=["MethodNotAllowed"])


class Error405Model(BaseModel):
    meta: Error405MetaModel
    detail: str


class Error422MetaModel(MetaModel):
    code: int = Field(..., examples=[1])
    title: str = Field(..., examples=["RequestValidationError"])


class Error422DetailModel(BaseModel):
    loc: List[str] = Field(..., examples=[["header", "issuer-address"]])
    msg: str = Field(..., examples=["field required"])
    type: str = Field(..., examples=["value_error.missing"])


class Error422Model(BaseModel):
    meta: Error422MetaModel
    detail: List[Error422DetailModel]


class Error503MetaModel(MetaModel):
    code: int = Field(..., examples=[1])
    title: str = Field(..., examples=["ServiceUnavailableError"])


class Error503Model(BaseModel):
    meta: Error503MetaModel
    detail: str


DEFAULT_RESPONSE: dict[int, dict[str, str | BaseModel]] = {
    400: {
        "description": "Invalid Parameter Error / Send Transaction Error / Contract Revert Error etc",
        "model": Error400Model,
    },
    401: {"description": "Authorization Error", "model": Error401Model},
    404: {"description": "Not Found Error", "model": Error404Model},
    405: {"description": "Method Not Allowed", "model": Error405Model},
    422: {"description": "Validation Error", "model": Error422Model},
    503: {"description": "Service Unavailable Error", "model": Error503Model},
}


@lru_cache(None)
def create_error_model(app_error: Type[AppError]):
    """
    This function creates Pydantic Model from AppError.
    * create_model() generates a different model each time when called,
      so cache is enabled.

    @param app_error: AppError defined in ibet-Prime
    @return: pydantic Model created dynamically
    """
    base_name = app_error.__name__
    error_code_enum = (
        Enum(f"{base_name}Code", {f"{app_error.code}": app_error.code})
        if app_error.code is not None
        else Enum(f"{base_name}Code", {f"{code}": code for code in app_error.code_list})
    )
    metainfo_model = create_model(
        f"{base_name}Metainfo",
        code=(
            error_code_enum,
            Field(..., examples=[app_error.code] if app_error.code else [0]),
        ),
        title=(str, Field(..., examples=[base_name])),
    )
    error_model = create_model(
        f"{base_name}Response",
        meta=(
            metainfo_model,
            Field(
                ...,
            ),
        ),
        detail=(str, Field()),
    )
    error_model.__doc__ = app_error.__doc__
    return error_model


def get_routers_responses(*args: Type[AppError] | int):
    """
    This function returns responses dictionary to be used for openapi document.
    Supposed to be used in router decorator.

    @param args: tuple of AppError
    @return: responses dict
    """
    responses_per_status_code: dict[int, list[BaseModel]] = {}
    for arg in args:
        if not isinstance(arg, int):
            responses_per_status_code.setdefault(arg.status_code, [])
            responses_per_status_code[arg.status_code].append(create_error_model(arg))
        else:
            responses_per_status_code.setdefault(arg, [])
            error_model = DEFAULT_RESPONSE.get(arg)["model"]
            responses_per_status_code[arg].append(error_model)

    responses: dict[int, dict] = {}
    for status_code, error_models in responses_per_status_code.items():
        if len(error_models) > 0:
            responses[status_code] = {
                "model": Union[tuple(set(error_models))],
                "description": DEFAULT_RESPONSE.get(status_code)["description"],
            }

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

        paths = _get(openapi_schema, "paths")
        if paths is not None:
            for path_info in paths.values():
                for router in path_info.values():
                    # Remove Default Validation Error Response Structure
                    # NOTE:
                    # HTTPValidationError is automatically added to APIs docs that have path, header, query,
                    # and body parameters.
                    # But HTTPValidationError does not have 'meta',
                    # and some APIs do not generate a Validation Error(API with no-required string parameter only, etc).
                    resp_422 = _get(router, "responses", "422")
                    if resp_422 is not None:
                        ref = _get(
                            resp_422, "content", "application/json", "schema", "$ref"
                        )
                        if ref == "#/components/schemas/HTTPValidationError":
                            router["responses"].pop("422")

                    # Remove empty response's contents
                    responses = _get(router, "responses")
                    for resp in responses.values():
                        schema = _get(resp, "content", "application/json", "schema")
                        if schema == {}:
                            resp.pop("content")
                        any_of: list | None = _get(schema, "anyOf")
                        if any_of is not None:
                            schema["anyOf"] = sorted(any_of, key=lambda x: x["$ref"])

        return openapi_schema

    return openapi
