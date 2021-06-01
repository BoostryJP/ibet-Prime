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
from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON
)

from .base import Base


class Notification(Base):
    """Notification"""
    __tablename__ = "notification"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # notification id (UUID)
    notice_id = Column(String(36), index=False)
    # issuer address
    issuer_address = Column(String(42))
    # notification priority（0:Low、1:Medium、2:High）
    priority = Column(Integer)
    # notification type
    type = Column(String(50))
    # notification code
    code = Column(Integer)
    # meta information
    metainfo = Column(JSON)


class NotificationType:
    BULK_TRANSFER_ERROR = "BulkTransferError"
    SCHEDULE_EVENT_ERROR = "ScheduleEventError"
