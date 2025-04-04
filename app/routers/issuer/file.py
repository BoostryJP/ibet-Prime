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

import base64
import uuid
from typing import Annotated, Optional

import pytz
from fastapi import APIRouter, Header, Path, Query
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, desc, func, select

from app.database import DBAsyncSession
from app.model.db import UploadFile
from app.model.schema import (
    DownloadFileResponse,
    FileResponse,
    ListAllFilesResponse,
    ListAllUploadFilesQuery,
    UploadFileRequest,
)
from app.utils.check_utils import address_is_valid_address, validate_headers
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from config import TZ

router = APIRouter(prefix="/files", tags=["utility"])

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /files
@router.get(
    "",
    operation_id="ListAllUploadFiles",
    response_model=ListAllFilesResponse,
    responses=get_routers_responses(422),
)
async def list_all_upload_files(
    db: DBAsyncSession,
    get_query: Annotated[ListAllUploadFilesQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all upload files"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    rows = [
        UploadFile.file_id,
        UploadFile.issuer_address,
        UploadFile.relation,
        UploadFile.file_name,
        UploadFile.content_size,
        UploadFile.description,
        UploadFile.label,
        UploadFile.created,
    ]
    stmt = select(*rows).order_by(desc(UploadFile.modified))

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(UploadFile).order_by(None)
    )

    # Search Filter
    if issuer_address is not None:
        stmt = stmt.where(UploadFile.issuer_address == issuer_address)
    if get_query.relation is not None:
        stmt = stmt.where(UploadFile.relation == get_query.relation)
    if get_query.file_name is not None:
        stmt = stmt.where(UploadFile.file_name.like("%" + get_query.file_name + "%"))
    if get_query.label is not None:
        if get_query.label == "":
            stmt = stmt.where(UploadFile.label == "")
        else:
            stmt = stmt.where(UploadFile.label.like("%" + get_query.label + "%"))

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(UploadFile).order_by(None)
    )

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _upload_file_list = (await db.execute(stmt)).tuples().all()

    files = []
    for _upload_file in _upload_file_list:
        created_formatted = (
            utc_tz.localize(_upload_file.created).astimezone(local_tz).isoformat()
        )
        files.append(
            {
                "file_id": _upload_file.file_id,
                "issuer_address": _upload_file.issuer_address,
                "relation": _upload_file.relation,
                "file_name": _upload_file.file_name,
                "content_size": _upload_file.content_size,
                "description": _upload_file.description,
                "label": _upload_file.label,
                "created": created_formatted,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": get_query.offset,
            "limit": get_query.limit,
            "total": total,
        },
        "files": files,
    }

    return json_response(resp)


# POST: /files
@router.post(
    "",
    operation_id="UploadFile",
    response_model=FileResponse,
    responses=get_routers_responses(422),
)
async def upload_file(
    db: DBAsyncSession,
    data: UploadFileRequest,
    issuer_address: Annotated[str, Header()],
):
    """Upload file"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Decode Base64
    content_binary = base64.b64decode(data.content)

    # Create Upload File
    _upload_file = UploadFile()
    _upload_file.file_id = str(uuid.uuid4())
    _upload_file.issuer_address = issuer_address
    _upload_file.relation = data.relation
    _upload_file.file_name = data.file_name
    _upload_file.content = content_binary
    _upload_file.content_size = len(content_binary)
    _upload_file.description = data.description
    _upload_file.label = data.label
    db.add(_upload_file)
    await db.commit()

    resp = {
        "file_id": _upload_file.file_id,
        "issuer_address": _upload_file.issuer_address,
        "relation": _upload_file.relation,
        "file_name": _upload_file.file_name,
        "content_size": _upload_file.content_size,
        "description": _upload_file.description,
        "label": _upload_file.label,
        "created": utc_tz.localize(_upload_file.created)
        .astimezone(local_tz)
        .isoformat(),
    }

    return json_response(resp)


# GET: /files/{file_id}
@router.get(
    "/{file_id}",
    operation_id="DownloadFile",
    response_model=DownloadFileResponse,
    responses=get_routers_responses(404),
)
async def download_file(
    db: DBAsyncSession,
    file_id: Annotated[str, Path()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """Download file"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Upload File
    if issuer_address is None:
        _upload_file: UploadFile | None = (
            await db.scalars(
                select(UploadFile).where(UploadFile.file_id == file_id).limit(1)
            )
        ).first()
    else:
        _upload_file: UploadFile | None = (
            await db.scalars(
                select(UploadFile)
                .where(
                    and_(
                        UploadFile.file_id == file_id,
                        UploadFile.issuer_address == issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
    if _upload_file is None:
        raise HTTPException(status_code=404, detail="file not found")

    # Base64 Encode
    content = base64.b64encode(_upload_file.content).decode("utf-8")

    resp = {
        "file_id": _upload_file.file_id,
        "issuer_address": _upload_file.issuer_address,
        "relation": _upload_file.relation,
        "file_name": _upload_file.file_name,
        "content": content,
        "content_size": _upload_file.content_size,
        "description": _upload_file.description,
        "label": _upload_file.label,
    }

    return json_response(resp)


# DELETE: /files/{file_id}
@router.delete(
    "/{file_id}",
    operation_id="DeleteFile",
    response_model=None,
    responses=get_routers_responses(422, 404),
)
async def delete_file(
    db: DBAsyncSession,
    file_id: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
):
    """Delete file"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Upload File
    _upload_file = (
        await db.scalars(
            select(UploadFile)
            .where(
                and_(
                    UploadFile.file_id == file_id,
                    UploadFile.issuer_address == issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _upload_file is None:
        raise HTTPException(status_code=404, detail="file not found")

    # Delete Upload File
    await db.delete(_upload_file)
    await db.commit()

    return
