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
from pydantic import BaseModel


############################
# REQUEST
############################

class AccountChangeRsaKeyRequest(BaseModel):
    """Account Change Rsa Key schema (REQUEST)"""
    rsa_private_key: str
    # TODO: issue#25 'Set KEY_FILE_PASSWORD from the client'
    password: Optional[str]


############################
# RESPONSE
############################

class AccountResponse(BaseModel):
    """Account schema (Response)"""
    issuer_address: str
    rsa_public_key: Optional[str]
