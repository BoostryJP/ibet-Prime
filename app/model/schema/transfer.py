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
from pydantic import BaseModel, Field, NonNegativeInt
from pydantic.dataclasses import dataclass

from .types import ResultSet

############################
# COMMON
############################


class TransferSourceEventType(str, Enum):
    Transfer = "Transfer"
    Unlock = "Unlock"


############################
# REQUEST
############################


class ListTransferHistorySortItem(str, Enum):
    BLOCK_TIMESTAMP = "block_timestamp"
    FROM_ADDRESS = "from_address"
    TO_ADDRESS = "to_address"
    AMOUNT = "amount"


@dataclass
class ListTransferHistoryQuery:
    source_event: Annotated[
        Optional[TransferSourceEventType], Query(description="source event of transfer")
    ] = None
    data: Annotated[Optional[str], Query(description="source event data")] = None

    sort_item: Annotated[
        ListTransferHistorySortItem, Query(description="sort item")
    ] = ListTransferHistorySortItem.BLOCK_TIMESTAMP
    sort_order: Annotated[int, Query(ge=0, le=1, description="0:asc, 1:desc")] = 1
    offset: Annotated[
        Optional[NonNegativeInt], Query(description="start position")
    ] = None
    limit: Annotated[
        Optional[NonNegativeInt], Query(description="number of set")
    ] = None


class UpdateTransferApprovalOperationType(str, Enum):
    APPROVE = "approve"
    CANCEL = "cancel"


class UpdateTransferApprovalRequest(BaseModel):
    """Update Transfer Approval schema (Request)"""

    operation_type: UpdateTransferApprovalOperationType = Field(...)


############################
# RESPONSE
############################


class TransferResponse(BaseModel):
    """transfer data"""

    transaction_hash: str
    token_address: str
    from_address: str
    to_address: str
    amount: int
    source_event: TransferSourceEventType = Field(description="Source Event")
    data: dict | None = Field(description="Event data")
    block_timestamp: str


class TransferHistoryResponse(BaseModel):
    """transfer history"""

    result_set: ResultSet
    transfer_history: List[TransferResponse]


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
    from_address_personal_information: Optional[dict] = Field(...)
    to_address: str
    to_address_personal_information: Optional[dict] = Field(...)
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
