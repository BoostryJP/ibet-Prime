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

from eth_keyfile import decode_keyfile_json
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.exceptions import HTTPException
from pytz import timezone
from sqlalchemy import String, and_, column, desc, func, literal, null, or_

from app.database import DBSession
from app.exceptions import (
    AuthorizationError,
    ContractRevertError,
    InvalidParameterError,
    SendTransactionError,
)
from app.model.blockchain import (
    IbetSecurityTokenInterface,
    IbetShareContract,
    IbetStraightBondContract,
)
from app.model.blockchain.tx_params.ibet_security_token import ForceUnlockParams
from app.model.db import (
    IDXLock,
    IDXLockedPosition,
    IDXPosition,
    IDXUnlock,
    Token,
    TokenType,
)
from app.model.schema import (
    ForceUnlockRequest,
    ListAllLockedPositionResponse,
    ListAllLockEventsQuery,
    ListAllLockEventsResponse,
    ListAllLockEventsSortItem,
    ListAllPositionResponse,
    LockEventCategory,
    PositionResponse,
)
from app.utils.check_utils import (
    address_is_valid_address,
    check_auth,
    eoa_password_is_encrypted_value,
    validate_headers,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi import json_response
from config import TZ

router = APIRouter(prefix="/positions", tags=["token_common"])

local_tz = timezone(TZ)


# GET: /positions/{account_address}
@router.get(
    "/{account_address}",
    summary="List all positions in the account",
    response_model=ListAllPositionResponse,
    responses=get_routers_responses(422),
)
def list_all_position(
    db: DBSession,
    account_address: str,
    issuer_address: Optional[str] = Header(None),
    include_former_position: bool = False,
    token_type: Optional[TokenType] = Query(None),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
):
    """List all account's position"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get a list of positions
    query = (
        db.query(IDXPosition, func.sum(IDXLockedPosition.value), Token)
        .join(Token, IDXPosition.token_address == Token.token_address)
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == IDXPosition.token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .filter(IDXPosition.account_address == account_address)
        .filter(Token.token_status != 2)
        .group_by(
            IDXPosition.id,
            Token.id,
            IDXLockedPosition.token_address,
            IDXLockedPosition.account_address,
        )
    )

    if not include_former_position:
        query = query.filter(
            or_(
                IDXPosition.balance != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0,
            )
        )

    query = query.order_by(IDXPosition.token_address, IDXPosition.account_address)

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
    for _position, _locked, _token in _position_list:
        # Get Token Name
        token_name = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
            _bond = IbetStraightBondContract(_token.token_address).get()
            token_name = _bond.name
        elif _token.type == TokenType.IBET_SHARE.value:
            _share = IbetShareContract(_token.token_address).get()
            token_name = _share.name
        positions.append(
            {
                "issuer_address": _token.issuer_address,
                "token_address": _token.token_address,
                "token_type": _token.type,
                "token_name": token_name,
                "balance": _position.balance,
                "exchange_balance": _position.exchange_balance,
                "exchange_commitment": _position.exchange_commitment,
                "pending_transfer": _position.pending_transfer,
                "locked": _locked if _locked is not None else 0,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "positions": positions,
    }

    return json_response(resp)


# GET: /positions/{account_address}/lock
@router.get(
    "/{account_address}/lock",
    summary="List all locked positions in the account",
    response_model=ListAllLockedPositionResponse,
    responses=get_routers_responses(422),
)
def list_all_locked_position(
    db: DBSession,
    account_address: str,
    issuer_address: Optional[str] = Header(None),
    token_type: Optional[TokenType] = Query(None),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
):
    """List all account's locked position"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get a list of locked positions
    query = (
        db.query(IDXLockedPosition, Token)
        .join(Token, IDXLockedPosition.token_address == Token.token_address)
        .filter(IDXLockedPosition.account_address == account_address)
        .filter(IDXLockedPosition.value > 0)
        .filter(Token.token_status != 2)
        .order_by(IDXLockedPosition.token_address)
    )

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
    for _locked_position, _token in _position_list:
        # Get Token Name
        token_name = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
            _bond = IbetStraightBondContract(_token.token_address).get()
            token_name = _bond.name
        elif _token.type == TokenType.IBET_SHARE.value:
            _share = IbetShareContract(_token.token_address).get()
            token_name = _share.name
        positions.append(
            {
                "issuer_address": _token.issuer_address,
                "token_address": _token.token_address,
                "token_type": _token.type,
                "token_name": token_name,
                "lock_address": _locked_position.lock_address,
                "locked": _locked_position.value,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "locked_positions": positions,
    }
    return json_response(resp)


# GET: /positions/{account_address}/lock/events
@router.get(
    "/{account_address}/lock/events",
    summary="List all lock/unlock events in the account",
    response_model=ListAllLockEventsResponse,
    responses=get_routers_responses(422),
)
def list_all_lock_events(
    db: DBSession,
    account_address: str,
    issuer_address: Optional[str] = Header(None),
    request_query: ListAllLockEventsQuery = Depends(),
):
    """List all lock/unlock events in the account"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Request parameters
    offset = request_query.offset
    limit = request_query.limit
    sort_item = request_query.sort_item
    sort_order = request_query.sort_order

    # Base query
    query_lock = (
        db.query(
            literal(value=LockEventCategory.Lock.value, type_=String).label("category"),
            IDXLock.transaction_hash.label("transaction_hash"),
            IDXLock.msg_sender.label("msg_sender"),
            IDXLock.token_address.label("token_address"),
            IDXLock.lock_address.label("lock_address"),
            IDXLock.account_address.label("account_address"),
            null().label("recipient_address"),
            IDXLock.value.label("value"),
            IDXLock.data.label("data"),
            IDXLock.block_timestamp.label("block_timestamp"),
            Token,
        )
        .join(Token, IDXLock.token_address == Token.token_address)
        .filter(column("account_address") == account_address)
        .filter(Token.token_status != 2)
    )
    if issuer_address is not None:
        query_lock = query_lock.filter(Token.issuer_address == issuer_address)

    query_unlock = (
        db.query(
            literal(value=LockEventCategory.Unlock.value, type_=String).label(
                "category"
            ),
            IDXUnlock.transaction_hash.label("transaction_hash"),
            IDXUnlock.msg_sender.label("msg_sender"),
            IDXUnlock.token_address.label("token_address"),
            IDXUnlock.lock_address.label("lock_address"),
            IDXUnlock.account_address.label("account_address"),
            IDXUnlock.recipient_address.label("recipient_address"),
            IDXUnlock.value.label("value"),
            IDXUnlock.data.label("data"),
            IDXUnlock.block_timestamp.label("block_timestamp"),
            Token,
        )
        .join(Token, IDXUnlock.token_address == Token.token_address)
        .filter(column("account_address") == account_address)
        .filter(Token.token_status != 2)
    )
    if issuer_address is not None:
        query_unlock = query_unlock.filter(Token.issuer_address == issuer_address)

    total = query_lock.count() + query_unlock.count()

    # Filter
    match request_query.category:
        case LockEventCategory.Lock.value:
            query = query_lock
        case LockEventCategory.Unlock.value:
            query = query_unlock
        case _:
            query = query_lock.union_all(query_unlock)

    query = query.filter(column("account_address") == account_address)

    if request_query.token_address is not None:
        query = query.filter(column("token_address") == request_query.token_address)
    if request_query.token_type is not None:
        query = query.filter(Token.type == request_query.token_type.value)
    if request_query.msg_sender is not None:
        query = query.filter(column("msg_sender") == request_query.msg_sender)
    if request_query.lock_address is not None:
        query = query.filter(column("lock_address") == request_query.lock_address)
    if request_query.recipient_address is not None:
        query = query.filter(
            column("recipient_address") == request_query.recipient_address
        )

    count = query.count()

    # Sort
    sort_attr = column(sort_item)
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))

    if sort_item != ListAllLockEventsSortItem.block_timestamp.value:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(
            desc(column(ListAllLockEventsSortItem.block_timestamp.value))
        )

    # Pagination
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    lock_events = query.all()

    resp_data = []
    for lock_event in lock_events:
        token_name = None
        _token = lock_event[10]
        if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
            _bond = IbetStraightBondContract(_token.token_address).get()
            token_name = _bond.name
        elif _token.type == TokenType.IBET_SHARE.value:
            _share = IbetShareContract(_token.token_address).get()
            token_name = _share.name

        block_timestamp_utc = timezone("UTC").localize(lock_event[9])
        resp_data.append(
            {
                "category": lock_event[0],
                "transaction_hash": lock_event[1],
                "msg_sender": lock_event[2],
                "issuer_address": _token.issuer_address,
                "token_address": lock_event[3],
                "token_type": _token.type,
                "token_name": token_name,
                "lock_address": lock_event[4],
                "account_address": lock_event[5],
                "recipient_address": lock_event[6],
                "value": lock_event[7],
                "data": lock_event[8],
                "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat(),
            }
        )

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "events": resp_data,
    }
    return json_response(data)


@router.post(
    "/{account_address}/force_unlock",
    summary="Force unlock the locked position",
    response_model=None,
    responses=get_routers_responses(
        401,
        422,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
    ),
)
def force_unlock(
    db: DBSession,
    request: Request,
    data: ForceUnlockRequest,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Force unlock the locked position"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Verify that the token is issued by the issuer_address
    _token = (
        db.query(Token)
        .filter(Token.issuer_address == issuer_address)
        .filter(Token.token_address == data.token_address)
        .filter(Token.token_status != 2)
        .first()
    )
    if _token is None:
        raise InvalidParameterError("token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Force unlock
    unlock_data = {
        "lock_address": data.lock_address,
        "account_address": data.account_address,
        "recipient_address": data.recipient_address,
        "value": data.value,
        "data": "",
    }
    try:
        IbetSecurityTokenInterface(data.token_address).force_unlock(
            data=ForceUnlockParams(**unlock_data),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except ContractRevertError:
        raise
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /positions/{account_address}/{token_address}
@router.get(
    "/{account_address}/{token_address}",
    summary="Token position in the account",
    response_model=PositionResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
def retrieve_position(
    db: DBSession,
    account_address: str,
    token_address: str,
    issuer_address: Optional[str] = Header(None),
):
    """Retrieve account's position"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token
    query = (
        db.query(Token)
        .filter(Token.token_address == token_address)
        .filter(Token.token_status != 2)
    )
    if issuer_address is not None:
        query = query.filter(Token.issuer_address == issuer_address)
    _token = query.first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Position
    _record = (
        db.query(IDXPosition, func.sum(IDXLockedPosition.value))
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == IDXPosition.token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .filter(IDXPosition.token_address == token_address)
        .filter(IDXPosition.account_address == account_address)
        .group_by(
            IDXPosition.id,
            IDXLockedPosition.token_address,
            IDXLockedPosition.account_address,
        )
        .first()
    )

    if _record is not None:
        _position = _record[0]
        _locked = _record[1]
    else:
        _position = None
        _locked = None

    if _position is None:
        # If there is no position, set default value(0) to each balance.
        _position = IDXPosition(
            balance=0, exchange_balance=0, exchange_commitment=0, pending_transfer=0
        )

    # Get Token Name
    token_name = None
    if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
        _bond = IbetStraightBondContract(_token.token_address).get()
        token_name = _bond.name
    elif _token.type == TokenType.IBET_SHARE.value:
        _share = IbetShareContract(_token.token_address).get()
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
        "locked": _locked if _locked is not None else 0,
    }

    return json_response(resp)
