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

import pytz
from sqlalchemy import JSON, BigInteger, DateTime, Index, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

import config

from .base import Base, naive_utcnow

local_tz = pytz.timezone(config.TZ)
utc_tz = pytz.timezone("UTC")


class PersonalInfoDataSource(StrEnum):
    ON_CHAIN = "on-chain"
    OFF_CHAIN = "off-chain"


class IDXPersonalInfo(Base):
    """INDEX Personal information of the token holder (decrypted)"""

    __tablename__ = "idx_personal_info"

    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # personal information
    #   {
    #       "key_manager": "string",  // If managed by the issuer itself, 'SELF' is set by default.
    #       "name": "string",
    #       "postal_code": "string",
    #       "address": "string",
    #       "email": "string",
    #       "birth": "string",
    #       "is_corporate": "boolean",
    #       "tax_category": "integer"
    #   }
    _personal_info = mapped_column("personal_info", JSON, nullable=False)
    # data source
    data_source: Mapped[PersonalInfoDataSource] = mapped_column(
        String(10), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_personal_info_issuer_account",
            issuer_address,
            account_address,
            postgresql_include=["personal_info", "data_source", "created", "modified"],
        ),
    )

    @hybrid_property
    def personal_info(self):
        if self._personal_info:
            return {
                "key_manager": self._personal_info.get("key_manager", None),
                "name": self._personal_info.get("name", None),
                "address": self._personal_info.get("address", None),
                "postal_code": self._personal_info.get("postal_code", None),
                "email": self._personal_info.get("email", None),
                "birth": self._personal_info.get("birth", None),
                "is_corporate": self._personal_info.get("is_corporate", None),
                "tax_category": self._personal_info.get("tax_category", None),
            }
        return self._personal_info

    @personal_info.inplace.setter
    def _personal_info_setter(self, personal_info_dict: dict):
        self._personal_info = {
            "key_manager": personal_info_dict.get("key_manager", None),
            "name": personal_info_dict.get("name", None),
            "address": personal_info_dict.get("address", None),
            "postal_code": personal_info_dict.get("postal_code", None),
            "email": personal_info_dict.get("email", None),
            "birth": personal_info_dict.get("birth", None),
            "is_corporate": personal_info_dict.get("is_corporate", None),
            "tax_category": personal_info_dict.get("tax_category", None),
        }

    @staticmethod
    def localize_datetime(_datetime: datetime) -> datetime | None:
        if _datetime is None:
            return None
        return utc_tz.localize(_datetime).astimezone(local_tz)

    def json(self):
        return {
            "account_address": self.account_address,
            "personal_info": self.personal_info,
            "created": self.localize_datetime(self.created),
            "modified": self.localize_datetime(self.modified),
        }


class IDXPersonalInfoBlockNumber(Base):
    """Synchronized blockNumber of IDXPersonalInfo"""

    __tablename__ = "idx_personal_info_block_number"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)


class PersonalInfoEventType(StrEnum):
    REGISTER = "register"
    MODIFY = "modify"


class IDXPersonalInfoHistory(Base):
    """Indexed personal information histories"""

    __tablename__ = "idx_personal_info_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # account address
    account_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # issuer address
    issuer_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # event type
    event_type: Mapped[PersonalInfoEventType] = mapped_column(
        String(10), index=True, nullable=False
    )
    # personal information
    personal_info = mapped_column(JSON, nullable=False)
    # block timestamp
    # - For off-chain transactions, UTC now at the time of record insertion is set.
    block_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime, default=naive_utcnow
    )

    @staticmethod
    def localize_datetime(_datetime: datetime) -> datetime | None:
        if _datetime is None:
            return None
        return utc_tz.localize(_datetime).astimezone(local_tz)

    def json(self):
        return {
            "id": self.id,
            "account_address": self.account_address,
            "event_type": self.event_type,
            "personal_info": self.personal_info,
            "block_timestamp": self.localize_datetime(self.block_timestamp),
            "created": self.localize_datetime(self.created),
        }
