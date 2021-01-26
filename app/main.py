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

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import SERVER_NAME
from app.routers import account, bond
from app.database import engine
from app.model import db

db.Base.metadata.create_all(bind=engine)

app = FastAPI()


###############################################################
# ROUTER
###############################################################

@app.get("/")
async def root():
    return {"server": SERVER_NAME}


app.include_router(account.router)
app.include_router(bond.router)


###############################################################
# EXCEPTION
###############################################################

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


# 404: NotFound
@app.exception_handler(404)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    meta = {
        "code": 1,
        "title": "NotFound"
    }
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta}),
    )


# 405: MethodNotAllowed
@app.exception_handler(405)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    meta = {
        "code": 1,
        "title": "MethodNotAllowed"
    }
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content=jsonable_encoder({"meta": meta}),
    )
