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
from typing import Optional
from pydantic import (
    BaseModel,
    validator,
    Field
)

from config import E2EE_REQUEST_ENABLED
from app.utils.check_utils import check_value_is_encrypted
from app.model.db import AccountRsaStatus


############################
# REQUEST
############################
class AccountCreateKeyRequest(BaseModel):
    """Account Create Key schema (REQUEST)"""
    eoa_password: str

    @validator("eoa_password")
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class AccountGenerateRsaKeyRequest(BaseModel):
    """Account Change Rsa Key schema (REQUEST)"""
    rsa_passphrase: Optional[str]

    @validator("rsa_passphrase")
    def rsa_passphrase_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("rsa_passphrase", v)
        return v


class AccountChangeEOAPasswordRequest(BaseModel):
    """Account Change EOA Password schema (REQUEST)"""
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


class AccountChangeRSAPassphraseRequest(BaseModel):
    """Account Change RSA Passphrase schema (REQUEST)"""
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


class AccountAuthTokenRequest(BaseModel):
    """Account Create Auth Token schema (REQUEST)"""
    valid_duration: int = Field(None, ge=0, le=259200)  # The maximum valid duration shall be 3 days.


############################
# RESPONSE
############################

class AccountResponse(BaseModel):
    """Account schema (Response)"""
    issuer_address: str
    rsa_public_key: Optional[str]
    rsa_status: AccountRsaStatus
    is_deleted: bool


class AccountAuthTokenResponse(BaseModel):
    """Account Auth Token schema (RESPONSE)"""
    auth_token: str
    usage_start: datetime
    valid_duration: int
