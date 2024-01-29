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
from enum import Enum, StrEnum

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TokenType(str, Enum):
    IBET_STRAIGHT_BOND = "IbetStraightBond"
    IBET_SHARE = "IbetShare"


class TokenVersion(StrEnum):
    V_22_12 = "22_12"
    V_23_12 = "23_12"


class Token(Base):
    """Issued Token"""

    __tablename__ = "token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token type
    type: Mapped[TokenType] = mapped_column(String(40), nullable=False)
    # transaction hash
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=True)
    # contract version
    version: Mapped[TokenVersion] = mapped_column(String(5), nullable=False)
    # contract ABI
    abi: Mapped[dict] = mapped_column(JSON, nullable=False)
    # token processing status (pending:0, succeeded:1, failed:2)
    token_status: Mapped[int | None] = mapped_column(Integer, default=1)


class TokenAttrUpdate(Base):
    """Managed Token Attribute Update"""

    __tablename__ = "token_attr_update"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # datetime when token attribute updated (UTC)
    updated_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TokenCache(Base):
    """Token Cache"""

    __tablename__ = "token_cache"

    # token address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # token attributes
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False)
    # cached datetime
    cached_datetime: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    # expiration datetime
    expiration_datetime: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
