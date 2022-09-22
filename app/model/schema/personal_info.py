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
from typing import Optional, List
from pydantic import (
    BaseModel,
    validator,
    Field
)
from web3 import Web3

from app.model.db import BatchRegisterPersonalInfoUploadStatus
from app.model.schema.types import ResultSet


class PersonalInfo(BaseModel):
    """Personal Information schema"""
    name: Optional[str]
    postal_code: Optional[str]
    address: Optional[str]
    email: Optional[str]
    birth: Optional[str]
    is_corporate: Optional[bool]
    tax_category: Optional[int]


############################
# REQUEST
############################
class ModifyPersonalInfoRequest(PersonalInfo):
    """Modify Personal Information schema (REQUEST)"""
    key_manager: str


class RegisterPersonalInfoRequest(PersonalInfo):
    """Register Personal Information schema (REQUEST)"""
    account_address: str
    key_manager: str

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v


############################
# RESPONSE
############################


class BatchRegisterPersonalInfoUploadResponse(BaseModel):
    """Batch Register PersonalInfo schema (RESPONSE)"""

    batch_id: str = Field(description="UUID v4 required")
    status: BatchRegisterPersonalInfoUploadStatus
    created: str

    class Config:
        schema_extra = {
            "example": {
                "batch_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                "status": "pending",
                "created": "2022-09-02T19:49:33.370874+09:00"
            }
        }


class ListBatchRegisterPersonalInfoUploadResponse(BaseModel):
    """List All Batch Register PersonalInfo Upload (Response)"""
    result_set: ResultSet
    uploads: List[BatchRegisterPersonalInfoUploadResponse]


class BatchRegisterPersonalInfoResult(BaseModel):
    """Result of Creating Batch Register PersonalInfo schema (RESPONSE)"""
    status: int  # (pending:0, succeeded:1, failed:2)

    account_address: str
    key_manager: str
    name: Optional[str]
    postal_code: Optional[str]
    address: Optional[str]
    email: Optional[str]
    birth: Optional[str]
    is_corporate: Optional[bool]
    tax_category: Optional[int]


class GetBatchRegisterPersonalInfoResponse(BaseModel):
    """Get Batch Register PersonalInfo schema (RESPONSE)"""

    status: BatchRegisterPersonalInfoUploadStatus
    results: List[BatchRegisterPersonalInfoResult]
