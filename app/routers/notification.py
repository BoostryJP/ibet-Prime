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
import pytz

from fastapi import (
    APIRouter,
    Header,
    Query,
    Depends
)
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from config import TZ
from app.database import db_session
from app.model.db import Notification
from app.model.schema import ListAllNotificationsResponse
from app.utils.check_utils import (
    validate_headers,
    address_is_valid_address
)
from app.utils.fastapi import json_response
from app.utils.docs_utils import get_routers_responses

router = APIRouter(tags=["notification"])

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /notifications
@router.get(
    "/notifications",
    response_model=ListAllNotificationsResponse,
    responses=get_routers_responses(422)
)
def list_all_notifications(
    issuer_address: Optional[str] = Header(None),
    notice_type: str = Query(None),
    offset: int = Query(None),
    limit: int = Query(None),
    db: Session = Depends(db_session)
):
    """List all notifications"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    query = db.query(Notification). \
        order_by(Notification.created)
    total = query.count()

    # Search Filter
    if issuer_address is not None:
        query = query.filter(Notification.issuer_address == issuer_address)
    if notice_type is not None:
        query = query.filter(Notification.type == notice_type)
    count = query.count()

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _notification_list = query.all()

    notifications = []
    for _notification in _notification_list:
        created_formatted = utc_tz.localize(_notification.created).astimezone(local_tz).isoformat()
        notifications.append({
            "notice_id": _notification.notice_id,
            "issuer_address": _notification.issuer_address,
            "priority": _notification.priority,
            "notice_type": _notification.type,
            "notice_code": _notification.code,
            "metainfo": _notification.metainfo,
            "created": created_formatted
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "notifications": notifications
    }

    return json_response(resp)


# DELETE: /notifications/{notice_id}
@router.delete(
    "/notifications/{notice_id}",
    response_model=None,
    responses=get_routers_responses(422, 404)
)
def delete_notification(
    notice_id: str,
    issuer_address: str = Header(...),
    db: Session = Depends(db_session)
):
    """Delete notification"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Notification
    _notification = db.query(Notification). \
        filter(Notification.notice_id == notice_id). \
        filter(Notification.issuer_address == issuer_address). \
        first()
    if _notification is None:
        raise HTTPException(status_code=404, detail="notification does not exist")

    # Delete Notification
    db.delete(_notification)

    db.commit()
    return
