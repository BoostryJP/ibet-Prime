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

from typing import Annotated, Optional, Sequence

from eth_keyfile import decode_keyfile_json
from fastapi import APIRouter, Header, Path, Query, Request
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
    OperationNotSupportedVersionError,
    SendTransactionError,
)
from app.model.db import (
    EthIbetWSTTx,
    IbetWSTTxType,
    IDXLock,
    IDXLockedPosition,
    IDXPosition,
    IDXUnlock,
    Token,
    TokenStatus,
    TokenType,
    TokenVersion,
)
from app.model.ibet import (
    IbetSecurityTokenInterface,
    IbetShareContract,
    IbetStraightBondContract,
)
from app.model.ibet.tx_params.ibet_security_token import (
    ForceLockParams,
    ForceUnlockParams,
)
from app.model.schema import (
    ForceLockRequest,
    ForceUnlockRequest,
    ListAllLockedPositionResponse,
    ListAllLockedPositionsQuery,
    ListAllLockEventsQuery,
    ListAllLockEventsResponse,
    ListAllLockEventsSortItem,
    ListAllPositionResponse,
    ListAllPositionsQuery,
    LockDataMessage,
    LockEventCategory,
    PositionResponse,
    UnlockDataMessage,
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
    operation_id="ListAllPositions",
    response_model=ListAllPositionResponse,
    responses=get_routers_responses(422),
)
async def list_all_positions(
    db: DBAsyncSession,
    account_address: Annotated[str, Path()],
    request_query: Annotated[ListAllPositionsQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all positions"""

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
                IDXPosition.account_address == account_address,
                Token.token_status != TokenStatus.FAILED,
            )
        )
        .group_by(
            IDXPosition.token_address,
            IDXPosition.account_address,
            Token.id,
            IDXLockedPosition.token_address,
            IDXLockedPosition.account_address,
        )
    )

    if not request_query.include_former_position:
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

    total = await db.scalar(
        select(func.count()).select_from(stmt.with_only_columns(1).order_by(None))
    )

    # Search Filter
    if request_query.token_type is not None:
        stmt = stmt.where(Token.type == request_query.token_type)

    count = await db.scalar(
        select(func.count()).select_from(stmt.with_only_columns(1).order_by(None))
    )

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    _position_list: Sequence[tuple[IDXPosition, int, Token]] = (
        (await db.execute(stmt)).tuples().all()
    )

    positions = []
    for _position, _locked, _token in _position_list:
        # Get Token Attributes
        token_attr = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND:
            token_attr = await IbetStraightBondContract(_token.token_address).get()
        elif _token.type == TokenType.IBET_SHARE:
            token_attr = await IbetShareContract(_token.token_address).get()

        positions.append(
            {
                "issuer_address": _token.issuer_address,
                "token_address": _token.token_address,
                "token_type": _token.type,
                "token_name": token_attr.name if token_attr is not None else None,
                "token_attributes": token_attr.__dict__
                if (
                    request_query.include_token_attributes is True
                    and token_attr is not None
                )
                else None,
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
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "positions": positions,
    }

    return json_response(resp)


# GET: /positions/{account_address}/lock
@router.get(
    "/{account_address}/lock",
    operation_id="ListAllLockedPosition",
    response_model=ListAllLockedPositionResponse,
    responses=get_routers_responses(422),
)
async def list_all_locked_position(
    db: DBAsyncSession,
    account_address: Annotated[str, Path()],
    request_query: Annotated[ListAllLockedPositionsQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all locked position"""

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
                Token.token_status != TokenStatus.FAILED,
            )
        )
        .order_by(IDXLockedPosition.token_address)
    )

    if issuer_address is not None:
        stmt = stmt.where(Token.issuer_address == issuer_address)

    total = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(IDXLockedPosition)
        .order_by(None)
    )

    # Search Filter
    if request_query.token_type is not None:
        stmt = stmt.where(Token.type == request_query.token_type)

    count = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(IDXLockedPosition)
        .order_by(None)
    )

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

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
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "locked_positions": positions,
    }
    return json_response(resp)


