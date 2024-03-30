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

from enum import Enum

from sqlalchemy import JSON, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BatchRegisterPersonalInfoUpload(Base):
    """Batch Register PersonalInfo Upload"""

    __tablename__ = "batch_register_personal_info_upload"

    # upload id (UUID)
    upload_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    # processing status (BatchRegisterPersonalInfoUploadStatus)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)


class BatchRegisterPersonalInfoUploadStatus(str, Enum):
    """Batch Register PersonalInfo Upload Status"""

    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class BatchRegisterPersonalInfo(Base):
    """Batch Register PersonalInfo"""

    __tablename__ = "batch_register_personal_info"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # upload id (UUID)
    upload_id: Mapped[str | None] = mapped_column(String(36), index=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # account address
    account_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # processing status (pending:0, succeeded:1, failed:2)
    status: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

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
