# Copyright BOOSTRY Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ScheduledEvents(Base):
    """Scheduled Event"""

    __tablename__ = "scheduled_events"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # event id (UUID)
    event_id: Mapped[str | None] = mapped_column(String(36), index=True)
    # issuer_address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token_address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token type
    token_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # datetime when the event is scheduled (UTC)
    scheduled_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # event type
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # event processing status (pending:0, succeeded:1, failed:2)
    status: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # transaction data
    data: Mapped[dict] = mapped_column(JSON, nullable=False)


class ScheduledEventType(StrEnum):
    UPDATE = "Update"
