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

import uuid
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.model import ValidatedDatetimeStr
from app.model.db import TokenHolderBatchStatus
from app.model.schema.base import (
    BasePaginationQuery,
    ResultSet,
    SortOrder,
    ValueOperator,
)
from app.model.schema.personal_info import (
    PersonalInfo,
    PersonalInfoEventType,
    PersonalInfoHistory,
    PersonalInfoIndex,
)


############################
# REQUEST
############################
class ListTokenHoldersPersonalInfoSortItem(StrEnum):
    account_address = "account_address"
    created = "created"
    modified = "modified"


class ListTokenHoldersPersonalInfoQuery(BasePaginationQuery):
    account_address: Optional[str] = Field(None, description="Account address")
    created_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (From)"
    )
    created_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (To)"
    )
    modified_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="Modified datetime (From)"
    )
    modified_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="Modified datetime (To)"
    )

    sort_item: Optional[ListTokenHoldersPersonalInfoSortItem] = Field(
        ListTokenHoldersPersonalInfoSortItem.created, description="Sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


class ListTokenHoldersPersonalInfoHistoryQuery(BasePaginationQuery):
    account_address: Optional[str] = Field(None, description="Account address")
    event_type: Optional[PersonalInfoEventType] = Field(None, description="event type")
    block_timestamp_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="block timestamp datetime (From)"
    )
    block_timestamp_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="block timestamp datetime (To)"
    )
    created_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (From)"
    )
    created_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (To)"
    )

    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


class CreateTokenHoldersListRequest(BaseModel):
    """Create Token Holders List schema (REQUEST)"""

    list_id: str = Field(description="UUID v4 required")
    block_number: int = Field(ge=1)
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "list_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                    "block_number": 765,
                }
            ]
        }
    )

    @field_validator("list_id")
    @classmethod
    def list_id_is_uuid_v4(cls, v):
        try:
            _uuid = uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("list_id is not UUIDv4.")
        return v


class RetrieveTokenHoldersCollectionSortItem(StrEnum):
    account_address = "account_address"
    hold_balance = "hold_balance"
    locked_balance = "locked_balance"
    key_manager = "key_manager"
    holder_name = "tax_category"


class RetrieveTokenHoldersCollectionQuery(BasePaginationQuery):
    hold_balance: Optional[int] = Field(None, description="Hold balance")
    hold_balance_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="Search condition of hold balance(0:equal, 1:greater than or equal, 2:less than or equal）",
    )
    locked_balance: Optional[int] = Field(None, description="Locked balance")
    locked_balance_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="Search condition of locked balance(0:equal, 1:greater than or equal, 2:less than or equal）",
    )
    account_address: Optional[str] = Field(
        None, description="Account address(partial match)"
    )
    key_manager: Optional[str] = Field(None, description="Key manager(partial match)")
    tax_category: Optional[int] = Field(None, description="Tax category")

    sort_item: Optional[RetrieveTokenHoldersCollectionSortItem] = Field(
        RetrieveTokenHoldersCollectionSortItem.account_address, description="Sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


############################
# RESPONSE
############################
class ListTokenHoldersPersonalInfoResponse(BaseModel):
    """List All Token Holders PersonalInfo (Response)"""

    result_set: ResultSet
    personal_info: List[PersonalInfoIndex]


class ListTokenHoldersPersonalInfoHistoryResponse(BaseModel):
    """List All Token Holders PersonalInfo Histories (Response)"""

    result_set: ResultSet
    personal_info: List[PersonalInfoHistory]


class CreateTokenHoldersListResponse(BaseModel):
    """Create Token Holders List schema (RESPONSE)"""

    list_id: str = Field(description="UUID v4 required")
    status: TokenHolderBatchStatus
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "list_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                    "status": "pending",
                }
            ]
        }
    )


class RetrieveTokenHolderCollectionResponse(BaseModel):
    """Retrieve Token Holders Collection schema (RESPONSE)"""

    token_address: str
    block_number: int
    list_id: str = Field(description="UUID v4 required")
    status: TokenHolderBatchStatus


class ListAllTokenHolderCollectionsResponse(BaseModel):
    """List All Token Holders Collections schema (RESPONSE)"""

    result_set: ResultSet
    collections: List[RetrieveTokenHolderCollectionResponse]


class TokenHoldersCollectionHolder(BaseModel):
    account_address: str = Field(description="Account address of token holder.")
    hold_balance: int = Field(
        description="Amount of balance."
        "This includes balance/pending_transfer/exchange_balance/exchange_commitment."
    )
    locked_balance: int = Field(description="Amount of locked balance.")
    personal_information: PersonalInfo


class RetrieveTokenHoldersListResponse(BaseModel):
    """Retrieve Token Holders List schema (RESPONSE)"""

    result_set: ResultSet
    status: TokenHolderBatchStatus
    holders: List[TokenHoldersCollectionHolder]
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "done",
                    "holders": [
                        {
                            "account_address": "0x85a8b8887a4bD76859751b10C8aC8EC5f3aA1bDB",
                            "hold_balance": 30000,
                            "locked_balance": 0,
                        }
                    ],
                }
            ]
        }
    )
