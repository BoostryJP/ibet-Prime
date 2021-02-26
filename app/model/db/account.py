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

from sqlalchemy import Column, JSON, String

from .base import Base


class Account(Base):
    """Issuer Account"""
    __tablename__ = "account"

    # issuer address
    issuer_address = Column(String(42), primary_key=True)
    # ethereum keyfile
    keyfile = Column(JSON)
    # ethereum account password(encrypted)
    eoa_password = Column(String(2000))
    # rsa private key
    rsa_private_key = Column(String(8000))
    # rsa public key
    rsa_public_key = Column(String(2000))
    # rsa passphrase(encrypted)
    rsa_passphrase = Column(String(2000))


class AccountRsaKeyTemporary(Base):
    """Issuer Account(RSA Key Temporary Table)"""
    __tablename__ = "account_rsa_key_temporary"

    # issuer address
    issuer_address = Column(String(42), primary_key=True)
    # rsa private key
    rsa_private_key = Column(String(8000))
    # rsa public key
    rsa_public_key = Column(String(2000))
    # rsa passphrase(encrypted)
    rsa_passphrase = Column(String(2000))
