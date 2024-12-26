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
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, RootModel, field_validator

from app.model import ValidatedDatetimeStr
from app.model.db import AccountRsaStatus
from app.model.schema.base import BasePaginationQuery, ResultSet, SortOrder
from app.model.schema.personal_info import PersonalInfo, PersonalInfoInput
from app.utils.check_utils import check_value_is_encrypted
from config import E2EE_REQUEST_ENABLED


############################
# COMMON
############################
class Account(BaseModel):
    """Account schema"""

    issuer_address: str
    rsa_public_key: Optional[str] = Field(...)
    rsa_status: AccountRsaStatus
    is_deleted: bool


class ChildAccount(BaseModel):
    """Child account schema"""

    issuer_address: str
    child_account_index: int
    child_account_address: str
    personal_information: PersonalInfo | None
    created: datetime | None
    modified: datetime | None


############################
# REQUEST
############################
class AccountCreateKeyRequest(BaseModel):
    """Account Create Key schema (REQUEST)"""

    eoa_password: str

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class AccountGenerateRsaKeyRequest(BaseModel):
    """Account Change Rsa Key schema (REQUEST)"""

    rsa_passphrase: Optional[str] = None

    @field_validator("rsa_passphrase")
    @classmethod
    def rsa_passphrase_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("rsa_passphrase", v)
        return v


class AccountChangeEOAPasswordRequest(BaseModel):
    """Account Change EOA Password schema (REQUEST)"""

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


class AccountChangeRSAPassphraseRequest(BaseModel):
    """Account Change RSA Passphrase schema (REQUEST)"""

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


class AccountAuthTokenRequest(BaseModel):
    """Account Create Auth Token schema (REQUEST)"""

    valid_duration: int = Field(
        None, ge=0, le=259200
    )  # The maximum valid duration shall be 3 days.


class CreateUpdateChildAccountRequest(BaseModel):
    """Create or update a issuer's child account schema (REQUEST)"""

    personal_information: PersonalInfoInput


class BatchCreateChildAccountRequest(BaseModel):
    """Batch create issuer's child accounts schema (REQUEST)"""

    personal_information_list: list[PersonalInfoInput]


class ListAllChildAccountSortItem(StrEnum):
    child_account_index = "child_account_index"
    child_account_address = "child_account_address"
    name = "name"
    created = "created"
    modified = "modified"


class ListAllChildAccountQuery(BasePaginationQuery):
    child_account_address: Optional[str] = Field(
        None, description="Child account address (partial match)"
    )
    name: Optional[str] = Field(None, description="Child account name (partial match)")
    created_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="Personal information created datetime (From)"
    )
    created_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="Personal information created datetime (To)"
    )
    modified_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="Personal information modified datetime (From)"
    )
    modified_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="Personal information modified datetime (To)"
    )

    sort_item: Optional[ListAllChildAccountSortItem] = Field(
        ListAllChildAccountSortItem.child_account_index, description="Sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC,
        description=SortOrder.__doc__,
    )


############################
# RESPONSE
############################
class AccountResponse(RootModel[Account]):
    """Account schema (Response)"""

    pass


class AccountAuthTokenResponse(BaseModel):
    """Account Auth Token schema (RESPONSE)"""

    auth_token: str
    usage_start: datetime
    valid_duration: int


class CreateChildAccountResponse(BaseModel):
    """Create a issuer's child account schema (RESPONSE)"""

    child_account_index: int


class BatchCreateChildAccountResponse(BaseModel):
    """Batch create issuer's child accounts schema (RESPONSE)"""

    child_account_index_list: list[int]


class ListAllChildAccountResponse(BaseModel):
    """List all child accounts schema (RESPONSE)"""

    result_set: ResultSet
    child_accounts: list[ChildAccount]


class ChildAccountResponse(RootModel[ChildAccount]):
    """Child account schema (Response)"""

    pass
