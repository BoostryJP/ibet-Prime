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

from typing import Annotated

import pytz
from eth_utils import to_checksum_address
from fastapi import APIRouter, Path, Query
from sqlalchemy import asc, desc, func, select

import config
from app.database import DBAsyncSession
from app.model import EthereumAddress
from app.model.db import Token, TokenType
from app.model.eth import IbetWST
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.model.schema import (
    GetIbetWSTBalanceResponse,
    ListAllIbetWSTTokensQuery,
    ListAllIbetWSTTokensResponse,
    ListAllIbetWSTTokensSortItem,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

router = APIRouter(prefix="/ibet_wst", tags=["[misc] ibet_wst"])
local_tz = pytz.timezone(config.TZ)
utc_tz = pytz.timezone("UTC")


# GET: /ibet_wst/tokens
@router.get(
    "/tokens",
    operation_id="ListAllIbetWSTTokens",
    response_model=ListAllIbetWSTTokensResponse,
    responses=get_routers_responses(422),
)
async def list_all_ibet_wst_tokens(
    db: DBAsyncSession,
    get_query: Annotated[ListAllIbetWSTTokensQuery, Query()],
):
    """
    List all IbetWST tokens

    - This endpoint retrieves all IbetWST tokens based on the provided query parameters.
    - Only tokens whose deployment has already been finalized will be returned.
    """

    # Base Query
    stmt = select(Token).where(Token.ibet_wst_deployed.is_(True))

    if get_query.issuer_address is not None:
        stmt = stmt.where(Token.issuer_address == get_query.issuer_address)

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Search Filter
    if get_query.ibet_wst_address is not None:
        stmt = stmt.where(Token.ibet_wst_address == get_query.ibet_wst_address)
    if get_query.ibet_token_address is not None:
        stmt = stmt.where(Token.token_address == get_query.ibet_token_address)
    if get_query.token_type is not None:
        stmt = stmt.where(Token.type == get_query.token_type)

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Sort
    sort_attr = getattr(Token, get_query.sort_item, None)
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if get_query.sort_item != ListAllIbetWSTTokensSortItem.CREATED:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(Token.created))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    # Execute Query
    issued_tokens = (await db.scalars(stmt)).all()

    # Get Token Attributes
    tokens = []
    for _token in issued_tokens:
        token_attr = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND:
            token_attr = await IbetStraightBondContract(_token.token_address).get()
        elif _token.type == TokenType.IBET_SHARE:
            token_attr = await IbetShareContract(_token.token_address).get()

        _issue_datetime = (
            pytz.timezone("UTC")
            .localize(_token.created)
            .astimezone(local_tz)
            .isoformat()
        )
        tokens.append(
            {
                "issuer_address": _token.issuer_address,
                "ibet_wst_address": _token.ibet_wst_address,
                "ibet_token_address": _token.token_address,
                "ibet_token_type": _token.type,
                "ibet_token_attributes": token_attr.__dict__,
                "created": _issue_datetime,
            }
        )

    # Response
    resp = {
        "result_set": {
            "count": count,
            "offset": get_query.offset,
            "limit": get_query.limit,
            "total": total,
        },
        "tokens": tokens,
    }
    return json_response(resp)


# GET: /ibet_wst/balances/{account_address}/{ibet_wst_address}
@router.get(
    "/balances/{account_address}/{ibet_wst_address}",
    operation_id="GetIbetWSTBalance",
    response_model=GetIbetWSTBalanceResponse,
    responses=get_routers_responses(422),
)
async def get_ibet_wst_balance(
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
):
    """
    Get IbetWST balance for a specific account address

    - This endpoint retrieves the IbetWST balance for the specified account address.
    """

    wst_contract = IbetWST(to_checksum_address(ibet_wst_address))
    balance = await wst_contract.balance_of(to_checksum_address(account_address))

    return json_response({"balance": balance})
