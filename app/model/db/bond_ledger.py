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


class BondLedger(Base):
    """Bond Ledger"""
    __tablename__ = "bond_ledger"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42))
    # ledger info
    # NOTE: JSON structures differs depending on localize.
    ledger = Column(JSON)
    # country code(ISO 3166-1 alpha-3(uppercase))
    country_code = Column(String(3))
    # created datetime(UTC)
    # NOTE: Because Base's created column is subject to change in the data patch, define another column.
    bond_ledger_created = Column(DateTime, nullable=False, default=datetime.utcnow)


'''
NOTE:
BondLedger.ledger's JSON structures differs depending on localize.

[localized:JPN]
{
   "社債原簿作成日": "string",
   "社債情報": {
     "社債名称": "string",
     "社債の説明": "string",
     "社債の総額": 0,
     "各社債の金額": 0,
     "払込情報": {
       "払込金額": 0,
       "払込日": "string",
       "払込状況": true,
     },
     "社債の種類": "string"
   },
   "社債原簿管理人": {
     "氏名または名称": "string",
     "住所": "string",
     "事務取扱場所": "string"
   },
   "社債権者": [
     {
       "アカウントアドレス": "string",
       "氏名または名称": "string",
       "住所": "string",
       "社債金額": 0,
       "取得日": "string",
       "金銭以外の財産給付情報": {
         "財産の価格": "string",
         "給付日": "string"
       },
       "債権相殺情報": {
         "相殺する債権額": "string",
         "相殺日": "string"
       },
       "質権情報": {
         "質権者の氏名または名称": "string",
         "質権者の住所": "string",
         "質権の目的である債券": "string"
       },
       "備考": "string"
     }
   ]
}
'''
