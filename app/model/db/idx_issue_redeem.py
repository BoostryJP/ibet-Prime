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

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IDXIssueRedeem(Base):
    """INDEX Issue/Redeem"""

    __tablename__ = "idx_issue_redeem"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # event type
    event_type: Mapped[str | None] = mapped_column(String(10), index=True)
    # transaction hash
    transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # token address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # locked address
    locked_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # target (account) address
    target_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # amount
    amount: Mapped[int | None] = mapped_column(BigInteger)
    # block timestamp
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime)


class IDXIssueRedeemEventType(StrEnum):
    """Issue/Redeem event type"""

    ISSUE = "Issue"
    REDEEM = "Redeem"


class IDXIssueRedeemSortItem(StrEnum):
    """Issue/Redeem sort item"""

    BLOCK_TIMESTAMP = "block_timestamp"
    LOCKED_ADDRESS = "locked_address"
    TARGET_ADDRESS = "target_address"
    AMOUNT = "amount"


class IDXIssueRedeemBlockNumber(Base):
    """Synchronized blockNumber of IDXIssueRedeem"""

    __tablename__ = "idx_issue_redeem_block_number"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)