# GET: /positions/{account_address}/lock/events
@router.get(
    "/{account_address}/lock/events",
    operation_id="ListAccountLockUnlockEvents",
    response_model=ListAllLockEventsResponse,
    responses=get_routers_responses(422),
)
async def list_account_lock_unlock_events(
    db: DBAsyncSession,
    account_address: Annotated[str, Path()],
    request_query: Annotated[ListAllLockEventsQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all lock/unlock events in the account"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base query
    stmt_lock = (
        select(
            literal(value=LockEventCategory.Lock.value, type_=String).label("category"),
            IDXLock.is_forced.label("is_forced"),
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
            and_(
                column("account_address") == account_address,
                Token.token_status != TokenStatus.FAILED,
            )
        )
    )
    if issuer_address is not None:
        stmt_lock = stmt_lock.where(Token.issuer_address == issuer_address)

    stmt_unlock = (
        select(
            literal(value=LockEventCategory.Unlock.value, type_=String).label(
                "category"
            ),
            IDXUnlock.is_forced.label("is_forced"),
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
            and_(
                column("account_address") == account_address,
                Token.token_status != TokenStatus.FAILED,
            )
        )
    )
    if issuer_address is not None:
        stmt_unlock = stmt_unlock.where(Token.issuer_address == issuer_address)

    total = (
        await db.scalar(
            stmt_lock.with_only_columns(func.count())
            .select_from(IDXLock)
            .order_by(None)
        )
    ) + (
        await db.scalar(
            stmt_unlock.with_only_columns(func.count())
            .select_from(IDXUnlock)
            .order_by(None)
        )
    )

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

    count = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(all_lock_event_alias)
        .order_by(None)
    )

    # Sort
    sort_attr = column(request_query.sort_item)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if request_query.sort_item != ListAllLockEventsSortItem.block_timestamp.value:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(
            desc(column(ListAllLockEventsSortItem.block_timestamp.value))
        )

    # Pagination
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)

    entries = [
        all_lock_event_alias.c.category,
        all_lock_event_alias.c.is_forced,
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

        block_timestamp_utc = timezone("UTC").localize(lock_event.block_timestamp)
        resp_data.append(
            {
                "category": lock_event.category,
                "is_forced": lock_event.is_forced,
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
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "events": resp_data,
    }
    return json_response(data)


@router.post(
    "/{account_address}/force_lock",
    operation_id="ForceLock",
    response_model=None,
    responses=get_routers_responses(
        401,
        422,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
        OperationNotSupportedVersionError,
    ),
)
async def force_lock(
    db: DBAsyncSession,
    request: Request,
    data: ForceLockRequest,
    account_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Force unlock the locked position

    - This feature is not available for tokens issued prior to v25.6.
    """

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
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise InvalidParameterError("token not found")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # This feature is not available for tokens issued prior to v25.6.
    if _token.version < TokenVersion.V_25_06:
        raise OperationNotSupportedVersionError(
            f"the operation is not supported in {_token.version}"
        )

    # Force lock
    lock_message_data = LockDataMessage(message=data.message).model_dump_json(
        exclude_none=True
    )
    lock_data = {
        "lock_address": data.lock_address,
        "account_address": account_address,
        "value": data.value,
        "data": lock_message_data,
    }
    try:
        await IbetSecurityTokenInterface(data.token_address).force_lock(
            tx_params=ForceLockParams(**lock_data),
            tx_sender=issuer_address,
            tx_sender_key=private_key,
        )
    except ContractRevertError:
        raise
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


@router.post(
    "/{account_address}/force_unlock",
    operation_id="ForceUnlock",
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
    data: ForceUnlockRequest,
    account_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
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
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == issuer_address,
                    Token.token_address == data.token_address,
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise InvalidParameterError("token not found")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Ensure that Burn or ForceBurn transactions for ibetWST are not in progress
    # NOTE:
    #   If a Burn or ForceBurn transaction for ibetWST is in progress,
    #   executing a ForceUnlock transaction may result in an insufficient locked balance error
    #   during the ForceUnlock transaction associated with the WST transaction.
    if _token.ibet_wst_activated and _token.ibet_wst_address is not None:
        _pending_wst_tx: EthIbetWSTTx | None = (
            await db.scalars(
                select(EthIbetWSTTx)
                .where(
                    and_(
                        EthIbetWSTTx.tx_type.in_(
                            [IbetWSTTxType.BURN, IbetWSTTxType.FORCE_BURN]
                        ),
                        EthIbetWSTTx.ibet_wst_address == _token.ibet_wst_address,
                        EthIbetWSTTx.authorizer == account_address,
                        EthIbetWSTTx.finalized == False,
                    )
                )
                .limit(1)
            )
        ).first()
        if _pending_wst_tx is not None:
            raise InvalidParameterError(
                "There is a pending ibetWST Burn or ForceBurn transaction for this account"
            )

    # Force unlock
    unlock_message_data = UnlockDataMessage(message=data.message).model_dump_json(
        exclude_none=True
    )
    unlock_data = {
        "lock_address": data.lock_address,
        "account_address": account_address,
        "recipient_address": data.recipient_address,
        "value": data.value,
        "data": unlock_message_data,
    }
    try:
        await IbetSecurityTokenInterface(data.token_address).force_unlock(
            tx_params=ForceUnlockParams(**unlock_data),
            tx_sender=issuer_address,
            tx_sender_key=private_key,
        )
    except ContractRevertError:
        raise
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /positions/{account_address}/{token_address}
@router.get(
    "/{account_address}/{token_address}",
    operation_id="RetrieveTokenPositionForAccount",
    response_model=PositionResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
async def retrieve_position(
    db: DBAsyncSession,
    account_address: Annotated[str, Path()],
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """Retrieve token position for account"""

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
                        Token.token_status != TokenStatus.FAILED,
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
                    and_(
                        Token.token_address == token_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == TokenStatus.PENDING:
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
                IDXPosition.token_address,
                IDXPosition.account_address,
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

    # Get Token Attributes
    token_attr = None
    if _token.type == TokenType.IBET_STRAIGHT_BOND:
        token_attr = await IbetStraightBondContract(_token.token_address).get()
    elif _token.type == TokenType.IBET_SHARE:
        token_attr = await IbetShareContract(_token.token_address).get()

    resp = {
        "issuer_address": _token.issuer_address,
        "token_address": _token.token_address,
        "token_type": _token.type,
        "token_name": token_attr.name if token_attr is not None else None,
        "token_attributes": token_attr.__dict__ if token_attr is not None else None,
        "balance": _position.balance,
        "exchange_balance": _position.exchange_balance,
        "exchange_commitment": _position.exchange_commitment,
        "pending_transfer": _position.pending_transfer,
        "locked": _locked if _locked is not None else 0,
    }

    return json_response(resp)
