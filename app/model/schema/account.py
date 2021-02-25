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
from pydantic import BaseModel, validator

from app.model.schema.utils import SecureValueUtils


############################
# REQUEST
############################
class AccountCreateKeyRequest(BaseModel):
    """Account Create Key schema (REQUEST)"""
    eoa_password: str

    @validator("eoa_password")
    def eoa_password_is_valid_encrypt(cls, v):
        try:
            SecureValueUtils.decrypt(v)
        except ValueError:
            raise ValueError("eoa_password is not a Base64-decoded encrypted data")
        return v


class AccountChangeRsaKeyRequest(BaseModel):
    """Account Change Rsa Key schema (REQUEST)"""
    # NOTE:
    # rsa_private_key is a long text, but there is a possible of encryption fail when RSA key length is small.
    # So It deals in rsa_private_key at plane text.
    rsa_private_key: str
    passphrase: str

    @validator("passphrase")
    def passphrase_is_valid_encrypt(cls, v):
        try:
            SecureValueUtils.decrypt(v)
        except ValueError:
            raise ValueError("passphrase is not a Base64-decoded encrypted data")
        return v


############################
# RESPONSE
############################

class AccountResponse(BaseModel):
    """Account schema (Response)"""
    issuer_address: str
    rsa_public_key: Optional[str]
