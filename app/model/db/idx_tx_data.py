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
from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IDXTxData(Base):
    """Transaction data (INDEX)"""

    __tablename__ = "tx_data"

    hash: Mapped[str] = mapped_column(String(66), primary_key=True)
    block_hash: Mapped[str | None] = mapped_column(String(66))
    block_number: Mapped[int | None] = mapped_column(BigInteger, index=True)
    transaction_index: Mapped[int | None] = mapped_column(Integer)
    from_address: Mapped[str | None] = mapped_column(String(42), index=True)
    to_address: Mapped[str | None] = mapped_column(String(42), index=True)
    input: Mapped[str | None] = mapped_column(Text)
    gas: Mapped[int | None] = mapped_column(Integer)
    gas_price: Mapped[int | None] = mapped_column(BigInteger)
    value: Mapped[int | None] = mapped_column(BigInteger)
    nonce: Mapped[int | None] = mapped_column(Integer)
