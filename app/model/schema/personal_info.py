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
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from web3 import Web3

from app.model.db import BatchRegisterPersonalInfoUploadStatus
from app.model.schema.types import ResultSet


class PersonalInfo(BaseModel):
    """Personal Information schema"""

    name: Optional[str] = None
    postal_code: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    birth: Optional[str] = None
    is_corporate: Optional[bool] = None
    tax_category: Optional[int] = None


############################
# REQUEST
############################


class RegisterPersonalInfoRequest(PersonalInfo):
    """Register Personal Information schema (REQUEST)"""

    account_address: str
    key_manager: str

    @field_validator("account_address")
    @classmethod
    def account_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "batch_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                    "status": "pending",
                    "created": "2022-09-02T19:49:33.370874+09:00",
                }
            ]
        }
    )


class ListBatchRegisterPersonalInfoUploadResponse(BaseModel):
    """List All Batch Register PersonalInfo Upload (Response)"""

    result_set: ResultSet
    uploads: List[BatchRegisterPersonalInfoUploadResponse]


class BatchRegisterPersonalInfoResult(BaseModel):
    """Result of Creating Batch Register PersonalInfo schema (RESPONSE)"""

    status: int  # (pending:0, succeeded:1, failed:2)

    account_address: str
    key_manager: str
    name: Optional[str] = Field(...)
    postal_code: Optional[str] = Field(...)
    address: Optional[str] = Field(...)
    email: Optional[str] = Field(...)
    birth: Optional[str] = Field(...)
    is_corporate: Optional[bool] = Field(...)
    tax_category: Optional[int] = Field(...)


class GetBatchRegisterPersonalInfoResponse(BaseModel):
    """Get Batch Register PersonalInfo schema (RESPONSE)"""

    status: BatchRegisterPersonalInfoUploadStatus
    results: List[BatchRegisterPersonalInfoResult]
