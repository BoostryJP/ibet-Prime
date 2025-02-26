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
from typing import Optional

from pydantic import BaseModel, Field

from app.model.schema.base import ResultSet

from .personal_info import PersonalInfo


############################
# COMMON
############################
class HolderExtraInfo(BaseModel):
    external_id1_type: Optional[str] = Field(
        ..., description="The type of external-id1"
    )
    external_id1: Optional[str] = Field(..., description="external-id1")
    external_id2_type: Optional[str] = Field(
        ..., description="The type of external-id2"
    )
    external_id2: Optional[str] = Field(..., description="external-id2")
    external_id3_type: Optional[str] = Field(
        ..., description="The type of external-id3"
    )
    external_id3: Optional[str] = Field(..., description="external-id3")


############################
# REQUEST
############################
class RegisterHolderExtraInfoRequest(BaseModel):
    """Schema for holder's extra information registration (REQUEST)"""

    external_id1_type: Optional[str] = Field(
        None, description="The type of external-id1", max_length=50
    )
    external_id1: Optional[str] = Field(None, description="external-id1", max_length=50)
    external_id2_type: Optional[str] = Field(
        None, description="The type of external-id2", max_length=50
    )
    external_id2: Optional[str] = Field(None, description="external-id2", max_length=50)
    external_id3_type: Optional[str] = Field(
        None, description="The type of external-id3", max_length=50
    )
    external_id3: Optional[str] = Field(None, description="external-id3", max_length=50)


############################
# RESPONSE
############################
class HolderResponse(BaseModel):
    """Holder schema (Response)"""

    account_address: str = Field(..., description="Holder's account address")
    personal_information: PersonalInfo = Field(
        ..., description="Holder's personal information"
    )
    holder_extra_info: HolderExtraInfo = Field(
        ..., description="Holder's extra information"
    )
    balance: int
    exchange_balance: int
    exchange_commitment: int
    pending_transfer: int
    locked: int
    modified: Optional[datetime]


class HoldersResponse(BaseModel):
    """Holders schema (Response)"""

    result_set: ResultSet
    holders: list[HolderResponse]


class HolderCountResponse(BaseModel):
    """Holder count schema (Response)"""

    count: int
