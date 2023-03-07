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

from sqlalchemy import JSON, BigInteger, Column, DateTime, String

from .base import Base


class IDXTransferSourceEventType(str, Enum):
    """Transfer source event type"""

    TRANSFER = "Transfer"
    UNLOCK = "Unlock"


class IDXTransfer(Base):
    """INDEX Transfer"""

    __tablename__ = "idx_transfer"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # transaction hash
    transaction_hash = Column(String(66), index=True)
    # token address
    token_address = Column(String(42), index=True)
    # transfer from address
    from_address = Column(String(42), index=True)
    # transfer to address
    to_address = Column(String(42), index=True)
    # transfer amount
    amount = Column(BigInteger)
    # Source Event (IDXTransferSourceEventType)
    source_event = Column(String(50), nullable=False)
    # Data
    data = Column(JSON)
    # block timestamp
    block_timestamp = Column(DateTime)


class IDXTransferBlockNumber(Base):
    """Synchronized blockNumber of IDXTransfer"""

    __tablename__ = "idx_transfer_block_number"

    # sequence id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)
