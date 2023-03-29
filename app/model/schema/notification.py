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

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, conint

from app.model.db import BatchIssueRedeemProcessingCategory, NotificationType, TokenType

from .types import ResultSet


class IssueErrorMetaInfo(BaseModel):
    token_address: str
    token_type: TokenType
    arguments: dict


class BulkTransferErrorMetaInfo(BaseModel):
    upload_id: str
    token_type: TokenType
    error_transfer_id: list[int]


class ScheduleEventErrorMetaInfo(BaseModel):
    scheduled_event_id: str
    token_address: Optional[str]
    token_type: TokenType


class TransferApprovalInfoMetaInfo(BaseModel):
    id: int
    token_address: str
    token_type: Optional[TokenType]


class CreateLedgerInfoMetaInfo(BaseModel):
    token_address: str
    token_type: TokenType
    ledger_id: int


class BatchRegisterPersonalInfoErrorMetaInfo(BaseModel):
    upload_id: str
    error_registration_id: list[int]


class BatchIssueRedeemProcessedMetaInfo(BaseModel):
    category: BatchIssueRedeemProcessingCategory
    upload_id: str
    error_data_id: list[int]
    token_address: str
    token_type: TokenType


class LockInfoMetaInfo(BaseModel):
    token_address: str
    token_type: TokenType
    lock_address: str
    account_address: str
    value: int
    data: dict


class UnlockInfoMetaInfo(BaseModel):
    token_address: str
    token_type: TokenType
    lock_address: str
    account_address: str
    recipient_address: str
    value: int
    data: dict


class Notification(BaseModel):
    notice_id: str
    issuer_address: str
    priority: int
    notice_code: int
    created: str


class IssueErrorNotification(Notification):
    notice_type: Literal[NotificationType.ISSUE_ERROR]
    notice_code: conint(ge=0, le=2)
    metainfo: IssueErrorMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = (
                " - 0: Issuer does not exist\n"
                " - 1: Could not get the private key of the issuer\n"
                " - 2: Failed to send transaction\n"
            )


class BulkTransferErrorNotification(Notification):
    notice_type: Literal[NotificationType.BULK_TRANSFER_ERROR]
    notice_code: conint(ge=0, le=2)
    metainfo: BulkTransferErrorMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = (
                " - 0: Issuer does not exist\n"
                " - 1: Could not get the private key of the issuer\n"
                " - 2: Failed to send transaction\n"
            )


class ScheduleEventErrorNotification(Notification):
    notice_type: Literal[NotificationType.SCHEDULE_EVENT_ERROR]
    notice_code: conint(ge=0, le=2)
    metainfo: ScheduleEventErrorMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = (
                " - 0: Issuer does not exist\n"
                " - 1: Could not get the private key of the issuer\n"
                " - 2: Failed to send transaction\n"
            )


class TransferApprovalInfoNotification(Notification):
    notice_type: Literal[NotificationType.TRANSFER_APPROVAL_INFO]
    notice_code: conint(ge=0, le=3)
    metainfo: TransferApprovalInfoMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = (
                " - 0: Apply for transfer\n"
                " - 1: Cancel transfer\n"
                " - 2: Approve transfer\n"
                " - 3: Escrow finished (Only occurs in security token escrow)\n"
            )


class CreateLedgerInfoNotification(Notification):
    notice_type: Literal[NotificationType.CREATE_LEDGER_INFO]
    notice_code: conint(ge=0, le=0)
    metainfo: CreateLedgerInfoMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema[
                "description"
            ] = " - 0: Created ledger info successfully\n"


class BatchRegisterPersonalInfoErrorNotification(Notification):
    notice_type: Literal[NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR]
    notice_code: conint(ge=0, le=1)
    metainfo: BatchRegisterPersonalInfoErrorMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = (
                " - 0: Issuer does not exist\n" " - 1: Failed to send transaction\n"
            )


class BatchIssueRedeemProcessedNotification(Notification):
    notice_type: Literal[NotificationType.BATCH_ISSUE_REDEEM_PROCESSED]
    notice_code: conint(ge=0, le=3)
    metainfo: BatchIssueRedeemProcessedMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = (
                " - 0: All records successfully processed\n"
                " - 1: Issuer does not exist\n"
                " - 2: Failed to decode keyfile\n"
                " - 3: Some records are failed to send transaction"
            )


class LockInfoNotification(Notification):
    notice_type: Literal[NotificationType.LOCK_INFO]
    notice_code: conint(ge=0, le=0)
    metainfo: LockInfoMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = " - 0: Balance is locked\n"


class UnlockInfoNotification(Notification):
    notice_type: Literal[NotificationType.UNLOCK_INFO]
    notice_code: conint(ge=0, le=0)
    metainfo: UnlockInfoMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = " - 0: Balance is unlocked\n"


############################
# REQUEST
############################


############################
# RESPONSE
############################


class NotificationsListResponse(BaseModel):
    """Notifications List schema (Response)"""

    __root__: Union[
        IssueErrorNotification,
        BulkTransferErrorNotification,
        ScheduleEventErrorNotification,
        TransferApprovalInfoNotification,
        CreateLedgerInfoNotification,
        BatchRegisterPersonalInfoErrorNotification,
        BatchIssueRedeemProcessedNotification,
        LockInfoNotification,
        UnlockInfoNotification,
    ]


class ListAllNotificationsResponse(BaseModel):
    """List All Notifications schema (Response)"""

    result_set: ResultSet
    notifications: List[NotificationsListResponse]
