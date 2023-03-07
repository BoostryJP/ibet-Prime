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
from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, Integer, String

from .base import Base


class E2EMessagingAccount(Base):
    """E2E Messaging Account"""

    __tablename__ = "e2e_messaging_account"

    # account address
    account_address = Column(String(42), primary_key=True)
    # ethereum keyfile
    keyfile = Column(JSON)
    # ethereum account password(encrypted)
    eoa_password = Column(String(2000))
    # RSA key auto-generation interval(hour)
    rsa_key_generate_interval = Column(Integer, default=0)
    # Number of RSA key generations
    rsa_generation = Column(Integer, default=0)
    # delete flag
    is_deleted = Column(Boolean, default=False)


class E2EMessagingAccountRsaKey(Base):
    """E2E Messaging Account Rsa Key"""

    __tablename__ = "e2e_messaging_account_rsa_key"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # transaction hash
    transaction_hash = Column(String(66), index=True)
    # account address
    account_address = Column(String(42), index=True)
    # rsa private key
    rsa_private_key = Column(String(4000))
    # rsa public key
    rsa_public_key = Column(String(1000))
    # rsa passphrase(encrypted)
    rsa_passphrase = Column(String(2000))
    # block timestamp
    block_timestamp = Column(DateTime)
