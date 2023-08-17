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
from typing import Optional, Sequence

from fastapi import APIRouter, Header, Path, Query
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, asc, desc, func, select

from app.database import DBSession
from app.exceptions import InvalidParameterError
from app.model.db import Token, TokenHolder, TokenHolderBatchStatus, TokenHoldersList
from app.model.schema import (
    CreateTokenHoldersListRequest,
    CreateTokenHoldersListResponse,
    ListAllTokenHolderCollectionsResponse,
    RetrieveTokenHoldersListResponse,
)
from app.utils.check_utils import address_is_valid_address, validate_headers
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.web3_utils import Web3Wrapper

web3 = Web3Wrapper()

router = APIRouter(
    prefix="/token",
    tags=["token_common"],
)


# POST: /token/holders/{token_address}/collection
@router.post(
    "/holders/{token_address}/collection",
    response_model=CreateTokenHoldersListResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def create_collection(
    db: DBSession,
    data: CreateTokenHoldersListRequest,
    token_address: str = Path(
        ...,
        examples=["0xABCdeF1234567890abcdEf123456789000000000"],
    ),
    issuer_address: str = Header(...),
):
    """Create collection"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.token_address == token_address,
                Token.issuer_address == issuer_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Validate block number
    if data.block_number > web3.eth.block_number:
        raise InvalidParameterError("Block number must be current or past one.")

    # Check list id conflict
    _same_list_id_record = db.scalars(
        select(TokenHoldersList)
        .where(TokenHoldersList.list_id == data.list_id)
        .limit(1)
    ).first()
    if _same_list_id_record is not None:
        raise InvalidParameterError("list_id must be unique.")

    # Check existing list
    _same_combi_record: TokenHoldersList | None = db.scalars(
        select(TokenHoldersList)
        .where(
            and_(
                TokenHoldersList.block_number == data.block_number,
                TokenHoldersList.token_address == token_address,
                TokenHoldersList.batch_status != TokenHolderBatchStatus.FAILED,
            )
        )
        .limit(1)
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
    db.commit()

    return json_response(
        {
            "status": _token_holders_list.batch_status,
            "list_id": _token_holders_list.list_id,
        }
    )


# GET: /token/holders/{token_address}/collection
@router.get(
    "/holders/{token_address}/collection",
    response_model=ListAllTokenHolderCollectionsResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def list_all_token_holders_collections(
    db: DBSession,
    token_address: str = Path(...),
    issuer_address: Optional[str] = Header(None),
    status: Optional[TokenHolderBatchStatus] = Query(None),
    sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc (created)"),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
):
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
    if issuer_address is not None:
        _token = db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == token_address,
                    Token.issuer_address == issuer_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        ).first()
    else:
        _token = db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        ).first()

    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Base query
    stmt = select(TokenHoldersList).where(
        TokenHoldersList.token_address == token_address
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    if status is not None:
        stmt = stmt.where(TokenHoldersList.batch_status == status.value)

    # Sort
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(TokenHoldersList.created)
    else:  # DESC
        stmt = stmt.order_by(desc(TokenHoldersList.created))

    # Count
    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    # Get all collections
    _token_holders_collections: Sequence[TokenHoldersList] = db.scalars(stmt).all()

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
    response_model=RetrieveTokenHoldersListResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
def retrieve_token_holders_list(
    db: DBSession,
    token_address: str = Path(...),
    list_id: str = Path(
        ...,
        examples=["cfd83622-34dc-4efe-a68b-2cc275d3d824"],
        description="UUID v4 required",
    ),
    issuer_address: str = Header(...),
):
    """Get token holders"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
    _token = db.scalars(
        select(Token)
        .where(
            and_(
                Token.token_address == token_address,
                Token.issuer_address == issuer_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Validate list id
    try:
        _uuid = uuid.UUID(list_id, version=4)
    except ValueError:
        description = "list_id must be UUIDv4."
        raise InvalidParameterError(description)

    # Check existing list
    _same_list_id_record: TokenHoldersList | None = db.scalars(
        select(TokenHoldersList).where(TokenHoldersList.list_id == list_id).limit(1)
    ).first()
    if not _same_list_id_record:
        raise HTTPException(status_code=404, detail="list not found")
    if _same_list_id_record.token_address != token_address:
        description = "list_id: %s is not related to token_address: %s" % (
            list_id,
            token_address,
        )
        raise InvalidParameterError(description)

    # Get holder list
    _token_holders: Sequence[TokenHolder] = db.scalars(
        select(TokenHolder)
        .where(TokenHolder.holder_list_id == _same_list_id_record.id)
        .order_by(asc(TokenHolder.account_address))
    ).all()
    token_holders = [_token_holder.json() for _token_holder in _token_holders]

    return json_response(
        {
            "status": _same_list_id_record.batch_status,
            "holders": token_holders,
        }
    )
