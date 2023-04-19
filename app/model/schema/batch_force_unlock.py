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
from pydantic import BaseModel, Field

from app.model.db import TokenType
from app.model.schema.types import ResultSet

############################
# REQUEST
############################


############################
# RESPONSE
############################


class BatchForceUnlockUpload(BaseModel):
    """batch force unlock upload"""

    batch_id: str
    issuer_address: str
    token_type: TokenType
    token_address: str
    status: int = Field(..., description="0:pending, 1:succeeded, 2:failed")
    created: str

    class Config:
        schema_extra = {
            "example": {
                "batch_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                "issuer_address": "0x0000000000000000000000000000000000000000",
                "token_type": "Bond",
                "token_address": "0x0000000000000000000000000000000000000000",
                "processed": True,
                "created": "2022-09-02T19:49:33.370874+09:00",
            }
        }


class BatchForceUnlockUploadResponse(BaseModel):
    """List All Batch force unlock uploads"""

    result_set: ResultSet
    uploads: list[BatchForceUnlockUpload]


class BatchForceUnlockUploadIdResponse(BaseModel):
    """batch force unlock upload id"""

    batch_id: str


class BatchForceUnlockResult(BaseModel):
    """batch force unlock data"""

    id: int
    account_address: str
    lock_address: str
    recipient_address: str
    value: int
    status: int = Field(..., description="0:pending, 1:succeeded, 2:failed")


class BatchForceUnlockResponse(BaseModel):
    """List All batch force unlock records"""

    status: int = Field(..., description="0:pending, 1:succeeded, 2:failed")
    results: list[BatchForceUnlockResult]
