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

from sqlalchemy import JSON, BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Account(Base):
    """Issuer Account"""

    __tablename__ = "account"

    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # issuer public key (hex encoded)
    # - NOTE: The value will be set in versions after v24.12.
    issuer_public_key: Mapped[str | None] = mapped_column(String(66))
    # ethereum private-key keyfile
    keyfile: Mapped[str | None] = mapped_column(JSON)
    # keyfile password (encrypted)
    eoa_password: Mapped[str | None] = mapped_column(String(2000))
    # rsa private key
    rsa_private_key: Mapped[str | None] = mapped_column(String(8000))
    # rsa public key
    rsa_public_key: Mapped[str | None] = mapped_column(String(2000))
    # rsa passphrase (encrypted)
    rsa_passphrase: Mapped[str | None] = mapped_column(String(2000))
    # rsa status (AccountRsaStatus)
    rsa_status: Mapped[int | None] = mapped_column(Integer)
    # delete flag
    is_deleted: Mapped[bool | None] = mapped_column(Boolean, default=False)


class AccountRsaStatus(int, Enum):
    """
    0:UNSET
    1:CREATING
    2:CHANGING
    3:SET
    """

    UNSET = 0
    CREATING = 1
    CHANGING = 2
    SET = 3


class AccountRsaKeyTemporary(Base):
    """Issuer Account (RSA Key Temporary Table)"""

    __tablename__ = "account_rsa_key_temporary"

    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # rsa private key
    rsa_private_key: Mapped[str | None] = mapped_column(String(8000))
    # rsa public key
    rsa_public_key: Mapped[str | None] = mapped_column(String(2000))
    # rsa passphrase (encrypted)
    rsa_passphrase: Mapped[str | None] = mapped_column(String(2000))


class ChildAccountIndex(Base):
    """Latest index of child account"""

    __tablename__ = "child_account_index"

    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # next index
    next_index: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ChildAccount(Base):
    """Issuer's Child Account"""

    __tablename__ = "child_account"

    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # child account index
    child_account_index: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # child account address
    child_account_address: Mapped[str] = mapped_column(String(42), nullable=False)


class TmpChildAccountBatchCreate(Base):
    """Temporary table for batch creation of child accounts"""

    __tablename__ = "tmp_child_account_batch_create"

    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # child account index
    child_account_index: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # personal information
    personal_info = mapped_column(JSON, nullable=False)
