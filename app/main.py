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
import os

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn.workers import UvicornWorker

from config import SERVER_NAME
from app.routers import account, bond, share
from app.database import engine
from app.model import db
from app.exceptions import *

# Create Database
db.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ibet Prime",
    version="0.0.1"
)


# gunicorn loading worker
class AppUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "loop": "asyncio",
        "http": "h11",
        # NOTE: gunicorn don't support '--worker-connections' to uvicorn
        "limit_concurrency": int(os.environ.get('WORKER_CONNECTIONS')) if os.environ.get('WORKER_CONNECTIONS') else 100
    }


###############################################################
# ROUTER
###############################################################

@app.get("/")
async def root():
    return {"server": SERVER_NAME}


app.include_router(account.router)
app.include_router(bond.router)
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
async def invalid_parameter_error_handler(request: Request, exc: SendTransactionError):
    meta = {
        "code": 2,
        "title": "SendTransactionError"
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
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
