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

from typing import (
    List,
    Dict,
    Any,
    Union
)

from pydantic import BaseModel, conint

from .types import ResultSet
from app.model.db import (
    NotificationType,
    BatchIssueRedeemProcessingCategory,
    TokenType
)


class IssueErrorMetainfo(BaseModel):
    token_address: str
    token_type: TokenType
    arguments: dict


class BulkTransferErrorMetainfo(BaseModel):
    upload_id: str
    token_type: TokenType
    error_transfer_id: list[int]


class ScheduleEventErrorMetainfo(BaseModel):
    scheduled_event_id: int
    token_type: TokenType


class TransferApprovalInfoMetaInfo(BaseModel):
    id: int
    token_address: str


class CreateLedgerInfoMetaInfo(BaseModel):
    token_address: str
    token_type: TokenType
    ledger_id: int


class BatchRegisterPersonalInfoErrorMetainfo(BaseModel):
    upload_id: str
    error_registration_id: list[int]


class BatchIssueRedeemProcessedMetainfo(BaseModel):
    category: BatchIssueRedeemProcessingCategory
    upload_id: str
    error_data_id: list[int]


class Notification(BaseModel):
    notice_id: str
    issuer_address: str
    priority: int
    notice_code: int
    created: str


class IssueErrorNotification(Notification):
    notice_type: str = NotificationType.ISSUE_ERROR
    notice_code: conint(ge=0, le=2)
    metainfo: IssueErrorMetainfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = " - 0: Issuer does not exist\n" \
                                                " - 1: Could not get the private key of the issuer\n" \
                                                " - 2: Failed to send transaction\n"


class BulkTransferErrorNotification(Notification):
    notice_type: str = NotificationType.BULK_TRANSFER_ERROR
    notice_code: conint(ge=0, le=2)
    metainfo: BulkTransferErrorMetainfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = " - 0: Issuer does not exist\n" \
                                                " - 1: Could not get the private key of the issuer\n" \
                                                " - 2: Failed to send transaction\n" \



class ScheduleEventErrorNotification(Notification):
    notice_type: str = NotificationType.SCHEDULE_EVENT_ERROR
    notice_code: conint(ge=0, le=2)
    metainfo: ScheduleEventErrorMetainfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = " - 0: Issuer does not exist\n" \
                                                " - 1: Could not get the private key of the issuer\n" \
                                                " - 2: Failed to send transaction\n" \



class TransferApprovalInfoNotification(Notification):
    notice_type: str = NotificationType.TRANSFER_APPROVAL_INFO
    notice_code: conint(ge=0, le=3)
    metainfo: TransferApprovalInfoMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = " - 0: Apply for transfer\n" \
                                                " - 1: Cancel transfer\n" \
                                                " - 2: Approve transfer\n" \
                                                " - 3: Escrow finished (Only occurs in security token escrow)\n"


class CreateLedgerInfoNotification(Notification):
    notice_type: str = NotificationType.CREATE_LEDGER_INFO
    notice_code: conint(ge=0, le=0)
    metainfo: CreateLedgerInfoMetaInfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = " - 0: Created ledger info successfully\n"


class BatchRegisterPersonalInfoErrorNotification(Notification):
    notice_type: str = NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
    notice_code: conint(ge=0, le=1)
    metainfo: BatchRegisterPersonalInfoErrorMetainfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = "notice_type: BatchRegisterPersonalInfoError\n" \
                                                " - 0: Issuer does not exist\n" \
                                                " - 1: Failed to send transaction\n"


class BatchIssueRedeemProcessedNotification(Notification):
    notice_type: str = NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
    notice_code: conint(ge=0, le=3)
    metainfo: BatchIssueRedeemProcessedMetainfo

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            notice_code_schema = schema["properties"]["notice_code"]
            notice_code_schema["description"] = "notice_type: BatchIssueRedeemProcessed\n" \
                                                " - 0: All records successfully processed\n" \
                                                " - 1: Issuer does not exist\n" \
                                                " - 2: Failed to decode keyfile\n" \
                                                " - 3: Some records are failed to send transaction"

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
        BatchIssueRedeemProcessedNotification
    ]


class ListAllNotificationsResponse(BaseModel):
    """List All Notifications schema (Response)"""
    result_set: ResultSet
    notifications: List[NotificationsListResponse]
