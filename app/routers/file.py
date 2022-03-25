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
from typing import Optional
import pytz

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query
)
from fastapi.exceptions import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import TZ
from app.database import db_session
from app.model.db import UploadFile
from app.model.schema import (
    UploadFileRequest,
    ListAllFilesResponse,
    DownloadFileResponse
)
from app.utils.check_utils import (
    validate_headers,
    address_is_valid_address
)
from app.utils.docs_utils import get_routers_responses
from app import log

LOG = log.get_logger()

router = APIRouter(tags=["file"])

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /files
@router.get(
    "/files",
    response_model=ListAllFilesResponse,
    responses=get_routers_responses(422)
)
def list_all_upload_files(
        issuer_address: Optional[str] = Header(None),
        relation: Optional[str] = Query(None),
        file_name: Optional[str] = Query(None, description="partial match"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)):
    """List all files"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    query = db.query(UploadFile). \
        order_by(desc(UploadFile.modified))
    total = query.count()

    # Search Filter
    if issuer_address is not None:
        query = query.filter(UploadFile.issuer_address == issuer_address)
    if relation is not None:
        query = query.filter(UploadFile.relation == relation)
    if file_name is not None:
        query = query.filter(UploadFile.file_name.like("%" + file_name + "%"))
    count = query.count()

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _upload_file_list = query.all()

    files = []
    for _upload_file in _upload_file_list:
        created_formatted = utc_tz.localize(_upload_file.created).astimezone(local_tz).isoformat()
        files.append({
            "file_id": _upload_file.file_id,
            "issuer_address": _upload_file.issuer_address,
            "relation": _upload_file.relation,
            "file_name": _upload_file.file_name,
            "content_size": _upload_file.content_size,
            "description": _upload_file.description,
            "created": created_formatted,
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "files": files
    }

    return resp


# POST: /files
@router.post(
    "/files",
    response_model=None,
    responses=get_routers_responses(422)
)
def upload_file(
        data: UploadFileRequest,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
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
    db.add(_upload_file)

    db.commit()
    return


# GET: /files/{file_id}
@router.get(
    "/files/{file_id}",
    response_model=DownloadFileResponse,
    responses=get_routers_responses(404)
)
def download_file(
        file_id: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Download file"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Upload File
    if issuer_address is None:
        _upload_file = db.query(UploadFile). \
            filter(UploadFile.file_id == file_id). \
            first()
    else:
        _upload_file = db.query(UploadFile). \
            filter(UploadFile.file_id == file_id). \
            filter(UploadFile.issuer_address == issuer_address). \
            first()
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
    }

    return resp


# DELETE: /files/{file_id}
@router.delete(
    "/files/{file_id}",
    response_model=None,
    responses=get_routers_responses(422, 404)
)
def delete_file(
        file_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Delete file"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Upload File
    _upload_file = db.query(UploadFile). \
        filter(UploadFile.file_id == file_id). \
        filter(UploadFile.issuer_address == issuer_address). \
        first()
    if _upload_file is None:
        raise HTTPException(status_code=404, detail="file not found")

    # Delete Upload File
    db.delete(_upload_file)

    db.commit()
    return
