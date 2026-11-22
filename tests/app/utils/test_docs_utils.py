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

from typing import get_args

import pytest
from pydantic import TypeAdapter, ValidationError

from app.exceptions import AppError, AuthorizationError, InvalidParameterError
from app.main import PrimeAPI
from app.utils.docs_utils import (
    Error404Model,
    create_error_model,
    get_routers_responses,
)


class ZeroCodeError(AppError):
    status_code = 400
    code = 0


class MultipleCodesError(AppError):
    status_code = 400
    code_list = [2, 3]


@pytest.mark.parametrize(
    ("error", "codes"),
    [(InvalidParameterError, [1]), (ZeroCodeError, [0]), (MultipleCodesError, [2, 3])],
)
def test_generated_error_model_validates_declared_codes(
    error: type[AppError], codes: list[int]
) -> None:
    model = create_error_model(error)
    for code in codes:
        payload = {"meta": {"code": code, "title": error.__name__}, "detail": "error"}
        assert model.model_validate(payload).model_dump(mode="json") == payload

    with pytest.raises(ValidationError):
        model.model_validate(
            {"meta": {"code": 999, "title": error.__name__}, "detail": "error"}
        )

    schema = model.model_json_schema()
    assert schema["$defs"][f"{error.__name__}Code"]["enum"] == codes
    assert create_error_model(error) is model


def test_error_model_requires_a_code_or_code_list() -> None:
    with pytest.raises(ValueError, match="either 'code' or 'code_list'"):
        create_error_model(AppError)


def test_response_models_group_by_status_and_deduplicate() -> None:
    responses = get_routers_responses(
        InvalidParameterError,
        MultipleCodesError,
        InvalidParameterError,
        AuthorizationError,
    )
    assert responses is not None
    assert set(responses) == {400, 401}
    assert set(get_args(responses[400]["model"])) == {
        create_error_model(InvalidParameterError),
        create_error_model(MultipleCodesError),
    }
    assert responses[401]["model"] is create_error_model(AuthorizationError)

    adapter = TypeAdapter(responses[400]["model"])
    for code, title in [(1, "InvalidParameterError"), (2, "MultipleCodesError")]:
        payload = {"meta": {"code": code, "title": title}, "detail": "error"}
        assert adapter.validate_python(payload).model_dump(mode="json") == payload


def test_default_response_model_and_unknown_status() -> None:
    responses = get_routers_responses(404, 599)
    assert responses is not None
    assert set(responses) == {404}
    assert responses[404]["model"] is Error404Model


def test_custom_openapi_filters_ui_and_preserves_error_schemas() -> None:
    app = PrimeAPI(title="Schema test")

    @app.get(
        "/visible/{item_id}", responses=get_routers_responses(InvalidParameterError)
    )
    def visible(item_id: int) -> dict[str, int]:
        return {"id": item_id}

    @app.get("/blockchain_explorer/ui")
    def ui() -> dict[str, str]:
        return {"page": "explorer"}

    schema = app.openapi()
    paths = schema["paths"]
    assert isinstance(paths, dict)
    assert "/blockchain_explorer/ui" not in paths
    responses = paths["/visible/{item_id}"]["get"]["responses"]
    assert "422" not in responses
    assert responses["400"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/InvalidParameterErrorResponse"
    }
