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
from enum import IntEnum

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DeliveryStatus(IntEnum):
    """DVP Delivery Status"""

    DELIVERY_CREATED = 0
    DELIVERY_CANCELED = 1
    DELIVERY_CONFIRMED = 2
    DELIVERY_FINISHED = 3
    DELIVERY_ABORTED = 4


class IDXDelivery(Base):
    """DVP Delivery Event (INDEX)"""

    __tablename__ = "idx_delivery"

    # Sequence Id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # DVP Contract Address
    exchange_address: Mapped[str] = mapped_column(
        String(42), index=True, nullable=False
    )
    # Delivery ID
    delivery_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Delivery Buyer
    buyer_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # Delivery From
    seller_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Delivery Amount
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Delivery Agent
    agent_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Data
    data: Mapped[str] = mapped_column(Text)
    # Settlement Service Type
    settlement_service_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    # Create Delivery Blocktimestamp
    create_blocktimestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Create Transaction Hash
    create_transaction_hash: Mapped[str] = mapped_column(
        String(66), index=True, nullable=False
    )
    # Cancel Delivery Blocktimestamp
    cancel_blocktimestamp: Mapped[datetime | None] = mapped_column(DateTime)
    # Cancel Transaction Hash
    cancel_transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # Confirm Delivery Blocktimestamp
    confirm_blocktimestamp: Mapped[datetime | None] = mapped_column(DateTime)
    # Confirm Transaction Hash
    confirm_transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # Finish Delivery Blocktimestamp
    finish_blocktimestamp: Mapped[datetime | None] = mapped_column(DateTime)
    # Finish Transaction Hash
    finish_transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # Abort Delivery Blocktimestamp
    abort_blocktimestamp: Mapped[datetime | None] = mapped_column(DateTime)
    # Abort Transaction Hash
    abort_transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # Confirmation Status
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Delivery Valid Status
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Delivery Status(DeliveryStatus)
    status: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=DeliveryStatus.DELIVERY_CREATED
    )
    # Dedicated Agent ID
    dedicated_agent_id: Mapped[str | None] = mapped_column(String(100))

    def json(self):
        return {
            "exchange_address": self.exchange_address,
            "token_address": self.token_address,
            "delivery_id": self.delivery_id,
            "buyer_address": self.buyer_address,
            "seller_address": self.seller_address,
            "agent_address": self.agent_address,
            "amount": self.amount,
            "data": self.data,
            "settlement_service_type": self.settlement_service_type,
            "create_blocktimestamp": self.create_blocktimestamp,
            "create_transaction_hash": self.create_transaction_hash,
            "cancel_blocktimestamp": self.cancel_blocktimestamp,
            "cancel_transaction_hash": self.cancel_transaction_hash,
            "confirm_blocktimestamp": self.confirm_blocktimestamp,
            "confirm_transaction_hash": self.confirm_transaction_hash,
            "finish_blocktimestamp": self.finish_blocktimestamp,
            "finish_transaction_hash": self.finish_transaction_hash,
            "abort_blocktimestamp": self.abort_blocktimestamp,
            "abort_transaction_hash": self.abort_transaction_hash,
            "confirmed": self.confirmed,
            "valid": self.valid,
            "status": self.status,
        }


class IDXDeliveryBlockNumber(Base):
    """Synchronized blockNumber of IDXDelivery"""

    __tablename__ = "idx_delivery_block_number"

    # target exchange address
    exchange_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
