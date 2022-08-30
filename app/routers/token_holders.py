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
from typing import List

from fastapi import APIRouter, Depends, Header, Path
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import asc
from web3 import Web3
from web3.middleware import geth_poa_middleware
import config

from app.database import db_session
from app.model.schema import (
    CreateTokenHoldersListRequest,
    CreateTokenHoldersListResponse,
    GetTokenHoldersListResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.check_utils import validate_headers, address_is_valid_address
from app.model.db import Token, TokenHoldersList, TokenHolderBatchStatus, TokenHolder
from app.exceptions import InvalidParameterError

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

router = APIRouter(
    prefix="/token",
    tags=["token"],
)


# POST: /token/holders/{token_address}/collection
@router.post(
    "/holders/{token_address}/collection",
    response_model=CreateTokenHoldersListResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def create_collection(
    data: CreateTokenHoldersListRequest,
    token_address: str = Path(
        ...,
        example="0xABCdeF1234567890abcdEf123456789000000000",
    ),
    issuer_address: str = Header(...),
    db: Session = Depends(db_session),
):
    """Create collection"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
    query = (
        db.query(Token)
        .filter(Token.token_address == token_address)
        .filter(Token.issuer_address == issuer_address)
        .filter(Token.token_status != 2)
    )
    _token = query.first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Validate block number
    if data.block_number > web3.eth.block_number:
        raise InvalidParameterError("Block number must be current or past one.")

    # Check list id conflict
    _same_list_id_record = (
        db.query(TokenHoldersList)
        .filter(TokenHoldersList.list_id == data.list_id)
        .first()
    )
    if _same_list_id_record is not None:
        raise InvalidParameterError("list_id must be unique.")

    # Check existing list
    _same_combi_record: TokenHoldersList = (
        db.query(TokenHoldersList)
        .filter(TokenHoldersList.block_number == data.block_number)
        .filter(TokenHoldersList.token_address == token_address)
        .filter(TokenHoldersList.batch_status != TokenHolderBatchStatus.FAILED.value)
        .first()
    )

    if _same_combi_record:
        return {
            "status": _same_combi_record.batch_status,
            "list_id": _same_combi_record.list_id,
        }

    _token_holders_list = TokenHoldersList()
    _token_holders_list.token_address = token_address
    _token_holders_list.list_id = data.list_id
    _token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
    _token_holders_list.block_number = data.block_number

    db.add(_token_holders_list)
    db.commit()

    return {
        "status": _token_holders_list.batch_status,
        "list_id": _token_holders_list.list_id,
    }


# GET: /token/holders/{token_address}/collection/{list_id}
@router.get(
    "/holders/{token_address}/collection/{list_id}",
    response_model=GetTokenHoldersListResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
def get_token_holders(
    token_address: str = Path(...),
    list_id: str = Path(
        ...,
        example="cfd83622-34dc-4efe-a68b-2cc275d3d824",
        description="UUID v4 required",
    ),
    issuer_address: str = Header(...),
    db: Session = Depends(db_session),
):
    """Get token holders"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token to ensure input token valid
    query = (
        db.query(Token)
        .filter(Token.token_address == token_address)
        .filter(Token.issuer_address == issuer_address)
        .filter(Token.token_status != 2)
    )
    _token = query.first()
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
    _same_list_id_record: TokenHoldersList = (
        db.query(TokenHoldersList).filter(TokenHoldersList.list_id == list_id).first()
    )

    if not _same_list_id_record:
        raise HTTPException(status_code=404, detail="list not found")
    if _same_list_id_record.token_address != token_address:
        description = "list_id: %s is not related to token_address: %s" % (
            list_id,
            token_address,
        )
        raise InvalidParameterError(description)

    _token_holders: List[TokenHolder] = (
        db.query(TokenHolder)
        .filter(TokenHolder.holder_list_id == _same_list_id_record.id)
        .order_by(asc(TokenHolder.account_address))
        .all()
    )
    token_holders = [_token_holder.json() for _token_holder in _token_holders]

    return {
        "status": _same_list_id_record.batch_status,
        "holders": token_holders,
    }
