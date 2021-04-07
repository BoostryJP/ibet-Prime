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
from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON
)

from .base import Base


class ScheduledEvents(Base):
    """Scheduled Event"""
    __tablename__ = "scheduled_events"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # issuer_address
    issuer_address = Column(String(42), nullable=False)
    # token_address
    token_address = Column(String(42), nullable=False)
    # token type
    token_type = Column(String(40), nullable=False)
    # event type
    event_type = Column(String(40), nullable=False)
    # event processing status (pending:0, succeeded:1, failed:2)
    status = Column(Integer, nullable=False, index=True)
    # transaction data
    data = Column(JSON, nullable=False)


class ScheduledEventType:
    UPDATE = "Update"
