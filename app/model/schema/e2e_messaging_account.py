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
    Optional,
    Dict,
    Any
)
from pydantic import (
    BaseModel,
    validator,
    Field
)

from config import E2EE_REQUEST_ENABLED
from app.utils.check_utils import check_value_is_encrypted


############################
# REQUEST
############################
class E2EMessagingAccountCreateKeyRequest(BaseModel):
    """E2E Messaging Account Create schema (REQUEST)"""
    eoa_password: str
    rsa_key_generate_interval: Optional[int] = Field(None, ge=1, le=10_000)
    rsa_generation: Optional[int] = Field(None, ge=1, le=100)

    @validator("eoa_password")
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            rsa_key_generate_interval_schema = schema["properties"]["rsa_key_generate_interval"]
            rsa_key_generate_interval_schema["description"] = "Unit is hour"


class E2EMessagingAccountUpdateRequest(BaseModel):
    """E2E Messaging Account Update schema (REQUEST)"""
    rsa_key_generate_interval: Optional[int] = Field(None, ge=1, le=10_000)
    rsa_generation: Optional[int] = Field(None, ge=1, le=100)

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            rsa_key_generate_interval_schema = schema["properties"]["rsa_key_generate_interval"]
            rsa_key_generate_interval_schema["description"] = "Unit is hour"


class E2EMessagingAccountGenerateRsaKeyRequest(BaseModel):
    """E2E Messaging Account Change Rsa Key schema (REQUEST)"""
    rsa_passphrase: Optional[str]

    @validator("rsa_passphrase")
    def rsa_passphrase_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("rsa_passphrase", v)
        return v


class E2EMessagingAccountChangeEOAPasswordRequest(BaseModel):
    """E2E Messaging Account Change EOA Password schema (REQUEST)"""
    old_eoa_password: str
    eoa_password: str

    @validator("old_eoa_password")
    def old_eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("old_eoa_password", v)
        return v

    @validator("eoa_password")
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class E2EMessagingAccountChangeRSAPassphraseRequest(BaseModel):
    """E2E Messaging Account Change RSA Passphrase schema (REQUEST)"""
    old_rsa_passphrase: str
    rsa_passphrase: str

    @validator("old_rsa_passphrase")
    def old_rsa_passphrase_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("old_rsa_passphrase", v)
        return v

    @validator("rsa_passphrase")
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
    rsa_key_generate_interval: Optional[int]
    rsa_generation: Optional[int]
    rsa_public_key: Optional[str]
    rsa_status: int
    is_deleted: bool
