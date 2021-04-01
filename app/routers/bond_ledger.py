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
    Dict,
    Any
)

from fastapi import (
    APIRouter,
    Header,
    Query,
    Depends,
    Request,
    Body
)
from fastapi.exceptions import (
    HTTPException,
    RequestValidationError
)
from pydantic import BaseConfig
from pydantic.fields import ModelField
from sqlalchemy.orm import Session

from config import SYSTEM_LOCALE
from app.database import db_session
from app.model.utils import (
    headers_validate,
    address_is_valid_address
)
from app.model.db import (
    Token,
    TokenType,
    BondLedger
)
from app.model.schema import (
    ListAllBondLedgerHistoryResponse,
    CreateUpdateBondLedgerTemplateRequestJPN
)
from app.routers.localized import bond_ledger_JPN
from app.exceptions import InvalidParameterError

router = APIRouter(
    prefix="/bond_ledger",
    tags=["bond_ledger"],
    responses={404: {"description": "Not found"}},
)


# GET: /bond_ledger/{token_address}/history
# NOTE: Localized Function
@router.get("/{token_address}/history", response_model=ListAllBondLedgerHistoryResponse)
async def list_all_bond_ledger_history(
        token_address: str,
        issuer_address: str = Header(...),
        locale: str = Query(..., description="Supported: JPN"),
        offset: int = Query(None),
        limit: int = Query(None),
        db: Session = Depends(db_session)):
    """List all Bond Ledger"""

    # Validate Headers
    headers_validate(issuer_address=(issuer_address, address_is_valid_address))

    # Function Enabled Check
    locale_upper = locale.upper()
    if locale_upper not in SYSTEM_LOCALE:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # API Localized Supported Check
    if locale_upper == "JPN":
        pass
    else:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Localized
    resp = None
    if locale_upper == "JPN":
        resp = bond_ledger_JPN.list_all_bond_ledger_history(token_address, offset, limit, db)

    return resp


# GET: /bond_ledger/{token_address}/history/{ledger_id}
# NOTE: Localized Function
@router.get("/{token_address}/history/{ledger_id}", response_model=Dict[str, Any],
            response_description="Successful Response (structures differs depending on localize.)")
async def retrieve_bond_ledger_history(
        token_address: str,
        ledger_id: int,
        issuer_address: str = Header(...),
        locale: str = Query(..., description="Supported: JPN"),
        latest_flg: int = Query(..., ge=0, le=1),
        db: Session = Depends(db_session)):
    """Retrieve Bond Ledger"""

    # Validate Headers
    headers_validate(issuer_address=(issuer_address, address_is_valid_address))

    # Function Enabled Check
    locale_upper = locale.upper()
    if locale_upper not in SYSTEM_LOCALE:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # API Localized Supported Check
    if locale_upper == "JPN":
        pass
    else:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Ledger Exist Check
    _bond_ledger = db.query(BondLedger). \
        filter(BondLedger.id == ledger_id). \
        filter(BondLedger.token_address == token_address). \
        filter(BondLedger.country_code == locale_upper). \
        first()
    if _bond_ledger is None:
        raise InvalidParameterError("ledger does not exist")

    # Localized
    resp = None
    if locale_upper == "JPN":
        resp = bond_ledger_JPN.retrieve_bond_ledger_history(token_address, ledger_id, issuer_address, latest_flg, db)

    return resp


# GET: /bond_ledger/{token_address}/template
# NOTE: Localized Function
@router.get("/{token_address}/template", response_model=Dict[str, Any],
            response_description="Successful Response (structures differs depending on localize.)")
async def retrieve_bond_ledger_template(
        token_address: str,
        issuer_address: str = Header(...),
        locale: str = Query(..., description="Supported: JPN"),
        db: Session = Depends(db_session)):
    """Retrieve Bond Ledger Template"""

    # Validate Headers
    headers_validate(issuer_address=(issuer_address, address_is_valid_address))

    # Function Enabled Check
    locale_upper = locale.upper()
    if locale_upper not in SYSTEM_LOCALE:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # API Localized Supported Check
    if locale_upper == "JPN":
        pass
    else:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Localized
    resp = None
    if locale_upper == "JPN":
        resp = bond_ledger_JPN.retrieve_bond_ledger_template(token_address, issuer_address, db)

    return resp


# POST: /bond_ledger/{token_address}/template
# NOTE: Localized Function
@router.post("/{token_address}/template")
async def create_update_bond_ledger_template(
        request: Request,
        token_address: str,
        issuer_address: str = Header(...),
        locale: str = Query(..., description="Supported: JPN"),
        # NOTE: for Swagger(Request-body is able to input, when API execute.)
        template: dict = Body(..., description="structures differs depending on localize."),
        db: Session = Depends(db_session)):
    """Create or Update Bond Ledger Template"""

    # Validate Headers
    headers_validate(issuer_address=(issuer_address, address_is_valid_address))

    # Function Enabled Check
    locale_upper = locale.upper()
    if locale_upper not in SYSTEM_LOCALE:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # API Localized Supported Check
    if locale_upper == "JPN":
        _request_model = CreateUpdateBondLedgerTemplateRequestJPN
    else:
        raise HTTPException(status_code=404, detail=f"Not Supported locale:{locale}")

    # Request-body validation and mapping to model
    body = await request.json()
    validator = ModelField.infer(name="", value=..., annotation=_request_model,
                                 class_validators={}, config=BaseConfig)
    value, errors = validator.validate(body, {}, loc=("body",))
    if errors:
        raise RequestValidationError([errors])
    template = value

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Localized
    if locale_upper == "JPN":
        bond_ledger_JPN.create_update_bond_ledger_template(token_address, template, issuer_address, db)

    return
