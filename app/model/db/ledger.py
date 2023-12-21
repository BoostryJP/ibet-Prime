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

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Ledger(Base):
    """Ledger"""

    __tablename__ = "ledger"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token type
    token_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # ledger info
    ledger: Mapped[dict] = mapped_column(JSON, nullable=False)
    # created datetime(UTC)
    # NOTE: Because Base's created column is subject to change in the data patch, define another column.
    ledger_created: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


"""
NOTE: Ledger.ledger's JSON structures

{
  "created": "string(YYYY/MM/DD)",
  "token_name": "string",
  "currency": "string",
  "headers": [],
  "details": [
    {
      "token_detail_type": "string",
      "headers": [],
      "data": [
        {
          "account_address": "string",
          "name": "string",
          "address": "string",
          "amount": 0,
          "price": 0,
          "balance": 0,
          "acquisition_date": "string(YYYY/MM/DD)"
        }
      ],
      "footers": [],
    },
  ],
  "footers": [],
}
"""


class LedgerDetailsData(Base):
    """Holder data outside of Blockchain"""

    __tablename__ = "ledger_details_data"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # data id (UUID)
    data_id: Mapped[str | None] = mapped_column(String(36), default=False)
    # name
    name: Mapped[str | None] = mapped_column(String(200))
    # address
    address: Mapped[str | None] = mapped_column(String(200))
    # amount
    amount: Mapped[int | None] = mapped_column(BigInteger)
    # price
    price: Mapped[int | None] = mapped_column(BigInteger)
    # balance
    balance: Mapped[int | None] = mapped_column(BigInteger)
    # acquisition date(format: YYYY/MM/DD)
    acquisition_date: Mapped[str | None] = mapped_column(String(10))
    # created datetime(UTC)
    # NOTE: Because Base's created column is subject to change in the data patch, define another column.
    data_created: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
