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
from typing import Optional

from sqlalchemy import JSON, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TransferApprovalHistory(Base):
    """Token Transfer Approval Operation History"""

    __tablename__ = "transfer_approval_history"

    # Sequence Id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), index=True, nullable=False)
    # Exchange Address (value is set if the event is from exchange)
    exchange_address: Mapped[str] = mapped_column(
        String(42), index=True, nullable=False
    )
    # Application ID (escrow id is set if the event is from exchange)
    application_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    # Operation Type: TransferApprovalOperationType
    operation_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    # From Address Personal Information (snapshot)
    from_address_personal_info: Mapped[Optional[dict | list]] = mapped_column(JSON)
    # To Address Personal Information (snapshot)
    to_address_personal_info: Mapped[Optional[dict | list]] = mapped_column(JSON)

    def json(self):
        return {
            "token_address": self.token_address,
            "exchange_address": self.exchange_address,
            "application_id": self.application_id,
            "operation_type": self.operation_type,
            "from_address_personal_info": self.from_address_personal_info,
            "to_address_personal_info": self.to_address_personal_info,
        }


class TransferApprovalOperationType(str, Enum):
    APPROVE = "approve"
    CANCEL = "cancel"
