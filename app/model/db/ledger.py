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

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.model.db.base import Base, naive_utcnow


class LedgerTemplate(Base):
    """Ledger Template"""

    __tablename__ = "ledger_template"

    # token address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # issuer address
    issuer_address: Mapped[str | None] = mapped_column(String(42), index=False)
    # token name
    token_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # headers(any object array)
    headers: Mapped[dict | None] = mapped_column(JSON, default=[])
    # footers(any object array)
    footers: Mapped[dict | None] = mapped_column(JSON, default=[])


class LedgerDataType(StrEnum):
    IBET_FIN = "ibetfin"
    DB = "db"


class LedgerDetailsTemplate(Base):
    """Ledger Details Template"""

    __tablename__ = "ledger_details_template"

    # sequence id
    # Note: It will be unique in token_address and token_detail_type,
    #       but since there is a possibility that multibyte characters will be set in token_detail_type,
    #       this column will be primary key.
    id: Mapped[str] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token detail type
    token_detail_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # headers(any object array)
    headers: Mapped[dict | None] = mapped_column(JSON, default=[])
    # footers(any object array)
    footers: Mapped[dict | None] = mapped_column(JSON, default=[])
    # data type
    data_type: Mapped[LedgerDataType] = mapped_column(String(20), nullable=False)
    # data source (address or UUID)
    data_source: Mapped[str | None] = mapped_column(String(42))


class LedgerCreationStatus(StrEnum):
    """Ledger creation status"""

    PROCESSING = "processing"
    COMPLETED = "completed"


class LedgerCreationRequest(Base):
    """Ledger creation requests"""

    __tablename__ = "ledger_creation_request"

    # request id (UUID4)
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # token type (TokenType)
    token_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # status
    status: Mapped[LedgerCreationStatus] = mapped_column(String(20), nullable=False)


class LedgerCreationRequestData(Base):
    """Input dataset for ledger creation request"""

    __tablename__ = "ledger_creation_request_data"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # request id (UUID4)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # data type
    data_type: Mapped[LedgerDataType] = mapped_column(
        String(20), nullable=False, index=True
    )
    # account address
    account_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # acquisition date (format: YYYY/MM/DD)
    acquisition_date: Mapped[str] = mapped_column(String(10), nullable=False)
    # name
    name: Mapped[str | None] = mapped_column(String(200), index=True)
    # address
    address: Mapped[str | None] = mapped_column(String(200))
    # amount
    amount: Mapped[int | None] = mapped_column(BigInteger)
    # price
    price: Mapped[int | None] = mapped_column(BigInteger)
    # balance
    balance: Mapped[int | None] = mapped_column(BigInteger)


class Ledger(Base):
    """Ledger"""

    __tablename__ = "ledger"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token type (TokenType)
    token_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # ledger info
    ledger: Mapped[dict] = mapped_column(JSON, nullable=False)
    # created datetime(UTC)
    # NOTE: Because Base's created column is subject to change in the data patch, define another column.
    ledger_created: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=naive_utcnow
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
      "some_personal_info_not_registered": "boolean",
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
        DateTime, nullable=False, default=naive_utcnow
    )
