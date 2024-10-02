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

from typing import Annotated, Optional

from fastapi import Query
from pydantic import BaseModel, Field, NonNegativeInt
from pydantic.dataclasses import dataclass

from .base import ResultSet, TokenType
from .personal_info import PersonalInfo
from .token import IbetShareTransfer, IbetStraightBondTransfer


############################
# COMMON
############################
class BulkTransferUpload(BaseModel):
    """Bulk transfer upload"""

    upload_id: str = Field(..., description="Upload id")
    issuer_address: str = Field(..., description="Issuer account address")
    token_type: TokenType = Field(..., description="Token type")
    token_address: str | None = Field(..., description="Token address")
    status: int = Field(..., description="Processing status")
    created: str = Field(..., description="Upload created datetime (ISO8601)")


class BulkTransferUploadRecord(BaseModel):
    """Bulk transfer upload record"""

    upload_id: str = Field(..., description="Upload id")
    issuer_address: str = Field(..., description="Issuer account address")
    token_address: str = Field(..., description="Token address")
    token_type: TokenType = Field(..., description="Token type")
    from_address: str = Field(..., description="Transfer source address")
    from_address_personal_information: Optional[PersonalInfo] = Field(
        ..., description="Personal information of the from_address"
    )
    to_address: str = Field(..., description="Transfer destination address")
    to_address_personal_information: Optional[PersonalInfo] = Field(
        ..., description="Personal information of the to_address"
    )
    amount: int = Field(..., description="Transfer amount")
    status: int = Field(..., description="Transfer status")
    transaction_error_code: int | None = Field(..., description="Transfer error code")
    transaction_error_message: str | None = Field(
        ..., description="Transfer error message"
    )


############################
# REQUEST
############################
class IbetStraightBondBulkTransferRequest(BaseModel):
    transfer_list: list[IbetStraightBondTransfer] = Field(
        ...,
        description="List of data to be transferred",
        min_length=1,
        max_length=500000,
    )


class IbetShareBulkTransferRequest(BaseModel):
    transfer_list: list[IbetShareTransfer] = Field(
        ...,
        description="List of data to be transferred",
        min_length=1,
        max_length=500000,
    )


@dataclass
class ListBulkTransferQuery:
    offset: Annotated[
        Optional[NonNegativeInt], Query(description="Offset for pagination")
    ] = None
    limit: Annotated[
        Optional[NonNegativeInt], Query(description="Limit for pagination")
    ] = None


############################
# RESPONSE
############################
class BulkTransferUploadIdResponse(BaseModel):
    """bulk transfer upload id"""

    upload_id: str = Field(..., description="Upload id")


class BulkTransferUploadResponse(BaseModel):
    """Bulk transfer uploads"""

    result_set: ResultSet
    bulk_transfer_uploads: list[BulkTransferUpload] = Field(
        default=[], description="Bulk transfer uploads"
    )


class BulkTransferUploadRecordResponse(BaseModel):
    """Bulk transfer upload records"""

    result_set: ResultSet
    bulk_transfer_upload_records: list[BulkTransferUploadRecord]
