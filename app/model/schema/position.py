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
from enum import Enum
from typing import Annotated, List, Optional

from fastapi import Query
from pydantic import BaseModel, Field, PositiveInt, RootModel, field_validator
from pydantic.dataclasses import dataclass
from web3 import Web3

from app.model.db import TokenType
from app.model.schema.base import ResultSet, SortOrder

############################
# COMMON
############################


class Position(BaseModel):
    """Position"""

    issuer_address: str = Field(description="Issuer address")
    token_address: str = Field(description="Token address")
    token_type: TokenType = Field(description="Token type")
    token_name: str = Field(description="Token name")
    balance: int = Field(description="Balance")
    exchange_balance: int = Field(description="Balance on the exchange contract")
    exchange_commitment: int = Field(description="Commitment on the exchange contract")
    pending_transfer: int = Field(description="Pending transfer amount")
    locked: int = Field(description="Total locked amount")


class LockedPosition(BaseModel):
    """Locked Position"""

    issuer_address: str = Field(description="Issuer address")
    token_address: str = Field(description="Token address")
    token_type: TokenType = Field(description="Token type")
    token_name: str = Field(description="Token name")
    lock_address: str = Field(description="Lock address")
    locked: int = Field(description="Locked amount")


class LockEventCategory(str, Enum):
    Lock = "Lock"
    Unlock = "Unlock"


class LockEvent(BaseModel):
    category: LockEventCategory = Field(description="Event category")
    transaction_hash: str = Field(description="Transaction hash")
    msg_sender: Optional[str] = Field(default=None, description="Message sender")
    issuer_address: str = Field(description="Issuer address")
    token_address: str = Field(description="Token address")
    token_type: TokenType = Field(description="Token type")
    token_name: str = Field(description="Token name")
    lock_address: str = Field(description="Lock address")
    account_address: str = Field(description="Account address")
    recipient_address: Optional[str] = Field(
        default=None, description="Recipient address"
    )
    value: int = Field(description="Lock/Unlock amount")
    data: dict = Field(description="Message at lock/unlock")
    block_timestamp: str = Field(
        description="block_timestamp when Lock log was emitted"
    )


############################
# REQUEST
############################


class ListAllLockEventsSortItem(str, Enum):
    token_address = "token_address"
    lock_address = "lock_address"
    recipient_address = "recipient_address"
    value = "value"
    block_timestamp = "block_timestamp"


@dataclass
class ListAllLockEventsQuery:
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None

    token_address: Annotated[Optional[str], Query(description="Token address")] = None
    token_type: Annotated[Optional[TokenType], Query(description="Token type")] = None
    msg_sender: Annotated[Optional[str], Query(description="Msg sender")] = None
    lock_address: Annotated[Optional[str], Query(description="Lock address")] = None
    recipient_address: Annotated[
        Optional[str], Query(description="Recipient address")
    ] = None
    category: Annotated[
        Optional[LockEventCategory], Query(description="Event category")
    ] = None

    sort_item: Annotated[
        ListAllLockEventsSortItem, Query(description="Sort item")
    ] = ListAllLockEventsSortItem.block_timestamp
    sort_order: Annotated[
        SortOrder, Query(description="Sort order(0: ASC, 1: DESC)")
    ] = SortOrder.DESC


class ForceUnlockRequest(BaseModel):
    token_address: str = Field(..., description="Token address")
    lock_address: str = Field(..., description="Lock address")
    recipient_address: str = Field(..., description="Recipient address")
    value: PositiveInt = Field(..., description="Unlock amount")

    @field_validator("token_address")
    @classmethod
    def token_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("token_address is not a valid address")
        return v

    @field_validator("lock_address")
    @classmethod
    def lock_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("lock_address is not a valid address")
        return v

    @field_validator("recipient_address")
    @classmethod
    def recipient_address_is_valid_address(cls, v):
        if not Web3.is_address(v):
            raise ValueError("recipient_address is not a valid address")
        return v


############################
# RESPONSE
############################


class PositionResponse(RootModel[Position]):
    """Position schema (Response)"""

    pass


class ListAllPositionResponse(BaseModel):
    """List All Position schema (Response)"""

    result_set: ResultSet
    positions: List[Position] = Field(description="Position list")


class ListAllLockedPositionResponse(BaseModel):
    """List All Locked Position schema (Response)"""

    result_set: ResultSet
    locked_positions: List[LockedPosition] = Field(description="Locked position list")


class ListAllLockEventsResponse(BaseModel):
    """List All Lock/Unlock events (Response)"""

    result_set: ResultSet
    events: List[LockEvent] = Field(description="Lock/Unlock event list")
