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
from typing import Optional

from pydantic import BaseModel, Field

from .base import TokenType
from .token import IbetShareTransfer, IbetStraightBondTransfer


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
    transaction_compression: Optional[bool] = Field(
        default=None,
        description="Transaction compression mode",
    )


class IbetShareBulkTransferRequest(BaseModel):
    transfer_list: list[IbetShareTransfer] = Field(
        ...,
        description="List of data to be transferred",
        min_length=1,
        max_length=500000,
    )
    transaction_compression: Optional[bool] = Field(
        default=None,
        description="Transaction compression mode",
    )


############################
# RESPONSE
############################
class BulkTransferUploadIdResponse(BaseModel):
    """bulk transfer upload id"""

    upload_id: str


class BulkTransferUploadResponse(BaseModel):
    """bulk transfer upload"""

    upload_id: str
    issuer_address: str
    token_type: TokenType
    transaction_compression: bool
    status: int
    created: str


class BulkTransferResponse(BaseModel):
    """bulk transfer data"""

    upload_id: str
    issuer_address: str
    token_address: str
    token_type: TokenType
    from_address: str
    to_address: str
    amount: int
    status: int
