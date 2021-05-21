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
    Boolean,
    JSON
)

from .base import Base


class LedgerTemplate(Base):
    """Ledger Template"""
    __tablename__ = "ledger_template"

    # token address
    token_address = Column(String(42), primary_key=True)
    # issuer address
    issuer_address = Column(String(42), index=False)
    # ledger name
    ledger_name = Column(String(200), nullable=False)
    # country code(ISO 3166-1 alpha-3(uppercase))
    country_code = Column(String(3), nullable=False)
    # item(ledger header, footer, etc)
    item = Column(JSON, default={})


class LedgerTemplateRights(Base):
    """Ledger Template Rights"""
    __tablename__ = "ledger_template_rights"

    # sequence id
    # Note: It will be unique in token_address and rights_name,
    #       but since there is a possibility that multibyte characters will be set in rights_name,
    #       this column will be primary key.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), nullable=False)
    # rights name
    rights_name = Column(String(100), nullable=False)
    # item(ledger rights header, footer, etc)
    item = Column(JSON, default={})
    # details item(items set for each details)
    # NOTE: The following key is a reserved word and cannot be set.
    #       - default: account_address, name, address, amount, price, balance, acquisition_date
    #       - JPN: アカウントアドレス, 氏名または名称, 住所, 保有口数, 一口あたりの金額, 保有残高, 取得日
    details_item = Column(JSON, default={})
    # use uploaded details
    is_uploaded_details = Column(Boolean, default=False)
