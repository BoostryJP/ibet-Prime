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
from enum import StrEnum

from sqlalchemy import JSON, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.model.db import Base


class TokenUpdateOperationLog(Base):
    """Token Update Operation Log"""

    __tablename__ = "token_update_operation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token type(TokenType)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    # arguments
    arguments: Mapped[dict] = mapped_column(JSON, nullable=False)
    # original contents
    original_contents: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # operation category(TokenUpdateOperationCategory)
    operation_category: Mapped[str] = mapped_column(String(40), nullable=False)


class TokenUpdateOperationCategory(StrEnum):
    """Operation category of update token"""

    ISSUE = "Issue"
    UPDATE = "Update"
