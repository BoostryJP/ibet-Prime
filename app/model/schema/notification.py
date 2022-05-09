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
from typing import (
    List,
    Dict,
    Any
)

from pydantic import BaseModel

from .types import ResultSet


############################
# REQUEST
############################


############################
# RESPONSE
############################

class NotificationsListResponse(BaseModel):
    """Notifications List schema (Response)"""
    notice_id: str
    issuer_address: str
    priority: int
    notice_type: str
    notice_code: int
    metainfo: dict
    created: datetime

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = "notice_type: IssueError\n" \
                                                " - 0: Issuer does not exist\n" \
                                                " - 1: Could not get the private key of the issuer\n" \
                                                " - 2: Failed to send transaction\n" \
                                                "\n" \
                                                "notice_type: BulkTransferError\n" \
                                                " - 0: Issuer does not exist\n" \
                                                " - 1: Could not get the private key of the issuer\n" \
                                                " - 2: Failed to send transaction\n" \
                                                "\n" \
                                                "notice_type: ScheduleEventError\n" \
                                                " - 0: Issuer does not exist\n" \
                                                " - 1: Could not get the private key of the issuer\n" \
                                                " - 2: Failed to send transaction\n" \
                                                "\n" \
                                                "notice_type: TransferApprovalInfo\n" \
                                                " - 0: Apply for transfer\n" \
                                                " - 1: Cancel transfer\n" \
                                                " - 2: Approve transfer\n" \
                                                " - 3: Escrow finished (Only occurs in security token escrow)\n" \
                                                "\n" \
                                                "notice_type: CreateLedgerInfo\n" \
                                                " - 0: Created ledger info successfully\n" \



class ListAllNotificationsResponse(BaseModel):
    """List All Notifications schema (Response)"""
    result_set: ResultSet
    notifications: List[NotificationsListResponse]
