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

from sqlalchemy import BigInteger, Column, DateTime, String

from .base import Base


class IDXIssueRedeem(Base):
    """INDEX Issue/Redeem"""

    __tablename__ = "idx_issue_redeem"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # event type
    event_type = Column(String(10), index=True)
    # transaction hash
    transaction_hash = Column(String(66), index=True)
    # token address
    token_address = Column(String(42), index=True)
    # locked address
    locked_address = Column(String(42), index=True)
    # target (account) address
    target_address = Column(String(42), index=True)
    # amount
    amount = Column(BigInteger)
    # block timestamp
    block_timestamp = Column(DateTime)


class IDXIssueRedeemEventType(str, Enum):
    """Issue/Redeem event type"""

    ISSUE = "Issue"
    REDEEM = "Redeem"


class IDXIssueRedeemSortItem(str, Enum):
    """Issue/Redeem sort item"""

    BLOCK_TIMESTAMP = "block_timestamp"
    LOCKED_ADDRESS = "locked_address"
    TARGET_ADDRESS = "target_address"
    AMOUNT = "amount"


class IDXIssueRedeemBlockNumber(Base):
    """Synchronized blockNumber of IDXIssueRedeem"""

    __tablename__ = "idx_issue_redeem_block_number"

    # sequence id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)
