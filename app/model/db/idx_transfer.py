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
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IDXTransferSourceEventType(StrEnum):
    """Transfer source event type"""

    TRANSFER = "Transfer"
    UNLOCK = "Unlock"


class DataMessage(BaseModel):
    message: Literal[
        "garnishment",
        "inheritance",
        "force_unlock",
    ]


class IDXTransfer(Base):
    """INDEX Transfer"""

    __tablename__ = "idx_transfer"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # transaction hash
    transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # token address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # transfer from address
    from_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # transfer to address
    to_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # transfer amount
    amount: Mapped[int | None] = mapped_column(BigInteger)
    # Source Event (IDXTransferSourceEventType)
    source_event: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Data
    #   source_event = "Transfer"
    #     => None
    #   source_event = "Unlock"
    #     =>  DataMessage
    data: Mapped[dict | None] = mapped_column(JSON)
    # Message
    #   source_event = "Transfer"
    #     => None
    #   source_event = "Unlock"
    #     => "force_unlock", "garnishment" or "inheritance"
    message: Mapped[str | None] = mapped_column(String(50), index=True)
    # block timestamp
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime)


class IDXTransferBlockNumber(Base):
    """Synchronized blockNumber of IDXTransfer"""

    __tablename__ = "idx_transfer_block_number"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)
