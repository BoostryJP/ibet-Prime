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

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime
)

from .base import Base


class AuthToken(Base):
    """Authentication Token"""
    __tablename__ = "auth_token"

    # issuer address
    issuer_address = Column(String(42), primary_key=True)
    # authentication token (sha256 hashed)
    auth_token = Column(String(64))
    # usage start
    usage_start = Column(DateTime, default=datetime.utcnow)
    # valid duration (sec)
    # - 0: endless
    valid_duration = Column(Integer, nullable=False)
