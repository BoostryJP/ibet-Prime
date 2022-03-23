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
import json
from typing import Optional
import pytz

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Path
)
from fastapi.exceptions import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import TZ
from app.database import db_session
from app.model.schema import (
    E2EMessagingResponse,
    ListAllE2EMessagingResponse
)
from app.utils.check_utils import (
    validate_headers,
    address_is_valid_address
)
from app.utils.docs_utils import get_routers_responses
from app.model.db import (
    IDXE2EMessaging,
    E2EMessagingAccount
)
from app import log

LOG = log.get_logger()

router = APIRouter(tags=["e2e_messaging"])

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /e2e_messaging/receive
@router.get(
    "/e2e_messaging/receive",
    response_model=ListAllE2EMessagingResponse,
    responses=get_routers_responses(422)
)
def list_all_e2e_messages(
        account_address: Optional[str] = Header(None),
        from_address: Optional[str] = Query(None),
        _type: Optional[str] = Query(None, alias="type"),
        message: Optional[str] = Query(None, description="partial match"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)):
    """List all e2e messaging"""

    # Validate Headers
    validate_headers(account_address=(account_address, address_is_valid_address))

    # NOTE: Only received message
    query = db.query(IDXE2EMessaging). \
        join(E2EMessagingAccount,
             IDXE2EMessaging.to_address == E2EMessagingAccount.account_address). \
        order_by(desc(IDXE2EMessaging.id))
    if account_address is not None:
        query = query.filter(IDXE2EMessaging.to_address == account_address)
    total = query.count()

    # Search Filter
    if from_address is not None:
        query = query.filter(IDXE2EMessaging.from_address == from_address)
    if _type is not None:
        query = query.filter(IDXE2EMessaging.type == _type)
    if message is not None:
        query = query.filter(IDXE2EMessaging.message.like("%" + message + "%"))
    count = query.count()

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _e2e_messaging_list = query.all()

    e2e_messages = []
    for _e2e_messaging in _e2e_messaging_list:
        send_timestamp_formatted = utc_tz.localize(_e2e_messaging.send_timestamp).astimezone(local_tz).isoformat()
        try:
            # json or list string decode
            message = json.loads(_e2e_messaging.message)
        except json.decoder.JSONDecodeError:
            message = _e2e_messaging.message
        e2e_messages.append({
            "id": _e2e_messaging.id,
            "from_address": _e2e_messaging.from_address,
            "to_address": _e2e_messaging.to_address,
            "type": _e2e_messaging.type,
            "message": message,
            "send_timestamp": send_timestamp_formatted,
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "e2e_messages": e2e_messages
    }

    return resp


# GET: /e2e_messaging/receive/{id}
@router.get(
    "/e2e_messaging/receive/{id}",
    response_model=E2EMessagingResponse,
    responses=get_routers_responses(422, 404)
)
def retrieve_e2e_messaging(
        _id: str = Path(..., alias="id"),
        account_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve an e2e messaging"""

    # Validate Headers
    validate_headers(account_address=(account_address, address_is_valid_address))

    # Get E2E Messaging
    query = db.query(IDXE2EMessaging). \
        join(E2EMessagingAccount,
             IDXE2EMessaging.to_address == E2EMessagingAccount.account_address). \
        filter(IDXE2EMessaging.id == _id)
    if account_address is not None:
        query = query.filter(IDXE2EMessaging.to_address == account_address)
    _e2e_messaging = query.first()
    if _e2e_messaging is None:
        raise HTTPException(status_code=404, detail="e2e messaging not found")

    send_timestamp_formatted = utc_tz.localize(_e2e_messaging.send_timestamp).astimezone(local_tz).isoformat()
    try:
        # json or list string decode
        message = json.loads(_e2e_messaging.message)
    except json.decoder.JSONDecodeError:
        message = _e2e_messaging.message

    return {
        "id": _e2e_messaging.id,
        "from_address": _e2e_messaging.from_address,
        "to_address": _e2e_messaging.to_address,
        "type": _e2e_messaging.type,
        "message": message,
        "send_timestamp": send_timestamp_formatted,
    }
