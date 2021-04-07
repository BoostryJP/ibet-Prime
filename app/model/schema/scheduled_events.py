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
from typing import Dict
from pydantic import (
    BaseModel,
    validator
)
from datetime import (
    datetime,
    timedelta
)
from config import SCHEDULED_EVENTS_INTERVAL
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
    start_time: str
    event_type: str
    data: IbetStraightBondUpdate

    @validator("start_time")
    def start_time_is_future(cls, v):
        start_time = datetime.strptime(v, "%Y-%m-%d %H:%M")
        if start_time < datetime.now() + 2*timedelta(seconds=SCHEDULED_EVENTS_INTERVAL):
            raise ValueError(f"start_time have to set {2 * SCHEDULED_EVENTS_INTERVAL} sec later.")
        return v

    @validator("event_type")
    def event_type_is_supported(cls, v):
        if v is not None and v != ScheduledEventType.UPDATE:
            raise ValueError("event_type is not supported")
        return v


class IbetShareScheduledUpdate(BaseModel):
    """scheduled event (Request)"""
    start_time: str
    event_type: str
    data: IbetShareUpdate

    @validator("start_time")
    def start_time_is_future(cls, v):
        start_time = datetime.strptime(v, "%Y-%m-%d %H:%M")
        if start_time < datetime.now() + 2*timedelta(seconds=SCHEDULED_EVENTS_INTERVAL):
            raise ValueError(f"start_time have to set {2 * SCHEDULED_EVENTS_INTERVAL} sec later.")
        return v

    @validator("event_type")
    def event_type_is_supported(cls, v):
        if v is not None and v != ScheduledEventType.UPDATE:
            raise ValueError("event_type is not supported")
        return v

############################
# RESPONSE
############################

class ScheduledEventsResponse(BaseModel):
    """scheduled event (Response)"""
    token_address: str
    token_type: str
    event_type: str
    data: str
