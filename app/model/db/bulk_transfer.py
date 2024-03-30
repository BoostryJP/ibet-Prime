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

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BulkTransferUpload(Base):
    """Bulk Transfer Upload"""

    __tablename__ = "bulk_transfer_upload"

    # upload id (UUID)
    upload_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    # token type
    token_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # transaction compression
    transaction_compression: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # processing status (pending:0, succeeded:1, failed:2)
    status: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


class BulkTransfer(Base):
    """Bulk Transfer"""

    __tablename__ = "bulk_transfer"

    # sequence id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    # upload id (UUID)
    upload_id: Mapped[str | None] = mapped_column(String(36), index=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token type
    token_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # transfer from
    from_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # transfer to
    to_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # transfer amount
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # processing status (pending:0, succeeded:1, failed:2)
    status: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # transaction error code
    transaction_error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # transaction error message
    transaction_error_message: Mapped[str | None] = mapped_column(String, nullable=True)
