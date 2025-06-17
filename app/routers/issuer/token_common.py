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

from typing import Annotated, Optional

import pytz
from fastapi import APIRouter, Header, Query
from sqlalchemy import asc, desc, func, select

import config
from app.database import DBAsyncSession
from app.model.db import ScheduledEvents, Token, TokenType
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.model.schema import (
    ListAllIssuedTokensQuery,
    ListAllIssuedTokensResponse,
    ListAllScheduledEventsQuery,
    ListAllScheduledEventsResponse,
    ListAllScheduledEventsSortItem,
)
from app.utils.check_utils import address_is_valid_address, validate_headers
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

router = APIRouter(
    prefix="",
    tags=["token_common"],
)

local_tz = pytz.timezone(config.TZ)
utc_tz = pytz.timezone("UTC")


# GET: /tokens
@router.get(
    "/tokens",
    operation_id="ListAllIssuedTokens",
    response_model=ListAllIssuedTokensResponse,
    responses=get_routers_responses(422),
)
async def list_all_issued_tokens(
    db: DBAsyncSession,
    request_query: Annotated[ListAllIssuedTokensQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all tokens issued from ibet-Prime"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base Query
    if issuer_address is None:
        stmt = select(Token)
    else:
        stmt = select(Token).where(Token.issuer_address == issuer_address)

    if request_query.token_address_list is not None:
        stmt = stmt.where(Token.token_address.in_(request_query.token_address_list))

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Search Filter
    if request_query.token_type is not None:
        stmt = stmt.where(Token.type == request_query.token_type)

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Sort
    sort_attr = getattr(Token, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if request_query.sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(Token.created))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

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
                "token_address": _token.token_address,
                "token_type": _token.type,
                "created": _issue_datetime,
                "token_status": _token.token_status,
                "contract_version": _token.version,
                "token_attributes": token_attr.__dict__,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "tokens": tokens,
    }
    return json_response(resp)


# GET: /tokens/scheduled_events
@router.get(
    "/tokens/scheduled_events",
    operation_id="ListAllScheduledEvents",
    response_model=ListAllScheduledEventsResponse,
)
async def list_all_scheduled_events(
    db: DBAsyncSession,
    request_query: Annotated[ListAllScheduledEventsQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all scheduled token update events"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base Query
    if issuer_address is None:
        stmt = select(ScheduledEvents)
    else:
        stmt = select(ScheduledEvents).where(
            ScheduledEvents.issuer_address == issuer_address
        )

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(ScheduledEvents).order_by(None)
    )

    # Search Filter
    if request_query.token_type is not None:
        stmt = stmt.where(ScheduledEvents.token_type == request_query.token_type)
    if request_query.token_address is not None:
        stmt = stmt.where(ScheduledEvents.token_address == request_query.token_address)
    if request_query.status is not None:
        stmt = stmt.where(ScheduledEvents.status == request_query.status)

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(ScheduledEvents).order_by(None)
    )

    # Sort
    sort_attr = getattr(ScheduledEvents, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if request_query.sort_item != ListAllScheduledEventsSortItem.CREATED:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(ScheduledEvents.created))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    # Execute Query
    rows = (await db.scalars(stmt)).all()

    # Get Token Attributes
    schedule_events = []
    for _event in rows:
        token_attr = None
        if _event.token_type == TokenType.IBET_STRAIGHT_BOND:
            token_attr = await IbetStraightBondContract(_event.token_address).get()
        elif _event.token_type == TokenType.IBET_SHARE:
            token_attr = await IbetShareContract(_event.token_address).get()

        _scheduled_datetime = (
            pytz.timezone("UTC")
            .localize(_event.scheduled_datetime)
            .astimezone(local_tz)
            .isoformat()
        )
        _created = (
            pytz.timezone("UTC")
            .localize(_event.created)
            .astimezone(local_tz)
            .isoformat()
        )

        schedule_events.append(
            {
                "scheduled_event_id": _event.event_id,
                "token_address": _event.token_address,
                "token_type": _event.token_type,
                "scheduled_datetime": _scheduled_datetime,
                "event_type": _event.event_type,
                "status": _event.status,
                "data": _event.data,
                "created": _created,
                "is_soft_deleted": _event.is_soft_deleted,
                "token_attributes": token_attr.__dict__,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "scheduled_events": schedule_events,
    }
    return json_response(resp)
