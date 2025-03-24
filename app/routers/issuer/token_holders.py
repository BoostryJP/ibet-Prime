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

import uuid
from datetime import datetime
from typing import Annotated, Optional, Sequence

import pytz
from fastapi import APIRouter, Header, Path, Query
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, asc, desc, func, select

import config
from app.database import DBAsyncSession
from app.exceptions import InvalidParameterError
from app.model.db import (
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    Token,
    TokenHolder,
    TokenHolderBatchStatus,
    TokenHoldersList,
    TokenStatus,
)
from app.model.schema import (
    CreateTokenHoldersListRequest,
    CreateTokenHoldersListResponse,
    ListAllTokenHolderCollectionsResponse,
    ListTokenHoldersPersonalInfoHistoryQuery,
    ListTokenHoldersPersonalInfoHistoryResponse,
    ListTokenHoldersPersonalInfoQuery,
    ListTokenHoldersPersonalInfoResponse,
    RetrieveTokenHoldersCollectionQuery,
    RetrieveTokenHoldersCollectionSortItem,
    RetrieveTokenHoldersListResponse,
)
from app.model.schema.base import KeyManagerType, ValueOperator
from app.utils.check_utils import address_is_valid_address, validate_headers
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.web3_utils import AsyncWeb3Wrapper

web3 = AsyncWeb3Wrapper()

router = APIRouter(
    prefix="/token",
    tags=["token_common"],
)
local_tz = pytz.timezone(config.TZ)
utc_tz = pytz.timezone("UTC")


# GET: /token/holders/personal_info
@router.get(
    "/holders/personal_info",
    operation_id="ListTokenHoldersPersonalInfo",
    response_model=ListTokenHoldersPersonalInfoResponse,
    responses=get_routers_responses(422),
)
async def list_all_token_holders_personal_info(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Header()],
    get_query: Annotated[ListTokenHoldersPersonalInfoQuery, Query()],
):
    """Lists the personal information of all registered holders linked to the token issuer"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base query
    stmt = select(IDXPersonalInfo).where(
        IDXPersonalInfo.issuer_address == issuer_address
    )
    match get_query.key_manager_type:
        case KeyManagerType.SELF:
            stmt = stmt.where(
                IDXPersonalInfo._personal_info["key_manager"].as_string() == "SELF"
            )
        case KeyManagerType.OTHERS:
            stmt = stmt.where(
                IDXPersonalInfo._personal_info["key_manager"].as_string() != "SELF"
            )
    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(IDXPersonalInfo).order_by(None)
    )

    # Filter
    if get_query.account_address:
        stmt = stmt.where(IDXPersonalInfo.account_address == get_query.account_address)
    if get_query.created_from:
        _created_from = datetime.strptime(
            get_query.created_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.created
            >= local_tz.localize(_created_from).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.created_to:
        _created_to = datetime.strptime(
            get_query.created_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.created
            <= local_tz.localize(_created_to).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.modified_from:
        _modified_from = datetime.strptime(
            get_query.modified_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.modified
            >= local_tz.localize(_modified_from).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.modified_to:
        _modified_to = datetime.strptime(
            get_query.modified_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.modified
            <= local_tz.localize(_modified_to).astimezone(utc_tz).replace(tzinfo=None)
        )

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(IDXPersonalInfo).order_by(None)
    )

    # Sort
    sort_attr = getattr(IDXPersonalInfo, get_query.sort_item, None)
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if get_query.sort_item != IDXPersonalInfo.created:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(IDXPersonalInfo.created)

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    personal_info_list: Sequence[IDXPersonalInfo] = (await db.scalars(stmt)).all()
    data = [_personal_info.json() for _personal_info in personal_info_list]

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "personal_info": data,
        },
    )


# GET: /token/holders/personal_info/history
@router.get(
    "/holders/personal_info/history",
    operation_id="ListTokenHoldersPersonalInfoHistory",
    response_model=ListTokenHoldersPersonalInfoHistoryResponse,
    responses=get_routers_responses(422),
)
async def list_all_token_holders_personal_info_history(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Header()],
    get_query: Annotated[ListTokenHoldersPersonalInfoHistoryQuery, Query()],
):
    """List personal information historical data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base query
    stmt = select(IDXPersonalInfoHistory).where(
        IDXPersonalInfoHistory.issuer_address == issuer_address
    )
    match get_query.key_manager_type:
        case KeyManagerType.SELF:
            stmt = stmt.where(
                IDXPersonalInfoHistory.personal_info["key_manager"].as_string()
                == "SELF"
            )
        case KeyManagerType.OTHERS:
            stmt = stmt.where(
                IDXPersonalInfoHistory.personal_info["key_manager"].as_string()
                != "SELF"
            )
    total = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(IDXPersonalInfoHistory)
        .order_by(None)
    )

    # Filter
    if get_query.account_address is not None:
        stmt = stmt.where(
            IDXPersonalInfoHistory.account_address == get_query.account_address
        )
    if get_query.event_type is not None:
        stmt = stmt.where(IDXPersonalInfoHistory.event_type == get_query.event_type)
    if get_query.block_timestamp_from:
        _block_timestamp_from = datetime.strptime(
            get_query.block_timestamp_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfoHistory.block_timestamp
            >= local_tz.localize(_block_timestamp_from)
            .astimezone(utc_tz)
            .replace(tzinfo=None)
        )
    if get_query.block_timestamp_to:
        _block_timestamp_to = datetime.strptime(
            get_query.block_timestamp_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfoHistory.block_timestamp
            <= local_tz.localize(_block_timestamp_to)
            .astimezone(utc_tz)
            .replace(tzinfo=None)
        )
    if get_query.created_from:
        _created_from = datetime.strptime(
            get_query.created_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfoHistory.created
            >= local_tz.localize(_created_from).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.created_to:
        _created_to = datetime.strptime(
            get_query.created_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfoHistory.created
            <= local_tz.localize(_created_to).astimezone(utc_tz).replace(tzinfo=None)
        )

    count = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(IDXPersonalInfoHistory)
        .order_by(None)
    )

    # Sort
    if get_query.sort_order == 0:
        stmt = stmt.order_by(IDXPersonalInfoHistory.block_timestamp)
    else:
        stmt = stmt.order_by(desc(IDXPersonalInfoHistory.block_timestamp))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    history_list: Sequence[IDXPersonalInfoHistory] = (await db.scalars(stmt)).all()
    data = [_history.json() for _history in history_list]

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "personal_info": data,
        },
    )


