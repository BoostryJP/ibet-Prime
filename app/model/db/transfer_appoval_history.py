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
    BigInteger,
    Column,
    Integer,
    String
)

from .base import Base


class TransferApprovalHistory(Base):
    """Token Transfer Approval History"""
    __tablename__ = 'transfer_approval_history'

    # Sequence Id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Token Address
    token_address = Column(String(42), index=True)
    # Application Id
    application_id = Column(BigInteger, index=True)
    # Result (Success:1, Fail:2)
    result = Column(Integer)

    def json(self):
        return {
            "token_address": self.token_address,
            "application_id": self.application_id,
            "result": self.result,
        }