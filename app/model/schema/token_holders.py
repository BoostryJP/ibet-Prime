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
from typing import List, Dict, Union

from pydantic import BaseModel, Field
from app.model.db import TokenHolderBatchStatus


############################
# REQUEST
############################


class CreateTokenHoldersListRequest(BaseModel):
    """Create Token Holders List schema (REQUEST)"""

    list_id: str = Field(description="UUID v4 required")
    block_number: int = Field(ge=1)

    class Config:
        schema_extra = {
            "example": {
                "list_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                "block_number": 765,
            }
        }


############################
# RESPONSE
############################


class CreateTokenHoldersListResponse(BaseModel):
    """Create Token Holders List schema (RESPONSE)"""

    list_id: str = Field(description="UUID v4 required")
    status: TokenHolderBatchStatus

    class Config:
        schema_extra = {
            "example": {
                "list_id": "cfd83622-34dc-4efe-a68b-2cc275d3d824",
                "status": "pending",
            }
        }


class GetTokenHoldersListResponse(BaseModel):
    """Get Token Holders List schema (RESPONSE)"""

    status: TokenHolderBatchStatus
    holders: List[Dict[str, Union[int, str]]]

    class Config:
        schema_extra = {
            "example": {
                "status": "done",
                "holders": [
                    {
                        "account_address": "0x85a8b8887a4bD76859751b10C8aC8EC5f3aA1bDB",
                        "balance": 30000,
                        "pending_transfer": 0,
                        "exchange_balance": 20000,
                        "exchange_commitment": 10000,
                    }
                ],
            }
        }
