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
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query
)
from fastapi.exceptions import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import db_session
from app.model.schema import (
    PositionResponse,
    ListAllPositionResponse
)
from app.utils.docs_utils import get_routers_responses
from app.utils.check_utils import (
    validate_headers,
    address_is_valid_address
)
from app.model.db import (
    IDXPosition,
    Token,
    TokenType
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract
)
from app.exceptions import InvalidParameterError
from app import log

LOG = log.get_logger()

router = APIRouter(tags=["position"])


# GET: /positions/{account_address}
@router.get(
    "/positions/{account_address}",
    response_model=ListAllPositionResponse,
    responses=get_routers_responses(422)
)
def list_all_position(
        account_address: str,
        issuer_address: Optional[str] = Header(None),
        token_type: Optional[TokenType] = Query(None),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)):
    """List all account's position"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get a list of positions
    query = db.query(IDXPosition, Token). \
        join(Token, IDXPosition.token_address == Token.token_address). \
        filter(IDXPosition.account_address == account_address). \
        filter(Token.token_status != 2). \
        filter(or_(
            IDXPosition.balance != 0,
            IDXPosition.exchange_balance != 0,
            IDXPosition.pending_transfer != 0,
            IDXPosition.exchange_commitment != 0
        )). \
        order_by(IDXPosition.token_address, IDXPosition.account_address)
    if issuer_address is not None:
        query = query.filter(Token.issuer_address == issuer_address)
    total = query.count()

    # Search Filter
    if token_type is not None:
        query = query.filter(Token.type == token_type.value)
    count = query.count()

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _position_list = query.all()

    positions = []
    for _position, _token in _position_list:
        # Get Token Name
        token_name = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
            _bond = IbetStraightBondContract.get(contract_address=_token.token_address)
            token_name = _bond.name
        elif _token.type == TokenType.IBET_SHARE.value:
            _share = IbetShareContract.get(contract_address=_token.token_address)
            token_name = _share.name
        positions.append({
            "issuer_address": _token.issuer_address,
            "token_address": _token.token_address,
            "token_type": _token.type,
            "token_name": token_name,
            "balance": _position.balance,
            "exchange_balance": _position.exchange_balance,
            "exchange_commitment": _position.exchange_commitment,
            "pending_transfer": _position.pending_transfer,
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "positions": positions
    }

    return resp


# GET: /positions/{account_address}/{token_address}
@router.get(
    "/positions/{account_address}/{token_address}",
    response_model=PositionResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404)
)
def retrieve_position(
        account_address: str,
        token_address: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve account's position"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token
    query = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2)
    if issuer_address is not None:
        query = query.filter(Token.issuer_address == issuer_address)
    _token = query.first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Position
    _position = db.query(IDXPosition). \
        filter(IDXPosition.token_address == token_address). \
        filter(IDXPosition.account_address == account_address). \
        first()
    if _position is None:
        # If there is no position, set default value(0) to each balance.
        _position = IDXPosition(balance=0, exchange_balance=0, exchange_commitment=0, pending_transfer=0)

    # Get Token Name
    token_name = None
    if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
        _bond = IbetStraightBondContract.get(contract_address=_token.token_address)
        token_name = _bond.name
    elif _token.type == TokenType.IBET_SHARE.value:
        _share = IbetShareContract.get(contract_address=_token.token_address)
        token_name = _share.name

    resp = {
        "issuer_address": _token.issuer_address,
        "token_address": _token.token_address,
        "token_type": _token.type,
        "token_name": token_name,
        "balance": _position.balance,
        "exchange_balance": _position.exchange_balance,
        "exchange_commitment": _position.exchange_commitment,
        "pending_transfer": _position.pending_transfer,
    }

    return resp
