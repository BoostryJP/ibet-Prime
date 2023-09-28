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

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IDXE2EMessaging(Base):
    """INDEX E2E Message"""

    __tablename__ = "idx_e2e_messaging"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # transaction hash
    transaction_hash: Mapped[str | None] = mapped_column(String(66), index=True)
    # from address
    from_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # to address
    to_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # type
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # message
    message: Mapped[str] = mapped_column(String(5000), nullable=False)
    # send timestamp
    send_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    # block timestamp
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime)


class IDXE2EMessagingBlockNumber(Base):
    """Synchronized blockNumber of IDXE2EMessaging"""

    __tablename__ = "idx_e2e_messaging_block_number"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)
