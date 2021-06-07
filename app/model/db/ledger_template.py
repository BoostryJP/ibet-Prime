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
    # token name
    token_name = Column(String(200), nullable=False)
    # headers(any object array)
    headers = Column(JSON, default=[])
    # footers(any object array)
    footers = Column(JSON, default=[])


class LedgerDetailsTemplate(Base):
    """Ledger Details Template"""
    __tablename__ = "ledger_details_template"

    # sequence id
    # Note: It will be unique in token_address and token_detail_type,
    #       but since there is a possibility that multibyte characters will be set in token_detail_type,
    #       this column will be primary key.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), nullable=False)
    # token detail type
    token_detail_type = Column(String(100), nullable=False)
    # headers(any object array)
    headers = Column(JSON, default=[])
    # footers(any object array)
    footers = Column(JSON, default=[])
    # data type
    data_type = Column(String(20), nullable=False)
    # data source
    data_source = Column(String(42))


class LedgerDetailsDataType:
    IBET_FIN = "ibetfin"
    DB = "db"
