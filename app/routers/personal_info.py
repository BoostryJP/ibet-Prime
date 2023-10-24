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
from typing import Sequence

from fastapi import APIRouter, Depends, Header
from pytz import timezone
from sqlalchemy import desc, func, select

import config
from app import log
from app.database import DBSession
from app.model.db import IDXPersonalInfo
from app.model.schema import (  # Request; Response
    ListPersonalInfoQuery,
    ListPersonalInfoResponse,
)
from app.utils.check_utils import address_is_valid_address, validate_headers
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

router = APIRouter(
    prefix="/personal_info",
    tags=["personal_info"],
)

LOG = log.get_logger()
local_tz = timezone(config.TZ)
utc_tz = timezone("UTC")


# POST: /personal_info
@router.get(
    "/",
    response_model=ListPersonalInfoResponse,
    responses=get_routers_responses(422),
)
def list_all_personal_info(
    db: DBSession,
    issuer_address: str = Header(...),
    request_query: ListPersonalInfoQuery = Depends(),
):
    """Issue ibetShare token"""
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    offset = request_query.offset
    limit = request_query.limit
    sort_order = request_query.sort_order  # default: asc

    stmt = select(IDXPersonalInfo).where(
        IDXPersonalInfo.issuer_address == issuer_address
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if sort_order == 0:
        stmt = stmt.order_by(IDXPersonalInfo.created)
    else:
        stmt = stmt.order_by(desc(IDXPersonalInfo.created))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    personal_info_list: Sequence[IDXPersonalInfo] = db.scalars(stmt).all()
    data = [_personal_info.json() for _personal_info in personal_info_list]

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "personal_info": data,
        },
    )
