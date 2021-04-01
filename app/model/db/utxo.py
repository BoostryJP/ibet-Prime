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
    Integer,
    String,
    BigInteger,
    DateTime
)

from .base import Base


class UTXO(Base):
    """UTXO"""
    # NOTE: When consuming amount, consume(subtract) in order from old records.

    __tablename__ = "utxo"

    # transaction hash
    transaction_hash = Column(String(66), primary_key=True)
    # account address
    account_address = Column(String(42), index=True)
    # token address
    token_address = Column(String(42), index=True)
    # transfer amount
    amount = Column(Integer)
    # block number
    block_number = Column(BigInteger)
    # block timestamp(UTC)
    block_timestamp = Column(DateTime)


class UTXOBlockNumber(Base):
    """Synchronized blockNumber of UTXO"""
    __tablename__ = "utxo_block_number"

    # sequence id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)
