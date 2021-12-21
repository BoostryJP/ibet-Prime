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
    Boolean,
    Column,
    DateTime,
    String,
    BigInteger
)

from .base import Base


class IDXTransferApproval(Base):
    """INDEX Position"""
    __tablename__ = 'idx_transfer_approval'

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Token Address
    token_address = Column(String(42), index=True)
    # Exchange Address (value is set if the event is from exchange)
    exchange_address = Column(String(42), index=True)
    # Application Id (escrow id is set if the event is from exchange)
    application_id = Column(BigInteger, index=True)
    # Transfer From
    from_address = Column(String(42))
    # Transfer To
    to_address = Column(String(42))
    # Transfer Amount
    amount = Column(BigInteger)
    # Application Datetime
    application_datetime = Column(DateTime)
    # Application Blocktimestamp
    application_blocktimestamp = Column(DateTime)
    # Approval Datetime(ownership vesting datetime)
    approval_datetime = Column(DateTime)
    # Approval Blocktimestamp(ownership vesting block timestamp)
    approval_blocktimestamp = Column(DateTime)
    # Cancellation Status
    cancelled = Column(Boolean)
    # Approve Status
    transfer_approved = Column(Boolean)

    def json(self):
        return {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": self.application_id,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "application_datetime": self.application_datetime,
            "application_blocktimestamp": self.application_blocktimestamp,
            "approval_datetime": self.approval_datetime,
            "approval_blocktimestamp": self.approval_blocktimestamp,
            "cancelled": self.cancelled,
            "transfer_approved": self.transfer_approved
        }


class IDXTransferApprovalBlockNumber(Base):
    """Synchronized blockNumber of IDXTransferApproval"""
    __tablename__ = "idx_transfer_approval_block_number"

    # sequence id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)
