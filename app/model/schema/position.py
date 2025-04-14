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

from enum import StrEnum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, PositiveInt, RootModel

from app.model import EthereumAddress

from .base import (
    BasePaginationQuery,
    IbetShare,
    IbetStraightBond,
    ResultSet,
    SortOrder,
    TokenType,
)


############################
# COMMON
############################
class Position(BaseModel):
    """Position"""

    issuer_address: str = Field(description="Issuer address")
    token_address: str = Field(description="Token address")
    token_type: TokenType = Field(description="Token type")
    token_name: str = Field(description="Token name")
    token_attributes: Optional[Union[IbetStraightBond, IbetShare]] = Field(
        description="Token attributes"
    )
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


class LockEventCategory(StrEnum):
    Lock = "Lock"
    Unlock = "Unlock"


class LockMessage(StrEnum):
    garnishment = "garnishment"
    inheritance = "inheritance"
    force_lock = "force_lock"


class LockDataMessage(BaseModel):
    message: LockMessage


class UnlockMessage(StrEnum):
    garnishment = "garnishment"
    inheritance = "inheritance"
    force_unlock = "force_unlock"


class UnlockDataMessage(BaseModel):
    message: UnlockMessage


class LockEvent(BaseModel):
    """Lock/Unlock event"""

    category: LockEventCategory = Field(description="Event category")
    is_forced: bool = Field(description="Set to `True` for force lock/unlock events")
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
    data: LockDataMessage | UnlockDataMessage | dict = Field(
        description="Message at lock/unlock"
    )
    block_timestamp: str = Field(
        description="block_timestamp when Lock log was emitted"
    )


############################
# REQUEST
############################
class ListAllPositionsQuery(BasePaginationQuery):
    include_former_position: bool = Field(
        False,
        description="Whether to include positions that were held in the past but currently have a zero balance.",
    )
    include_token_attributes: bool = Field(
        False,
        description="Whether to include token attribute information in the response.",
    )
    token_type: Optional[TokenType] = Field(None, description="Token type")


class ListAllLockedPositionsQuery(BasePaginationQuery):
    token_type: Optional[TokenType] = Field(None, description="Token type")


class ListAllLockEventsSortItem(StrEnum):
    token_address = "token_address"
    lock_address = "lock_address"
    recipient_address = "recipient_address"
    value = "value"
    block_timestamp = "block_timestamp"


class ListAllLockEventsQuery(BasePaginationQuery):
    token_address: Optional[str] = Field(None, description="Token address")
    token_type: Optional[TokenType] = Field(None, description="Token type")
    msg_sender: Optional[str] = Field(None, description="Msg sender")
    lock_address: Optional[str] = Field(None, description="Lock address")
    recipient_address: Optional[str] = Field(None, description="Recipient address")
    category: Optional[LockEventCategory] = Field(None, description="Event category")

    sort_item: Optional[ListAllLockEventsSortItem] = Field(
        ListAllLockEventsSortItem.block_timestamp, description="Sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class ForceLockRequest(BaseModel):
    token_address: EthereumAddress = Field(..., description="Token address")
    lock_address: EthereumAddress = Field(..., description="Lock address")
    message: Optional[LockMessage] = Field(
        LockMessage.force_lock, description="Lock message"
    )
    value: PositiveInt = Field(..., description="Lock amount")


class ForceUnlockRequest(BaseModel):
    token_address: EthereumAddress = Field(..., description="Token address")
    lock_address: EthereumAddress = Field(..., description="Lock address")
    recipient_address: EthereumAddress = Field(..., description="Recipient address")
    message: Optional[UnlockMessage] = Field(
        UnlockMessage.force_unlock, description="Unlock message"
    )
    value: PositiveInt = Field(..., description="Unlock amount")


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
