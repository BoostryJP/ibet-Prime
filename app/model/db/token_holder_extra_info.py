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

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TokenHolderExtraInfo(Base):
    """Additional attributes of token holders"""

    __tablename__ = "token_holder_extra_info"

    # token address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # the type of external-id-1
    external_id_1_type: Mapped[str | None] = mapped_column(String(50))
    # external-id-1
    external_id_1: Mapped[str | None] = mapped_column(String(50))
    # the type of external-id-2
    external_id_2_type: Mapped[str | None] = mapped_column(String(50))
    # external-id-2
    external_id_2: Mapped[str | None] = mapped_column(String(50))
    # the type of external-id-3
    external_id_3_type: Mapped[str | None] = mapped_column(String(50))
    # external-id-3
    external_id_3: Mapped[str | None] = mapped_column(String(50))

    def json(self):
        return {
            "token_address": self.token_address,
            "account_address": self.account_address,
            "external_id_1_type": self.external_id_1_type,
            "external_id_1": self.external_id_1,
            "external_id_2_type": self.external_id_2_type,
            "external_id_2": self.external_id_2,
            "external_id_3_type": self.external_id_3_type,
            "external_id_3": self.external_id_3,
        }

    default_extra_info = {
        "external_id_1_type": None,
        "external_id_1": None,
        "external_id_2_type": None,
        "external_id_2": None,
        "external_id_3_type": None,
        "external_id_3": None,
    }

    def extra_info(self):
        return {
            "external_id_1_type": self.external_id_1_type,
            "external_id_1": self.external_id_1,
            "external_id_2_type": self.external_id_2_type,
            "external_id_2": self.external_id_2,
            "external_id_3_type": self.external_id_3_type,
            "external_id_3": self.external_id_3,
        }
