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
from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON
)

from .base import Base


class UpdateToken(Base):
    """Update Token"""
    __tablename__ = "update_token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), index=True)
    # issuer address
    issuer_address = Column(String(42), nullable=True)
    # token type
    type = Column(String(40), nullable=False)
    # arguments
    arguments = Column(JSON, nullable=False)
    # processing status (pending:0, succeeded:1, failed:2)
    status = Column(Integer, nullable=False)
    # update trigger
    trigger = Column(String(40), nullable=False)
