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

from enum import StrEnum

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

"""
notice_type: IssueError
- 0: Issuer does not exist
- 1: Could not get the private key of the issuer
- 2: Failed to send transaction

notice_type: BulkTransferError
- 0: Issuer does not exist
- 1: Could not get the private key of the issuer
- 2: Failed to send transaction

notice_type: BatchRegisterPersonalInfoError
- 0: Issuer does not exist
- 1: Failed to send transaction

notice_type: BatchIssueRedeemProcessed
- 0: All records successfully processed
- 1: Issuer does not exist
- 2: Failed to decode keyfile
- 3: Some records are failed to send transaction

notice_type: ScheduleEventError
- 0: Issuer does not exist
- 1: Could not get the private key of the issuer
- 2: Failed to send transaction

notice_type: TransferApprovalInfo
- 0: Apply for transfer
- 1: Cancel transfer
- 2: Approve transfer
- 3: Escrow finished (Only occurs in security token escrow)

notice_type: CreateLedgerInfo
- 0: Created ledger info successfully

notice_type: LockInfo
- 0: Balance is locked

notice_type: UnlockInfo
- 0: Balance is unlocked

notice_type: DVPDeliveryInfo
- 0: Delivery is confirmed
- 1: Delivery is finished
"""


class Notification(Base):
    """Notification"""

    __tablename__ = "notification"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # notification id (UUID)
    notice_id: Mapped[str | None] = mapped_column(String(36), index=False)
    # issuer address
    issuer_address: Mapped[str | None] = mapped_column(String(42))
    # notification priority（0:Low、1:Medium、2:High）
    priority: Mapped[int | None] = mapped_column(Integer)
    # notification type
    type: Mapped[str | None] = mapped_column(String(50))
    # notification code
    code: Mapped[int | None] = mapped_column(Integer)
    # meta information
    metainfo: Mapped[dict | None] = mapped_column(JSON)


class NotificationType(StrEnum):
    ISSUE_ERROR = "IssueError"
    BULK_TRANSFER_ERROR = "BulkTransferError"
    BATCH_REGISTER_PERSONAL_INFO_ERROR = "BatchRegisterPersonalInfoError"
    SCHEDULE_EVENT_ERROR = "ScheduleEventError"
    TRANSFER_APPROVAL_INFO = "TransferApprovalInfo"
    CREATE_LEDGER_INFO = "CreateLedgerInfo"
    BATCH_ISSUE_REDEEM_PROCESSED = "BatchIssueProcessed"
    LOCK_INFO = "LockInfo"
    UNLOCK_INFO = "UnlockInfo"
    DVP_DELIVERY_INFO = "DVPDeliveryInfo"
