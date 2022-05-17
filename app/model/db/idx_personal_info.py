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
from sqlalchemy import Column
from sqlalchemy import (
    BigInteger,
    String,
    JSON
)

from .base import Base


class IDXPersonalInfo(Base):
    """INDEX Personal information of the token holder (decrypted)"""
    __tablename__ = 'idx_personal_info'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # account address
    account_address = Column(String(42), index=True)
    # issuer address
    issuer_address = Column(String(42), index=True)
    # personal information
    #   {
    #       "key_manager": "string",
    #       "name": "string",
    #       "postal_code": "string",
    #       "address": "string",
    #       "email": "string",
    #       "birth": "string",
    #       "is_corporate": "boolean",
    #       "tax_category": "integer"
    #   }
    personal_info = Column(JSON, nullable=False)


class IDXPersonalInfoBlockNumber(Base):
    """Synchronized blockNumber of IDXPersonalInfo"""
    __tablename__ = "idx_personal_info_block_number"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)
