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

from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
    DateTime
)

from .base import Base


class Ledger(Base):
    """Ledger"""
    __tablename__ = "ledger"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), nullable=False)
    # token type
    token_type = Column(String(40), nullable=False)
    # ledger info
    ledger = Column(JSON, nullable=False)
    # created datetime(UTC)
    # NOTE: Because Base's created column is subject to change in the data patch, define another column.
    ledger_created = Column(DateTime, nullable=False, default=datetime.utcnow)


"""
NOTE: Ledger.ledger's JSON structures
If LedgerDetailsTemplate.data_type is 'db', 'details[].data' is empty.
This is merged with LedgerTemplate, LedgerDetailsTemplate, and LedgerDetailsData.

{
  "created": "string(YYYY/MM/DD)",
  "token_name": "",
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
    """Ledger Details Data"""
    __tablename__ = "ledger_details_data"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), nullable=False)
    # data id
    data_id = Column(String(42), default=False)
    # name
    name = Column(String(200))
    # address
    address = Column(String(200))
    # amount
    amount = Column(Integer)
    # price
    price = Column(Integer)
    # balance
    balance = Column(Integer)
    # acquisition date(format: YYYY/MM/DD)
    acquisition_date = Column(String(10))
    # created datetime(UTC)
    # NOTE: Because Base's created column is subject to change in the data patch, define another column.
    data_created = Column(DateTime, nullable=False, default=datetime.utcnow)