# POST: /token/holders/{token_address}/collection
@router.post(
    "/holders/{token_address}/collection",
    operation_id="CreateTokenHoldersCollection",
    response_model=CreateTokenHoldersListResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def create_token_holders_collection(
    db: DBAsyncSession,
    data: CreateTokenHoldersListRequest,
    token_address: str = Path(
        ...,
        examples=["0xABCdeF1234567890abcdEf123456789000000000"],
    ),
    issuer_address: str = Header(...),
):
    """Create token holders collection"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
    _token: Token | None = (
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
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Validate block number
    if data.block_number > await web3.eth.block_number:
        raise InvalidParameterError("Block number must be current or past one.")

    # Check list id conflict
    _same_list_id_record = (
        await db.scalars(
            select(TokenHoldersList)
            .where(TokenHoldersList.list_id == data.list_id)
            .limit(1)
        )
    ).first()
    if _same_list_id_record is not None:
        raise InvalidParameterError("list_id must be unique.")

    # Check existing list
    _same_combi_record: TokenHoldersList | None = (
        await db.scalars(
            select(TokenHoldersList)
            .where(
                and_(
                    TokenHoldersList.block_number == data.block_number,
                    TokenHoldersList.token_address == token_address,
                    TokenHoldersList.batch_status != TokenHolderBatchStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()

    if _same_combi_record:
        return json_response(
            {
                "status": _same_combi_record.batch_status,
                "list_id": _same_combi_record.list_id,
            }
        )

    _token_holders_list = TokenHoldersList()
    _token_holders_list.token_address = token_address
    _token_holders_list.list_id = data.list_id
    _token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
    _token_holders_list.block_number = data.block_number
    db.add(_token_holders_list)
    await db.commit()

    return json_response(
        {
            "status": _token_holders_list.batch_status,
            "list_id": _token_holders_list.list_id,
        }
    )


# GET: /token/holders/{token_address}/collection
@router.get(
    "/holders/{token_address}/collection",
    operation_id="ListAllTokenHoldersCollections",
    response_model=ListAllTokenHolderCollectionsResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_all_token_holders_collections(
    db: DBAsyncSession,
    token_address: str = Path(...),
    issuer_address: Optional[str] = Header(None),
    status: Optional[TokenHolderBatchStatus] = Query(None),
    sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc (created)"),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
):
    """List all token holders collections"""
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
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

    # Base query
    stmt = select(TokenHoldersList).where(
        TokenHoldersList.token_address == token_address
    )
    total = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(TokenHoldersList)
        .order_by(None)
    )

    if status is not None:
        stmt = stmt.where(TokenHoldersList.batch_status == status.value)

    # Sort
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(TokenHoldersList.created)
    else:  # DESC
        stmt = stmt.order_by(desc(TokenHoldersList.created))

    # Count
    count = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(TokenHoldersList)
        .order_by(None)
    )

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    # Get all collections
    _token_holders_collections: Sequence[TokenHoldersList] = (
        await db.scalars(stmt)
    ).all()

    token_holders_collections = []
    for _collection in _token_holders_collections:
        token_holders_collections.append(
            {
                "token_address": _collection.token_address,
                "block_number": _collection.block_number,
                "list_id": _collection.list_id,
                "status": _collection.batch_status,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "collections": token_holders_collections,
    }

    return json_response(resp)


# GET: /token/holders/{token_address}/collection/{list_id}
@router.get(
    "/holders/{token_address}/collection/{list_id}",
    operation_id="RetrieveTokenHoldersCollection",
    response_model=RetrieveTokenHoldersListResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
async def retrieve_token_holders_collection(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    list_id: Annotated[
        str,
        Path(
            examples=["cfd83622-34dc-4efe-a68b-2cc275d3d824"],
            description="UUID v4 required",
        ),
    ],
    issuer_address: Annotated[str, Header()],
    get_query: Annotated[RetrieveTokenHoldersCollectionQuery, Query()],
):
    """Retrieve token holders collection"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
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
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Validate list id
    try:
        _uuid = uuid.UUID(list_id, version=4)
    except ValueError:
        description = "list_id must be UUIDv4."
        raise InvalidParameterError(description)

    # Check existing list
    _same_list_id_record: TokenHoldersList | None = (
        await db.scalars(
            select(TokenHoldersList).where(TokenHoldersList.list_id == list_id).limit(1)
        )
    ).first()
    if not _same_list_id_record:
        raise HTTPException(status_code=404, detail="list not found")
    if _same_list_id_record.token_address != token_address:
        description = "list_id: %s is not related to token_address: %s" % (
            list_id,
            token_address,
        )
        raise InvalidParameterError(description)

    # Base query
    stmt = (
        select(TokenHolder, IDXPersonalInfo)
        .outerjoin(
            IDXPersonalInfo,
            and_(
                IDXPersonalInfo.issuer_address == issuer_address,
                IDXPersonalInfo.account_address == TokenHolder.account_address,
            ),
        )
        .where(TokenHolder.holder_list_id == _same_list_id_record.id)
    )
    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(TokenHolder).order_by(None)
    )

    if (
        get_query.hold_balance is not None
        and get_query.hold_balance_operator is not None
    ):
        match get_query.hold_balance_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(TokenHolder.hold_balance == get_query.hold_balance)
            case ValueOperator.GTE:
                stmt = stmt.where(TokenHolder.hold_balance >= get_query.hold_balance)
            case ValueOperator.LTE:
                stmt = stmt.where(TokenHolder.hold_balance <= get_query.hold_balance)

    if (
        get_query.locked_balance is not None
        and get_query.locked_balance_operator is not None
    ):
        match get_query.locked_balance_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(
                    TokenHolder.locked_balance == get_query.locked_balance
                )
            case ValueOperator.GTE:
                stmt = stmt.where(
                    TokenHolder.locked_balance >= get_query.locked_balance
                )
            case ValueOperator.LTE:
                stmt = stmt.where(
                    TokenHolder.locked_balance <= get_query.locked_balance
                )

    if get_query.account_address is not None:
        stmt = stmt.where(
            TokenHolder.account_address.like("%" + get_query.account_address + "%")
        )

    if get_query.tax_category is not None:
        stmt = stmt.where(
            IDXPersonalInfo._personal_info["tax_category"].as_integer()
            == get_query.tax_category
        )

    if get_query.key_manager is not None:
        stmt = stmt.where(
            IDXPersonalInfo._personal_info["key_manager"]
            .as_string()
            .like("%" + get_query.key_manager + "%")
        )

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(TokenHolder).order_by(None)
    )

    # Sort
    if get_query.sort_item == RetrieveTokenHoldersCollectionSortItem.tax_category:
        sort_attr = IDXPersonalInfo._personal_info["tax_category"].as_integer()
    elif get_query.sort_item == RetrieveTokenHoldersCollectionSortItem.key_manager:
        sort_attr = IDXPersonalInfo._personal_info["key_manager"].as_string()
    else:
        sort_attr = getattr(TokenHolder, get_query.sort_item)

    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if get_query.sort_item != RetrieveTokenHoldersCollectionSortItem.account_address:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(
            asc(RetrieveTokenHoldersCollectionSortItem.account_address)
        )

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    # Get holder list
    _token_holders: Sequence[tuple[TokenHolder, IDXPersonalInfo | None]] = (
        (await db.execute(stmt)).tuples().all()
    )
    personal_info_default = {
        "key_manager": None,
        "name": None,
        "postal_code": None,
        "address": None,
        "email": None,
        "birth": None,
        "is_corporate": None,
        "tax_category": None,
    }
    token_holders = [
        {
            **_token_holder[0].json(),
            "personal_information": (
                _token_holder[1].personal_info
                if _token_holder[1] is not None
                and _token_holder[1].personal_info is not None
                else personal_info_default
            ),
        }
        for _token_holder in _token_holders
    ]

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "status": _same_list_id_record.batch_status,
            "holders": token_holders,
        }
    )
