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

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IDXPosition(Base):
    """INDEX Position"""

    __tablename__ = "idx_position"

    # token address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # balance
    balance: Mapped[int | None] = mapped_column(BigInteger)
    # exchange balance
    exchange_balance: Mapped[int | None] = mapped_column(BigInteger)
    # exchange commitment
    exchange_commitment: Mapped[int | None] = mapped_column(BigInteger)
    # pendingTransfer
    pending_transfer: Mapped[int | None] = mapped_column(BigInteger)

    def json(self):
        return {
            "account_address": self.account_address,
            "balance": self.balance,
            "exchange_balance": self.exchange_balance,
            "exchange_commitment": self.exchange_commitment,
            "pending_transfer": self.pending_transfer,
        }


class IDXPositionBondBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Bond token)"""

    __tablename__ = "idx_position_bond_block_number"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)


class IDXPositionShareBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Share token)"""

    __tablename__ = "idx_position_share_block_number"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)


class IDXLockedPosition(Base):
    """INDEX Locked Position"""

    __tablename__ = "idx_locked_position"

    # token address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # lock address
    lock_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # locked amount
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)

    def json(self):
        return {
            "token_address": self.token_address,
            "lock_address": self.lock_address,
            "account_address": self.account_address,
            "value": self.value,
        }
