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
from fastapi import (
    FastAPI,
    Request,
    status
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import SERVER_NAME
from app.routers import (
    index,
    account,
    bond,
    e2e_messaging,
    file,
    ledger,
    notification,
    position,
    share
)
from app.utils.docs_utils import custom_openapi
from app.exceptions import *
from app.log import output_access_log

app = FastAPI(
    title="ibet Prime",
    version="22.3.0"
)


@app.middleware("http")
async def api_call_handler(request: Request, call_next):
    response = await call_next(request)
    output_access_log(request, response)
    return response


app.openapi = custom_openapi(app)


###############################################################
# ROUTER
###############################################################

@app.get("/")
async def root():
    return {"server": SERVER_NAME}


app.include_router(index.router)
app.include_router(account.router)
app.include_router(bond.router)
app.include_router(e2e_messaging.router)
app.include_router(file.router)
app.include_router(ledger.router)
app.include_router(notification.router)
app.include_router(position.router)
app.include_router(share.router)


###############################################################
# EXCEPTION
###############################################################

# 500:InternalServerError
@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    meta = {
        "code": 1,
        "title": "InternalServerError"
    }
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({"meta": meta}),
    )


# 422:RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    meta = {
        "code": 1,
        "title": "RequestValidationError"
    }
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"meta": meta, "detail": exc.errors()}),
    )


# 400:InvalidParameterError
@app.exception_handler(InvalidParameterError)
async def invalid_parameter_error_handler(request: Request, exc: InvalidParameterError):
    meta = {
        "code": 1,
        "title": "InvalidParameterError"
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 400:SendTransactionError
@app.exception_handler(SendTransactionError)
async def send_transaction_error_handler(request: Request, exc: SendTransactionError):
    meta = {
        "code": 2,
        "title": "SendTransactionError"
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 401:AuthorizationError
@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    meta = {
        "code": 1,
        "title": "AuthorizationError"
    }
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )


# 404:NotFound
@app.exception_handler(404)
async def not_found_error_handler(request: Request, exc: StarletteHTTPException):
    meta = {
        "code": 1,
        "title": "NotFound"
    }
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta, "detail": exc.detail}),
    )


# 405:MethodNotAllowed
@app.exception_handler(405)
async def method_not_allowed_error_handler(request: Request, exc: StarletteHTTPException):
    meta = {
        "code": 1,
        "title": "MethodNotAllowed"
    }
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content=jsonable_encoder({"meta": meta}),
    )


# 503:ServiceUnavailable
@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_error_handler(request: Request, exc: ServiceUnavailableError):
    meta = {
        "code": 1,
        "title": "ServiceUnavailableError"
    }
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=jsonable_encoder({"meta": meta, "detail": exc.args[0]}),
    )
