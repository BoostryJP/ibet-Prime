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
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.model.schema.base import ResultSet
from app.utils.check_utils import check_value_is_encrypted
from config import E2EE_REQUEST_ENABLED


############################
# REQUEST
############################
class E2EMessagingAccountCreateRequest(BaseModel):
    """E2E Messaging Account Create schema (REQUEST)"""

    eoa_password: str
    rsa_passphrase: Optional[str] = None
    rsa_key_generate_interval: Optional[int] = Field(
        default=24,
        ge=0,
        le=10_000,
        description="0 disables auto-generate(Unit is hour)",
    )
    rsa_generation: Optional[int] = Field(
        default=7, ge=0, le=100, description="0 disables generation"
    )

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v

    @field_validator("rsa_passphrase")
    @classmethod
    def rsa_passphrase_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("rsa_passphrase", v)
        return v


class E2EMessagingAccountUpdateRsaKeyRequest(BaseModel):
    """E2E Messaging Account Rsa Key Update schema (REQUEST)"""

    rsa_key_generate_interval: Optional[int] = Field(
        24, ge=0, le=10_000, description="0 disables auto-generate(Unit is hour)"
    )
    rsa_generation: Optional[int] = Field(
        7, ge=0, le=100, description="0 disables generation"
    )


class E2EMessagingAccountChangeEOAPasswordRequest(BaseModel):
    """E2E Messaging Account Change EOA Password schema (REQUEST)"""

    old_eoa_password: str
    eoa_password: str

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


class E2EMessagingAccountChangeRSAPassphraseRequest(BaseModel):
    """E2E Messaging Account Change RSA Passphrase schema (REQUEST)"""

    old_rsa_passphrase: str
    rsa_passphrase: str

    @field_validator("old_rsa_passphrase")
    @classmethod
    def old_rsa_passphrase_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("old_rsa_passphrase", v)
        return v

    @field_validator("rsa_passphrase")
    @classmethod
    def rsa_passphrase_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("rsa_passphrase", v)
        return v


############################
# RESPONSE
############################
class E2EMessagingAccountResponse(BaseModel):
    """E2E Messaging Account schema (Response)"""

    account_address: str
    rsa_key_generate_interval: Optional[int] = Field(...)
    rsa_generation: Optional[int] = Field(...)
    rsa_public_key: Optional[str] = Field(...)
    is_deleted: bool


class E2EMessagingResponse(BaseModel):
    """E2E Messaging schema (Response)"""

    id: int
    from_address: str
    to_address: str
    type: str
    message: Union[str, Dict, List[Any]]
    send_timestamp: datetime


class ListAllE2EMessagingResponse(BaseModel):
    """List All E2E Messaging schema (Response)"""

    result_set: ResultSet
    e2e_messages: List[E2EMessagingResponse]
