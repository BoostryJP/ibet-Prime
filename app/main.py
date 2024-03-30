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

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pydantic_core import ArgsKwargs, ErrorDetails
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import *
from app.log import output_access_log
from app.routers import (
    account,
    bc_explorer,
    bond,
    common,
    e2e_messaging,
    file,
    freeze_log,
    ledger,
    notification,
    position,
    share,
    token_holders,
)
from app.utils.docs_utils import custom_openapi
from config import SERVER_NAME

tags_metadata = [
    {"name": "root", "description": ""},
    {"name": "common", "description": "Common functions"},
    {"name": "account", "description": "Issuer account management"},
    {"name": "notification", "description": "Notifications for accounts"},
    {"name": "token_common", "description": "Common functions for tokens"},
    {"name": "bond", "description": "Bond token management"},
    {"name": "share", "description": "Share token management"},
    {"name": "utility", "description": "Utility functions"},
    {"name": "messaging", "description": "Messaging functions with external systems"},
    {"name": "blockchain_explorer", "description": "Blockchain explorer"},
]

app = FastAPI(
    title="ibet Prime",
    description="Security token management system for ibet network",
    version="24.6.0",
    contact={"email": "dev@boostry.co.jp"},
    license_info={
        "name": "Apache 2.0",
        "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=tags_metadata,
)


@app.middleware("http")
async def api_call_handler(request: Request, call_next):
    request_start_time = datetime.utcnow()
    response = await call_next(request)
    output_access_log(request, response, request_start_time)
    return response


app.openapi = custom_openapi(app)


###############################################################
# ROUTER
###############################################################


@app.get("/", tags=["root"])
async def root():
    return {"server": SERVER_NAME}


app.include_router(common.router)
app.include_router(account.router)
app.include_router(bond.router)
app.include_router(e2e_messaging.router)
app.include_router(file.router)
app.include_router(ledger.router)
app.include_router(notification.router)
app.include_router(position.router)
app.include_router(share.router)
app.include_router(token_holders.router)
app.include_router(bc_explorer.router)
app.include_router(freeze_log.router)


###############################################################
# EXCEPTION
###############################################################


# 500:InternalServerError
@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    meta = {"code": 1, "title": "InternalServerError"}
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({"meta": meta}),
    )


def convert_errors(
    e: ValidationError | RequestValidationError,
) -> list[ErrorDetails]:
    new_errors: list[ErrorDetails] = []
    for error in e.errors():
        # "url" field which Pydantic V2 adds when validation error occurs is not needed for API response.
        # https://docs.pydantic.dev/2.1/errors/errors/
        if "url" in error.keys():
            error.pop("url", None)

        # "input" field generated from GET query model_validator is ArgsKwargs instance.
        # This cannot be serialized to json as it is, so nested field should be picked.
        # https://docs.pydantic.dev/2.1/errors/errors/
        if "input" in error.keys() and isinstance(error["input"], ArgsKwargs):
            error["input"] = error["input"].kwargs
        new_errors.append(error)
    return new_errors


# 422:RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    meta = {"code": 1, "title": "RequestValidationError"}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"meta": meta, "detail": convert_errors(exc)}),
    )


# 422:ValidationError
# NOTE: for exceptions raised directly from Pydantic validation
@app.exception_handler(ValidationError)
async def query_validation_exception_handler(request: Request, exc: ValidationError):
    meta = {"code": 1, "title": "RequestValidationError"}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"meta": meta, "detail": convert_errors(exc)}),
    )


# 400:InvalidParameterError
@app.exception_handler(InvalidParameterError)
async def invalid_parameter_error_handler(request: Request, exc: InvalidParameterError):
    meta = {"code": 1, "title": "InvalidParameterError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 400:SendTransactionError
@app.exception_handler(SendTransactionError)
async def send_transaction_error_handler(request: Request, exc: SendTransactionError):
    meta = {"code": 2, "title": "SendTransactionError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 400:AuthTokenAlreadyExistsError
@app.exception_handler(AuthTokenAlreadyExistsError)
async def auth_token_already_exists_error_handler(
    request: Request, exc: AuthTokenAlreadyExistsError
):
    meta = {"code": 3, "title": "AuthTokenAlreadyExistsError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta}),
    )


# 400:ResponseLimitExceededError
@app.exception_handler(ResponseLimitExceededError)
async def response_limit_exceeded_error_handler(
    request: Request, exc: ResponseLimitExceededError
):
    meta = {"code": 4, "title": "ResponseLimitExceededError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 400:ResponseLimitExceededError
@app.exception_handler(Integer64bitLimitExceededError)
async def response_limit_exceeded_error_handler(
    request: Request, exc: Integer64bitLimitExceededError
):
    meta = {"code": 5, "title": "Integer64bitLimitExceededError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 400:OperationNotAllowedStateError
@app.exception_handler(OperationNotAllowedStateError)
async def operation_not_permitted_error_handler(
    request: Request, exc: OperationNotAllowedStateError
):
    meta = {"code": exc.code, "title": "OperationNotAllowedStateError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 400:ContractRevertError
@app.exception_handler(ContractRevertError)
async def contract_revert_error_handler(request: Request, exc: ContractRevertError):
    meta = {"code": exc.code, "title": "ContractRevertError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.message}),
    )


# 401:AuthorizationError
@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    meta = {"code": 1, "title": "AuthorizationError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 404:NotFound
@app.exception_handler(404)
async def not_found_error_handler(request: Request, exc: StarletteHTTPException):
    meta = {"code": 1, "title": "NotFound"}
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta, "detail": exc.detail}),
    )


# 405:MethodNotAllowed
@app.exception_handler(405)
async def method_not_allowed_error_handler(
    request: Request, exc: StarletteHTTPException
):
    meta = {"code": 1, "title": "MethodNotAllowed"}
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content=jsonable_encoder({"meta": meta}),
    )


# 503:ServiceUnavailable
@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_error_handler(
    request: Request, exc: ServiceUnavailableError
):
    meta = {"code": 1, "title": "ServiceUnavailableError"}
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )
