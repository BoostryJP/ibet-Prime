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
    Column,
    String,
    BigInteger
)

from .base import Base


class IDXPosition(Base):
    """INDEX Position"""
    __tablename__ = 'idx_position'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), index=True)
    # account address
    account_address = Column(String(42), index=True)
    # balance
    balance = Column(BigInteger)
    # exchange balance
    exchange_balance = Column(BigInteger)
    # exchange commitment
    exchange_commitment = Column(BigInteger)
    # pendingTransfer
    pending_transfer = Column(BigInteger)

    def json(self):
        return {
            "account_address": self.account_address,
            "balance": self.balance,
            "exchange_balance": self.exchange_balance,
            "exchange_commitment": self.exchange_commitment,
            "pending_transfer": self.pending_transfer
        }


class IDXPositionBondBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Bond token)"""
    __tablename__ = "idx_position_bond_block_number"

    # sequence id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)


class IDXPositionShareBlockNumber(Base):
    """Synchronized blockNumber of IDXPosition(Share token)"""
    __tablename__ = "idx_position_share_block_number"

    # sequence id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)
