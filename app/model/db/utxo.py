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

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UTXO(Base):
    """UTXO"""

    # NOTE: When consuming amount, consume(subtract) in order from old records.

    __tablename__ = "utxo"

    # transaction hash
    transaction_hash: Mapped[str] = mapped_column(String(66), primary_key=True)
    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # token address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # transfer amount
    amount: Mapped[int | None] = mapped_column(BigInteger)
    # block number
    block_number: Mapped[int | None] = mapped_column(BigInteger)
    # block timestamp(UTC)
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime)


class UTXOBlockNumber(Base):
    """Synchronized blockNumber of UTXO"""

    __tablename__ = "utxo_block_number"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)
