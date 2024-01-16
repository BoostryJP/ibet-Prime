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

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class E2EMessagingAccount(Base):
    """Account for E2E-Messaging"""

    __tablename__ = "e2e_messaging_account"

    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # ethereum keyfile
    keyfile: Mapped[dict | None] = mapped_column(JSON)
    # ethereum account password(encrypted)
    eoa_password: Mapped[str | None] = mapped_column(String(2000))
    # RSA key auto-generation interval(hour)
    rsa_key_generate_interval: Mapped[int | None] = mapped_column(Integer, default=0)
    # Number of RSA key generations
    rsa_generation: Mapped[int | None] = mapped_column(Integer, default=0)
    # delete flag
    is_deleted: Mapped[bool | None] = mapped_column(Boolean, default=False)


class E2EMessagingAccountRsaKey(Base):
    """E2E Messaging Account Rsa Key"""

    __tablename__ = "e2e_messaging_account_rsa_key"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # transaction hash
    transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # account address
    account_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # rsa private key
    rsa_private_key: Mapped[str | None] = mapped_column(String(4000))
    # rsa public key
    rsa_public_key: Mapped[str | None] = mapped_column(String(1000))
    # rsa passphrase(encrypted)
    rsa_passphrase: Mapped[str | None] = mapped_column(String(2000))
    # block timestamp
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
