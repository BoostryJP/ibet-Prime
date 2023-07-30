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
from sqlalchemy import JSON, BigInteger, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IDXPersonalInfo(Base):
    """INDEX Personal information of the token holder (decrypted)"""

    __tablename__ = "idx_personal_info"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # account address
    account_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # issuer address
    issuer_address: Mapped[str | None] = mapped_column(String(42), index=True)
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
    _personal_info = mapped_column("personal_info", JSON, nullable=False)

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


class IDXPersonalInfoBlockNumber(Base):
    """Synchronized blockNumber of IDXPersonalInfo"""

    __tablename__ = "idx_personal_info_block_number"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)
