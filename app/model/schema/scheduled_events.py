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
from typing import Any, Dict

from pydantic import BaseModel, Field

from app.model.db.scheduled_events import ScheduledEventType

from .base import TokenType
from .token import IbetShareUpdate, IbetStraightBondUpdate


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


############################
# RESPONSE
############################
class ScheduledEventIdResponse(BaseModel):
    """scheduled event (Response)"""

    scheduled_event_id: str


class ScheduledEventResponse(BaseModel):
    """scheduled event (Response)"""

    scheduled_event_id: str
    token_address: str
    token_type: TokenType
    scheduled_datetime: datetime
    event_type: ScheduledEventType
    status: int
    data: Dict[str, Any]
    created: str
