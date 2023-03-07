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
from sqlalchemy import JSON, BigInteger, Column, DateTime, String

from .base import Base


class IDXLock(Base):
    """Token Lock Event (INDEX)"""

    __tablename__ = "idx_lock"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66), index=True, nullable=False)
    # Block Number
    block_number = Column(BigInteger, nullable=False)
    # Token Address
    token_address = Column(String(42), index=True, nullable=False)
    # Lock Address
    lock_address = Column(String(42), index=True, nullable=False)
    # Account Address
    account_address = Column(String(42), index=True, nullable=False)
    # Lock Amount
    value = Column(BigInteger, nullable=False)
    # Message at Lock
    data = Column(JSON, nullable=False)
    # Lock Datetime
    block_timestamp = Column(DateTime, nullable=False)


class IDXUnlock(Base):
    """Token Unlock Event (INDEX)"""

    __tablename__ = "idx_unlock"

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Transaction Hash
    transaction_hash = Column(String(66), index=True, nullable=False)
    # Block Number
    block_number = Column(BigInteger, nullable=False)
    # Token Address
    token_address = Column(String(42), index=True, nullable=False)
    # Lock Address
    lock_address = Column(String(42), index=True, nullable=False)
    # Account Address
    account_address = Column(String(42), index=True, nullable=False)
    # Recipient Address
    recipient_address = Column(String(42), index=True, nullable=False)
    # Unlock Amount
    value = Column(BigInteger, nullable=False)
    # Message at Unlock
    data = Column(JSON, nullable=False)
    # Unlock Datetime
    block_timestamp = Column(DateTime, nullable=False)
