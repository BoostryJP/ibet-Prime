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
import uuid
from typing import Dict, List, Union

from pydantic import BaseModel, Field, validator

from app.model.db import TokenHolderBatchStatus
from app.model.schema.types import ResultSet

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

    @validator("list_id")
    def list_id_is_uuid_v4(cls, v):
        try:
            _uuid = uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("list_id is not UUIDv4.")
        return v


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


class RetrieveTokenHolderCollectionResponse(BaseModel):
    """Retrieve Token Holders Collection schema (RESPONSE)"""

    token_address: str
    block_number: int
    list_id: str = Field(description="UUID v4 required")
    status: TokenHolderBatchStatus


class ListAllTokenHolderCollectionsResponse(BaseModel):
    """List All Token Holders Collections schema (RESPONSE)"""

    result_set: ResultSet
    collections: List[RetrieveTokenHolderCollectionResponse]


class TokenHoldersCollectionHolder(BaseModel):
    account_address: str = Field(description="Account address of token holder.")
    hold_balance: int = Field(
        description="Amount of balance."
        "This includes balance/pending_transfer/exchange_balance/exchange_commitment."
    )
    locked_balance: int = Field(description="Amount of locked balance.")


class RetrieveTokenHoldersListResponse(BaseModel):
    """Retrieve Token Holders List schema (RESPONSE)"""

    status: TokenHolderBatchStatus
    holders: List[TokenHoldersCollectionHolder]

    class Config:
        schema_extra = {
            "example": {
                "status": "done",
                "holders": [
                    {
                        "account_address": "0x85a8b8887a4bD76859751b10C8aC8EC5f3aA1bDB",
                        "hold_balance": 30000,
                        "locked_balance": 0,
                    }
                ],
            }
        }
