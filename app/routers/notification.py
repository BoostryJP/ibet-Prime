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

import pytz
from fastapi import APIRouter, Header, Query
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, func, select

from app.database import DBAsyncSession
from app.model.db import Notification
from app.model.schema import ListAllNotificationsResponse
from app.utils.check_utils import address_is_valid_address, validate_headers
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from config import TZ

router = APIRouter(tags=["notification"])

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /notifications
@router.get(
    "/notifications",
    response_model=ListAllNotificationsResponse,
    responses=get_routers_responses(422),
)
async def list_all_notifications(
    db: DBAsyncSession,
    issuer_address: Optional[str] = Header(None),
    notice_type: str = Query(None),
    offset: int = Query(None),
    limit: int = Query(None),
):
    """List all notifications"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    stmt = select(Notification).order_by(Notification.created)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if issuer_address is not None:
        stmt = stmt.where(Notification.issuer_address == issuer_address)
    if notice_type is not None:
        stmt = stmt.where(Notification.type == notice_type)

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _notification_list: Sequence[Notification] = (await db.scalars(stmt)).all()

    notifications = []
    for _notification in _notification_list:
        created_formatted = (
            utc_tz.localize(_notification.created).astimezone(local_tz).isoformat()
        )
        notifications.append(
            {
                "notice_id": _notification.notice_id,
                "issuer_address": _notification.issuer_address,
                "priority": _notification.priority,
                "notice_type": _notification.type,
                "notice_code": _notification.code,
                "metainfo": _notification.metainfo,
                "created": created_formatted,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "notifications": notifications,
    }

    return json_response(resp)


# DELETE: /notifications/{notice_id}
@router.delete(
    "/notifications/{notice_id}",
    response_model=None,
    responses=get_routers_responses(422, 404),
)
async def delete_notification(
    db: DBAsyncSession,
    notice_id: str,
    issuer_address: str = Header(...),
):
    """Delete notification"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Notification
    _notification = (
        await db.scalars(
            select(Notification)
            .where(
                and_(
                    Notification.notice_id == notice_id,
                    Notification.issuer_address == issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _notification is None:
        raise HTTPException(status_code=404, detail="notification does not exist")

    # Delete Notification
    await db.delete(_notification)
    await db.commit()

    return
