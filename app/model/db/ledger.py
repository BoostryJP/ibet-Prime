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
    # NOTE: JSON structures differs depending on localize.
    ledger = Column(JSON, nullable=False)
    # country code(ISO 3166-1 alpha-3(uppercase))
    country_code = Column(String(3), nullable=False)
    # created datetime(UTC)
    # NOTE: Because Base's created column is subject to change in the data patch, define another column.
    ledger_created = Column(DateTime, nullable=False, default=datetime.utcnow)


"""
NOTE: Ledger.ledger's JSON structures
- 'ledger.item' is set to LedgerTemplate.item
- 'ledger.rights[].item' is set to LedgerTemplateRights.item
- LedgerTemplateRights.details_item add in the 'ledger.rights[].details[]'

[default]
{
  "created": "string(YYYY/MM/DD)",
  "rights_name": "string",
  "item": {},
  "rights": [
    {
      "rights_name": "string",
      "item": {},
      "details": [
        "account_address": "string",
        "name": "string",
        "address": "string",
        "amount": 0,
        "price": 0,
        "balance": 0,
        "acquisition_date": "string(YYYY/MM/DD)",
        item_key: item_value
      ]
    }
  ]
}

[country_code:JPN]
{
  "原簿作成日": "string(YYYY/MM/DD)",
  "原簿名称": "string",
  "項目": {},
  "権利": [
    {
      "権利名称": "string",
      "項目": {},
      "明細": [
        {
          "アカウントアドレス": "string",
          "氏名または名称": "string",
          "住所": "string",
          "保有口数": 0,
          "一口あたりの金額": 0,
          "保有残高": 0,
          "取得日": "string(YYYY/MM/DD)",
          item_key: item_value
        }
      ]
    }
  ]
}
"""


class LedgerRightsDetails(Base):
    """Ledger Rights Details"""
    __tablename__ = "ledger_rights_details"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), nullable=False)
    # rights name
    rights_name = Column(String(100), nullable=False)
    # account address
    account_address = Column(String(42))
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