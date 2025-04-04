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
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.model import EthereumAddress
from app.model.db import BatchRegisterPersonalInfoUploadStatus

from .base import BasePaginationQuery, ResultSet, SortOrder


############################
# COMMON
############################
class PersonalInfoEventType(StrEnum):
    REGISTER = "register"
    MODIFY = "modify"


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

    account_address: str = Field(...)
    personal_info: PersonalInfo = Field(...)
    created: datetime
    modified: datetime


class PersonalInfoHistory(BaseModel):
    """Personal Information History schema"""

    id: int = Field(...)
    account_address: str = Field(...)
    event_type: PersonalInfoEventType = Field(...)
    personal_info: PersonalInfo = Field(...)
    block_timestamp: datetime = Field(...)
    created: datetime


class PersonalInfoDataSource(StrEnum):
    """Personal information data source"""

    ON_CHAIN = "on-chain"
    OFF_CHAIN = "off-chain"


############################
# REQUEST
############################
class RegisterPersonalInfoRequest(PersonalInfoInput):
    """Register Personal Information schema (REQUEST)"""

    account_address: EthereumAddress
    key_manager: str
    data_source: PersonalInfoDataSource = Field(
        PersonalInfoDataSource.ON_CHAIN, description=PersonalInfoDataSource.__doc__
    )


class ListAllPersonalInfoBatchRegistrationUploadQuery(BasePaginationQuery):
    status: Optional[str] = Field(None)
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


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
