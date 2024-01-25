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
from typing import Optional, Sequence

from eth_keyfile import decode_keyfile_json
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.exceptions import HTTPException
from pytz import timezone
from sqlalchemy import String, and_, column, desc, func, literal, null, or_, select
from sqlalchemy.orm import aliased
from web3 import Web3

from app.database import DBAsyncSession
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
from app.utils.fastapi_utils import json_response
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
async def list_all_position(
    db: DBAsyncSession,
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
    stmt = (
        select(IDXPosition, func.sum(IDXLockedPosition.value), Token)
        .join(Token, IDXPosition.token_address == Token.token_address)
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == IDXPosition.token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .where(
            and_(
                IDXPosition.account_address == account_address, Token.token_status != 2
            )
        )
        .group_by(
            IDXPosition.id,
            Token.id,
            IDXLockedPosition.token_address,
            IDXLockedPosition.account_address,
        )
    )

    if not include_former_position:
        stmt = stmt.where(
            or_(
                IDXPosition.balance != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0,
            )
        )

    stmt = stmt.order_by(IDXPosition.token_address, IDXPosition.account_address)

    if issuer_address is not None:
        stmt = stmt.where(Token.issuer_address == issuer_address)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if token_type is not None:
        stmt = stmt.where(Token.type == token_type.value)

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _position_list: Sequence[tuple[IDXPosition, int, Token]] = (
        (await db.execute(stmt)).tuples().all()
    )

    positions = []
    for _position, _locked, _token in _position_list:
        # Get Token Name
        token_name = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
            _bond = await IbetStraightBondContract(_token.token_address).get()
            token_name = _bond.name
        elif _token.type == TokenType.IBET_SHARE.value:
            _share = await IbetShareContract(_token.token_address).get()
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
async def list_all_locked_position(
    db: DBAsyncSession,
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
    stmt = (
        select(IDXLockedPosition, Token)
        .join(Token, IDXLockedPosition.token_address == Token.token_address)
        .where(
            and_(
                IDXLockedPosition.account_address == account_address,
                IDXLockedPosition.value > 0,
                Token.token_status != 2,
            )
        )
        .order_by(IDXLockedPosition.token_address)
    )

    if issuer_address is not None:
        stmt = stmt.where(Token.issuer_address == issuer_address)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if token_type is not None:
        stmt = stmt.where(Token.type == token_type.value)

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _position_list: Sequence[tuple[IDXLockedPosition, Token]] = (
        (await db.execute(stmt)).tuples().all()
    )

    positions = []
    for _locked_position, _token in _position_list:
        # Get Token Name
        token_name = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
            _bond = await IbetStraightBondContract(_token.token_address).get()
            token_name = _bond.name
        elif _token.type == TokenType.IBET_SHARE.value:
            _share = await IbetShareContract(_token.token_address).get()
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
async def list_all_lock_events(
    db: DBAsyncSession,
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
    stmt_lock = (
        select(
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
        .where(
            and_(column("account_address") == account_address, Token.token_status != 2)
        )
    )
    if issuer_address is not None:
        stmt_lock = stmt_lock.where(Token.issuer_address == issuer_address)

    stmt_unlock = (
        select(
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
        .where(
            and_(column("account_address") == account_address, Token.token_status != 2)
        )
    )
    if issuer_address is not None:
        stmt_unlock = stmt_unlock.where(Token.issuer_address == issuer_address)

    total = (
        await db.scalar(select(func.count()).select_from(stmt_lock.subquery()))
    ) + (await db.scalar(select(func.count()).select_from(stmt_unlock.subquery())))

    # Filter
    match request_query.category:
        case LockEventCategory.Lock.value:
            all_lock_event_alias = aliased(stmt_lock.subquery("all_lock_event"))
        case LockEventCategory.Unlock.value:
            all_lock_event_alias = aliased(stmt_unlock.subquery("all_lock_event"))
        case _:
            all_lock_event_alias = aliased(
                stmt_lock.union_all(stmt_unlock).subquery("all_lock_event")
            )
    stmt = select(all_lock_event_alias)

    stmt = stmt.where(all_lock_event_alias.c.account_address == account_address)

    if request_query.token_address is not None:
        stmt = stmt.where(
            all_lock_event_alias.c.token_address == request_query.token_address
        )
    if request_query.token_type is not None:
        stmt = stmt.where(all_lock_event_alias.c.type == request_query.token_type)
    if request_query.msg_sender is not None:
        stmt = stmt.where(all_lock_event_alias.c.msg_sender == request_query.msg_sender)
    if request_query.lock_address is not None:
        stmt = stmt.where(
            all_lock_event_alias.c.lock_address == request_query.lock_address
        )
    if request_query.recipient_address is not None:
        stmt = stmt.where(
            all_lock_event_alias.c.recipient_address == request_query.recipient_address
        )

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    sort_attr = column(sort_item)
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if sort_item != ListAllLockEventsSortItem.block_timestamp.value:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(
            desc(column(ListAllLockEventsSortItem.block_timestamp.value))
        )

    # Pagination
    if offset is not None:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    entries = [
        all_lock_event_alias.c.category,
        all_lock_event_alias.c.transaction_hash,
        all_lock_event_alias.c.msg_sender,
        all_lock_event_alias.c.token_address,
        all_lock_event_alias.c.lock_address,
        all_lock_event_alias.c.account_address,
        all_lock_event_alias.c.recipient_address,
        all_lock_event_alias.c.value,
        all_lock_event_alias.c.data,
        all_lock_event_alias.c.block_timestamp,
        Token,
    ]
    lock_events = (
        (await db.execute(select(*entries).from_statement(stmt))).tuples().all()
    )

    resp_data = []
    for lock_event in lock_events:
        token_name = None
        token: Token = lock_event.Token
        if token.type == TokenType.IBET_STRAIGHT_BOND.value:
            _contract = await IbetStraightBondContract(token.token_address).get()
            token_name = _contract.name
        elif token.type == TokenType.IBET_SHARE.value:
            _contract = await IbetShareContract(token.token_address).get()
            token_name = _contract.name

        block_timestamp_utc = timezone("UTC").localize(lock_event[9])
        resp_data.append(
            {
                "category": lock_event.category,
                "transaction_hash": lock_event.transaction_hash,
                "msg_sender": lock_event.msg_sender,
                "issuer_address": token.issuer_address,
                "token_address": token.token_address,
                "token_type": token.type,
                "token_name": token_name,
                "lock_address": lock_event.lock_address,
                "account_address": lock_event.account_address,
                "recipient_address": lock_event.recipient_address,
                "value": lock_event.value,
                "data": lock_event.data,
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
async def force_unlock(
    db: DBAsyncSession,
    request: Request,
    account_address: str,
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
    _account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    if not Web3.is_address(account_address):
        raise InvalidParameterError("account_address is not a valid address")

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Verify that the token is issued by the issuer_address
    _token = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == issuer_address,
                    Token.token_address == data.token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise InvalidParameterError("token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Force unlock
    unlock_data = {
        "lock_address": data.lock_address,
        "account_address": account_address,
        "recipient_address": data.recipient_address,
        "value": data.value,
        "data": "",
    }
    try:
        await IbetSecurityTokenInterface(data.token_address).force_unlock(
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
async def retrieve_position(
    db: DBAsyncSession,
    account_address: str,
    token_address: str,
    issuer_address: Optional[str] = Header(None),
):
    """Retrieve account's position"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token
    if issuer_address is not None:
        _token = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.issuer_address == issuer_address,
                        Token.token_status != 2,
                    )
                )
                .limit(1)
            )
        ).first()
    else:
        _token = (
            await db.scalars(
                select(Token)
                .where(
                    and_(Token.token_address == token_address, Token.token_status != 2)
                )
                .limit(1)
            )
        ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Position
    _record: tuple[IDXPosition, int] = (
        await db.execute(
            select(IDXPosition, func.sum(IDXLockedPosition.value))
            .outerjoin(
                IDXLockedPosition,
                and_(
                    IDXLockedPosition.token_address == IDXPosition.token_address,
                    IDXLockedPosition.account_address == IDXPosition.account_address,
                ),
            )
            .where(
                and_(
                    IDXPosition.token_address == token_address,
                    IDXPosition.account_address == account_address,
                )
            )
            .group_by(
                IDXPosition.id,
                IDXLockedPosition.token_address,
                IDXLockedPosition.account_address,
            )
            .limit(1)
        )
    ).first()

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
        _bond = await IbetStraightBondContract(_token.token_address).get()
        token_name = _bond.name
    elif _token.type == TokenType.IBET_SHARE.value:
        _share = await IbetShareContract(_token.token_address).get()
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
