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
from typing import Annotated, List, Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, field_validator
from pydantic.dataclasses import dataclass

from app.model import ValidatedDatetimeStr
from app.model.db import TokenHolderBatchStatus
from app.model.schema.base import ResultSet, SortOrder, ValueOperator
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


@dataclass
class ListTokenHoldersPersonalInfoQuery:
    account_address: Annotated[Optional[str], Query(description="account address")] = (
        None
    )
    created_from: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="created datetime (From)")
    ] = None
    created_to: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="created datetime (To)")
    ] = None
    modified_from: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="modified datetime (From)")
    ] = None
    modified_to: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="modified datetime (To)")
    ] = None

    sort_item: Annotated[
        ListTokenHoldersPersonalInfoSortItem, Query(description="sort item")
    ] = ListTokenHoldersPersonalInfoSortItem.created
    sort_order: Annotated[
        Optional[SortOrder], Query(description="sort order(0: ASC, 1: DESC)")
    ] = SortOrder.ASC

    offset: Annotated[Optional[NonNegativeInt], Query(description="start position")] = (
        None
    )
    limit: Annotated[Optional[NonNegativeInt], Query(description="number of set")] = (
        None
    )


@dataclass
class ListTokenHoldersPersonalInfoHistoryQuery:
    account_address: Annotated[Optional[str], Query(description="account address")] = (
        None
    )
    event_type: Annotated[
        Optional[PersonalInfoEventType], Query(description="event type")
    ] = None
    block_timestamp_from: Annotated[
        Optional[ValidatedDatetimeStr],
        Query(description="block timestamp datetime (From)"),
    ] = None
    block_timestamp_to: Annotated[
        Optional[ValidatedDatetimeStr],
        Query(description="block timestamp datetime (To)"),
    ] = None
    created_from: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="created datetime (From)")
    ] = None
    created_to: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="created datetime (To)")
    ] = None

    sort_order: Annotated[
        Optional[SortOrder], Query(description="sort order (0: ASC, 1: DESC)")
    ] = SortOrder.ASC

    offset: Annotated[Optional[NonNegativeInt], Query(description="start position")] = (
        None
    )
    limit: Annotated[Optional[NonNegativeInt], Query(description="number of set")] = (
        None
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


@dataclass
class RetrieveTokenHoldersCollectionQuery:
    hold_balance: Annotated[
        Optional[int], Query(description="number of hold balance")
    ] = None
    hold_balance_operator: Annotated[
        Optional[ValueOperator],
        Query(
            description="search condition of hold balance(0:equal, 1:greater than or equal, 2:less than or equal）",
        ),
    ] = ValueOperator.EQUAL
    locked_balance: Annotated[
        Optional[int], Query(description="number of locked balance")
    ] = None
    locked_balance_operator: Annotated[
        Optional[ValueOperator],
        Query(
            description="search condition of locked balance(0:equal, 1:greater than or equal, 2:less than or equal）",
        ),
    ] = ValueOperator.EQUAL
    account_address: Annotated[
        Optional[str], Query(description="account address(partial match)")
    ] = None
    key_manager: Annotated[
        Optional[str], Query(description="key manager(partial match)")
    ] = None
    tax_category: Annotated[Optional[int], Query(description="tax category")] = None
    sort_item: Annotated[
        RetrieveTokenHoldersCollectionSortItem, Query(description="Sort Item")
    ] = RetrieveTokenHoldersCollectionSortItem.account_address
    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = SortOrder.ASC
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


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
