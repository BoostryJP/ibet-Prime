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
from enum import IntEnum, StrEnum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.model.schema.base import (
    BasePaginationQuery,
    ResultSet,
    SortOrder,
    ValueOperator,
)

from .personal_info import PersonalInfo

############################
# COMMON
############################


class TransferSourceEventType(StrEnum):
    Transfer = "Transfer"
    Unlock = "Unlock"


class TransferApprovalStatus(IntEnum):
    UNAPPROVED = 0
    ESCROW_FINISHED = 1
    TRANSFERRED = 2
    CANCELED = 3


class TransferBase(BaseModel):
    """transfer data base"""

    transaction_hash: str
    token_address: str
    from_address: str
    from_address_personal_information: Optional[PersonalInfo] = Field(...)
    to_address: str
    to_address_personal_information: Optional[PersonalInfo] = Field(...)
    amount: int
    block_timestamp: str


class Transfer(TransferBase):
    source_event: Literal[TransferSourceEventType.Transfer] = Field(
        description="Source Event"
    )
    data: None = Field(description="Event data")


class DataMessage(BaseModel):
    message: Literal[
        "garnishment",
        "inheritance",
        "force_unlock",
    ]


class UnlockTransfer(TransferBase):
    source_event: Literal[TransferSourceEventType.Unlock] = Field(
        description="Source Event"
    )
    data: DataMessage | dict = Field(description="Event data")


############################
# REQUEST
############################


class ListTransferHistorySortItem(StrEnum):
    BLOCK_TIMESTAMP = "block_timestamp"
    FROM_ADDRESS = "from_address"
    TO_ADDRESS = "to_address"
    FROM_ADDRESS_NAME = "from_address_name"
    TO_ADDRESS_NAME = "to_address_name"
    AMOUNT = "amount"


class ListTransferHistoryQuery(BasePaginationQuery):
    block_timestamp_from: Optional[datetime] = Field(
        None, description="Block timestamp (From)"
    )
    block_timestamp_to: Optional[datetime] = Field(
        None, description="Block timestamp (To)"
    )
    from_address: Optional[str] = Field(None, description="Transfer source address")
    to_address: Optional[str] = Field(None, description="Transfer destination address")
    from_address_name: Optional[str] = Field(
        None, description="Name of transfer source address"
    )
    to_address_name: Optional[str] = Field(
        None, description="Name of transfer destination address"
    )
    amount: Optional[int] = Field(None, description="Transfer amount")
    amount_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="Value filter condition(0: equal, 1: greater than, 2: less than)",
    )
    source_event: Optional[TransferSourceEventType] = Field(
        None, description="Source event of transfer"
    )
    data: Optional[str] = Field(None, description="source event data")
    message: Optional[
        Literal["garnishment"] | Literal["inheritance"] | Literal["force_unlock"]
    ] = Field(None, description="message field in source event data")

    sort_item: Optional[ListTransferHistorySortItem] = Field(
        ListTransferHistorySortItem.BLOCK_TIMESTAMP, description="Sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class UpdateTransferApprovalOperationType(StrEnum):
    APPROVE = "approve"
    CANCEL = "cancel"


class UpdateTransferApprovalRequest(BaseModel):
    """Update Transfer Approval schema (Request)"""

    operation_type: UpdateTransferApprovalOperationType = Field(...)


class ListTransferApprovalHistorySortItem(StrEnum):
    ID = "id"
    EXCHANGE_ADDRESS = "exchange_address"
    APPLICATION_ID = "application_id"
    FROM_ADDRESS = "from_address"
    TO_ADDRESS = "to_address"
    AMOUNT = "amount"
    APPLICATION_DATETIME = "application_datetime"
    APPROVAL_DATETIME = "approval_datetime"
    STATUS = "status"


class ListTransferApprovalHistoryQuery(BasePaginationQuery):
    pass


class ListSpecificTokenTransferApprovalHistoryQuery(BasePaginationQuery):
    from_address: Optional[str] = Field(None, description="Transfer from")
    to_address: Optional[str] = Field(None, description="Transfer to")
    status: Optional[List[TransferApprovalStatus]] = Field(
        None, description="0:unapproved, 1:escrow_finished, 2:transferred, 3:canceled"
    )

    sort_item: Optional[ListTransferApprovalHistorySortItem] = Field(
        ListTransferApprovalHistorySortItem.ID
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


############################
# RESPONSE
############################


class TransferHistoryResponse(BaseModel):
    """transfer history"""

    result_set: ResultSet
    transfer_history: List[Transfer | UnlockTransfer]


class TransferApprovalResponse(BaseModel):
    """transfer approval data"""

    issuer_address: str
    token_address: str
    application_count: int
    unapproved_count: int
    escrow_finished_count: int
    transferred_count: int
    canceled_count: int


class TransferApprovalsResponse(BaseModel):
    """transfer approvals"""

    result_set: ResultSet
    transfer_approvals: List[TransferApprovalResponse]


class TransferApprovalTokenResponse(BaseModel):
    """transfer approval token data"""

    id: int
    token_address: str
    exchange_address: str
    application_id: int
    from_address: str
    from_address_personal_information: Optional[PersonalInfo] = Field(...)
    to_address: str
    to_address_personal_information: Optional[PersonalInfo] = Field(...)
    amount: int
    application_datetime: str
    application_blocktimestamp: str
    approval_datetime: Optional[str] = Field(...)
    approval_blocktimestamp: Optional[str] = Field(...)
    cancellation_blocktimestamp: Optional[str] = Field(...)
    cancelled: bool
    escrow_finished: bool
    transfer_approved: bool
    status: int
    issuer_cancelable: bool


class TransferApprovalTokenDetailResponse(BaseModel):
    """transfer approval token data"""

    id: int
    token_address: str
    exchange_address: str
    application_id: int
    from_address: str
    from_address_personal_information: Optional[PersonalInfo] = Field(...)
    to_address: str
    to_address_personal_information: Optional[PersonalInfo] = Field(...)
    amount: int
    application_datetime: str
    application_blocktimestamp: str
    approval_datetime: Optional[str] = Field(...)
    approval_blocktimestamp: Optional[str] = Field(...)
    cancellation_blocktimestamp: Optional[str] = Field(...)
    cancelled: bool
    escrow_finished: bool
    transfer_approved: bool
    status: int
    issuer_cancelable: bool


class TransferApprovalHistoryResponse(BaseModel):
    """transfer approval token history"""

    result_set: ResultSet
    transfer_approval_history: List[TransferApprovalTokenResponse]
