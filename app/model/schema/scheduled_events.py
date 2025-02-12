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
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, RootModel

from app.model.db.scheduled_events import ScheduledEventStatus, ScheduledEventType

from .. import EthereumAddress
from .base import (
    BasePaginationQuery,
    IbetShare,
    IbetStraightBond,
    ResultSet,
    SortOrder,
    TokenType,
)
from .token import IbetShareUpdate, IbetStraightBondUpdate


############################
# COMMON
############################
class ScheduledEvent(BaseModel):
    """Scheduled event"""

    scheduled_event_id: str
    token_address: str
    token_type: TokenType
    scheduled_datetime: datetime
    event_type: ScheduledEventType
    status: ScheduledEventStatus
    data: Dict[str, Any]
    created: str


class ScheduledEventWithTokenAttributes(ScheduledEvent):
    """Scheduled event with token attributes"""

    token_attributes: IbetStraightBond | IbetShare = Field(
        description="Token attributes"
    )


############################
# REQUEST
############################
class IbetStraightBondScheduledUpdate(BaseModel):
    """scheduled event (Request)"""

    scheduled_datetime: datetime
    event_type: ScheduledEventType = Field(...)
    data: IbetStraightBondUpdate


class IbetShareScheduledUpdate(BaseModel):
    """scheduled event (Request)"""

    scheduled_datetime: datetime
    event_type: ScheduledEventType = Field(...)
    data: IbetShareUpdate


class ListAllScheduledEventsSortItem(StrEnum):
    CREATED = "created"
    SCHEDULED_DATETIME = "scheduled_datetime"
    TOKEN_ADDRESS = "token_address"


class ListAllScheduledEventsQuery(BasePaginationQuery):
    """ListAllScheduledEvents query parameters"""

    token_type: Optional[TokenType] = Field(None, description="Token type")
    token_address: Optional[EthereumAddress] = Field(None, description="Token address")
    status: Optional[ScheduledEventStatus] = Field(
        None, description="Scheduled event processing status"
    )

    sort_item: Optional[ListAllScheduledEventsSortItem] = Field(
        ListAllScheduledEventsSortItem.CREATED
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


############################
# RESPONSE
############################
class ScheduledEventIdResponse(BaseModel):
    """scheduled event (Response)"""

    scheduled_event_id: str


class ScheduledEventIdListResponse(BaseModel):
    """scheduled event list (Response)"""

    scheduled_event_id_list: list[str]


class ScheduledEventResponse(RootModel[ScheduledEvent]):
    """scheduled event (Response)"""

    pass


class ListAllScheduledEventsResponse(BaseModel):
    """List scheduled events schema"""

    result_set: ResultSet
    scheduled_events: list[ScheduledEventWithTokenAttributes]
