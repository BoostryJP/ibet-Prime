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
from datetime import datetime
from typing import (
    Optional,
    List,
    Dict,
    Any
)

from pydantic import (
    BaseModel,
    validator,
    Field
)

from config import MAX_UPLOAD_FILE_SIZE
from .types import ResultSet


############################
# REQUEST
############################

class UploadFileRequest(BaseModel):
    """Upload File schema (Request)"""
    relation: Optional[str] = Field(None, max_length=50)
    file_name: str = Field(..., max_length=256)
    content: str
    description: Optional[str] = Field(None, max_length=1000)
    label: Optional[str] = Field(None, max_length=200)

    @validator("content")
    def content_is_less_than_max_upload_file_size(cls, v):
        try:
            data = base64.b64decode(v)
        except Exception:
            raise ValueError("content is not a Base64-encoded string")
        if len(data) >= MAX_UPLOAD_FILE_SIZE:
            raise ValueError(
                f"file size(Base64-decoded size) must be less than or equal to {MAX_UPLOAD_FILE_SIZE}")
        return v

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["content"]
            notice_code_schema["description"] = "Base64-encoded content.\n" \
                                                f"Max length of binary data before encoding is {MAX_UPLOAD_FILE_SIZE}."


############################
# RESPONSE
############################

class FileResponse(BaseModel):
    """File schema (Response)"""
    file_id: str
    issuer_address: str
    relation: Optional[str]
    file_name: str
    content_size: int
    description: Optional[str]
    label: str
    created: datetime


class ListAllFilesResponse(BaseModel):
    """List All Files schema (Response)"""
    result_set: ResultSet
    files: List[FileResponse]


class DownloadFileResponse(BaseModel):
    """Download File schema (Response)"""
    file_id: str
    issuer_address: str
    relation: Optional[str]
    file_name: str
    content: str
    content_size: int
    description: Optional[str]
    label: str

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["content"]
            notice_code_schema["description"] = "Base64-encoded content"
