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

from sqlalchemy import JSON, BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IDXBlockData(Base):
    """Block data (INDEX)"""

    __tablename__ = "block_data"

    # Header data
    number: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    parent_hash: Mapped[str | None] = mapped_column(String(66), nullable=False)
    sha3_uncles: Mapped[str | None] = mapped_column(String(66))
    miner: Mapped[str | None] = mapped_column(String(42))
    state_root: Mapped[str | None] = mapped_column(String(66))
    transactions_root: Mapped[str | None] = mapped_column(String(66))
    receipts_root: Mapped[str | None] = mapped_column(String(66))
    logs_bloom: Mapped[str | None] = mapped_column(String(514))
    difficulty: Mapped[int | None] = mapped_column(BigInteger)
    gas_limit: Mapped[int | None] = mapped_column(Integer)
    gas_used: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[int | None] = mapped_column(Integer, nullable=False, index=True)
    proof_of_authority_data: Mapped[str | None] = mapped_column(Text)
    mix_hash: Mapped[str | None] = mapped_column(String(66))
    nonce: Mapped[str | None] = mapped_column(String(18))

    # Other data
    hash: Mapped[str] = mapped_column(String(66), nullable=False, index=True)
    size: Mapped[int | None] = mapped_column(Integer)
    transactions: Mapped[dict | None] = mapped_column(JSON)


class IDXBlockDataBlockNumber(Base):
    """Synchronized blockNumber of IDXBlockData"""

    __tablename__ = "idx_block_data_block_number"

    # Chain id
    chain_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    # Latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)
