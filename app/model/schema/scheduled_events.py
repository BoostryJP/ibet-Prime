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
from typing import (
    Dict,
    Any
)

from pydantic import (
    BaseModel,
    validator
)

from datetime import datetime
from app.model.db.scheduled_events import ScheduledEventType
from app.model.schema.token import (
    IbetStraightBondUpdate,
    IbetShareUpdate
)


############################
# REQUEST
############################
class IbetStraightBondScheduledUpdate(BaseModel):
    """scheduled event (Request)"""
    scheduled_datetime: datetime
    event_type: str
    data: IbetStraightBondUpdate

    @validator("event_type")
    def event_type_is_supported(cls, v):
        if v is not None and v != ScheduledEventType.UPDATE:
            raise ValueError("event_type is not supported")
        return v


class IbetShareScheduledUpdate(BaseModel):
    """scheduled event (Request)"""
    scheduled_datetime: datetime
    event_type: str
    data: IbetShareUpdate

    @validator("event_type")
    def event_type_is_supported(cls, v):
        if v is not None and v != ScheduledEventType.UPDATE:
            raise ValueError("event_type is not supported")
        return v

############################
# RESPONSE
############################

class ScheduledEventResponse(BaseModel):
    """scheduled event (Response)"""
    token_address: str
    token_type: str
    scheduled_datetime: datetime
    event_type: str
    data: Dict[str, Any]
