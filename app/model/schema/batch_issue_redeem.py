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
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from .base import ResultSet, TokenType
from .personal_info import PersonalInfo

############################
# RESPONSE
############################


class BatchIssueRedeemUpload(BaseModel):
    """Batch issue/redeem Upload"""

    batch_id: str = Field(description="UUID v4 required")
    issuer_address: str
    token_type: TokenType
    token_address: str
    processed: bool
    created: str
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "batch_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                    "issuer_address": "0x0000000000000000000000000000000000000000",
                    "token_type": "Bond",
                    "token_address": "0x0000000000000000000000000000000000000000",
                    "processed": True,
                    "created": "2022-09-02T19:49:33.370874+09:00",
                }
            ]
        }
    )


class ListBatchIssueRedeemUploadResponse(BaseModel):
    """List All Batch issue/redeem Upload(RESPONSE)"""

    result_set: ResultSet
    uploads: List[BatchIssueRedeemUpload]


class BatchIssueRedeemUploadIdResponse(BaseModel):
    """Batch issue/redeem upload id (RESPONSE)"""

    batch_id: str


class GetBatchIssueRedeemResult(BaseModel):
    """Result of Creating Batch issue/redeem schema (RESPONSE)"""

    account_address: str
    amount: int
    status: int
    personal_information: PersonalInfo


class GetBatchIssueRedeemResponse(BaseModel):
    """Get Batch issue/redeem upload schema (RESPONSE)"""

    processed: bool
    results: List[GetBatchIssueRedeemResult]
