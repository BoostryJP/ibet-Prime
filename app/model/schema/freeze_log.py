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

from pydantic import BaseModel, Field, PositiveInt, RootModel, field_validator

from app.model import EthereumAddress
from app.utils.check_utils import check_value_is_encrypted
from config import E2EE_REQUEST_ENABLED


############################
# REQUEST
############################
class CreateFreezeLogAccountRequest(BaseModel):
    """Freeze-Logging account create schema (REQUEST)"""

    eoa_password: str = Field(..., description="EOA keyfile password")

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class FreezeLogAccountChangeEOAPasswordRequest(BaseModel):
    """Freeze-Logging account change EOA password schema (REQUEST)"""

    old_eoa_password: str = Field(..., description="EOA keyfile password (old)")
    eoa_password: str = Field(..., description="EOA keyfile password (new)")

    @field_validator("old_eoa_password")
    @classmethod
    def old_eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("old_eoa_password", v)
        return v

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class RecordNewFreezeLogRequest(BaseModel):
    """Record new freeze log schema (REQUEST)"""

    account_address: EthereumAddress = Field(..., description="Logging account address")
    eoa_password: str = Field(..., description="Logging account key file password")
    log_message: str = Field(..., description="Log message")
    freezing_grace_block_count: PositiveInt = Field(
        ..., description="Freezing grace block count"
    )

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class UpdateFreezeLogRequest(BaseModel):
    """Update freeze log schema (REQUEST)"""

    account_address: EthereumAddress = Field(..., description="Logging account address")
    eoa_password: str = Field(..., description="Logging account key file password")
    log_message: str = Field(..., description="Log message")

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class RetrieveFreezeLogQuery(BaseModel):
    """Retrieve freeze log query (REQUEST)"""

    account_address: EthereumAddress = Field(description="Logging account address")


############################
# RESPONSE
############################
class FreezeLogAccountResponse(BaseModel):
    """Freeze-logging account reference schema (RESPONSE)"""

    account_address: str
    is_deleted: bool


class ListAllFreezeLogAccountResponse(RootModel[list[FreezeLogAccountResponse]]):
    """Freeze-logging account list reference schema (RESPONSE)"""

    pass


class RecordNewFreezeLogResponse(BaseModel):
    """New freeze-log recording schema (RESPONSE)"""

    log_index: int


class RetrieveFreezeLogResponse(BaseModel):
    """Frozen log data (RESPONSE)"""

    block_number: int
    freezing_grace_block_count: int
    log_message: str
