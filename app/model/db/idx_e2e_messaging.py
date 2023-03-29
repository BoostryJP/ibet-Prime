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
from sqlalchemy import BigInteger, Column, DateTime, String

from .base import Base


class IDXE2EMessaging(Base):
    """INDEX E2E Message"""

    __tablename__ = "idx_e2e_messaging"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # transaction hash
    transaction_hash = Column(String(66), index=True)
    # from address
    from_address = Column(String(42), index=True)
    # to address
    to_address = Column(String(42), index=True)
    # type
    type = Column(String(50), nullable=False, index=True)
    # message
    message = Column(String(5000), nullable=False)
    # send timestamp
    send_timestamp = Column(DateTime)
    # block timestamp
    block_timestamp = Column(DateTime)


class IDXE2EMessagingBlockNumber(Base):
    """Synchronized blockNumber of IDXE2EMessaging"""

    __tablename__ = "idx_e2e_messaging_block_number"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # latest blockNumber
    latest_block_number = Column(BigInteger)
