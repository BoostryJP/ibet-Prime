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
from enum import Enum

from sqlalchemy import JSON, Column, DateTime, Integer, String

from .base import Base


class Token(Base):
    """Issued Token"""

    __tablename__ = "token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # token type
    type = Column(String(40), nullable=False)
    # transaction hash
    tx_hash = Column(String(66), nullable=False)
    # issuer address
    issuer_address = Column(String(42), nullable=True)
    # token address
    token_address = Column(String(42), nullable=True)
    # ABI
    abi = Column(JSON, nullable=False)
    # token processing status (pending:0, succeeded:1, failed:2)
    token_status = Column(Integer, default=1)


class TokenAttrUpdate(Base):
    """Managed Token Attribute Update"""

    __tablename__ = "token_attr_update"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), index=True)
    # datetime when token attribute updated (UTC)
    updated_datetime = Column(DateTime, nullable=False)


class TokenType(str, Enum):
    IBET_STRAIGHT_BOND = "IbetStraightBond"
    IBET_SHARE = "IbetShare"


class TokenCache(Base):
    """Token Cache"""

    __tablename__ = "token_cache"

    # token address
    token_address = Column(String(42), primary_key=True)
    # token attributes
    attributes = Column(JSON, nullable=False)
    # cached datetime
    cached_datetime = Column(DateTime, default=datetime.utcnow)
    # expiration datetime
    expiration_datetime = Column(DateTime, default=datetime.utcnow)
