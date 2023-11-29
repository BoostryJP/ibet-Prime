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
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.dataclasses import dataclass
from web3 import Web3

from app.model.db import BatchRegisterPersonalInfoUploadStatus
from app.model.schema.base import ResultSet, SortOrder


class PersonalInfo(BaseModel):
    key_manager: Optional[str] = Field(...)
    name: Optional[str] = Field(...)
    postal_code: Optional[str] = Field(...)
    address: Optional[str] = Field(...)
    email: Optional[str] = Field(...)
    birth: Optional[str] = Field(...)
    is_corporate: Optional[bool] = Field(...)
    tax_category: Optional[int] = Field(...)


class PersonalInfoInput(BaseModel):
    """Personal Information Input schema"""

    name: Optional[str] = None
    postal_code: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    birth: Optional[str] = None
    is_corporate: Optional[bool] = None
    tax_category: Optional[int] = None


class PersonalInfoIndex(BaseModel):
    """Personal Information Index schema"""

    id: int = Field(...)
    account_address: str = Field(...)
    personal_info: PersonalInfo = Field(...)
    created: datetime


############################
# REQUEST
############################
class RegisterPersonalInfoRequest(PersonalInfoInput):
    """Register Personal Information schema (REQUEST)"""

    account_address: str
    key_manager: str

    @field_validator("account_address")
    @classmethod
    def account_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("account_address is not a valid address")
        return v


@dataclass
class ListAllPersonalInfoBatchRegistrationUploadQuery:
    status: Annotated[Optional[str], Query()] = None
    sort_order: Annotated[
        SortOrder, Query(description="0:asc, 1:desc")
    ] = SortOrder.DESC
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


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
