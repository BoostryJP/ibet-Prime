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
from pydantic import (
    BaseModel,
    validator
)
from web3 import Web3


############################
# REQUEST
############################
class ModifyPersonalInfoRequest(BaseModel):
    """Modify Personal Information schema (REQUEST)"""
    key_manager: str
    name: Optional[str]
    postal_code: Optional[str]
    address: Optional[str]
    email: Optional[str]
    birth: Optional[str]
    is_corporate: Optional[bool]
    tax_category: Optional[int]


class RegisterPersonalInfoRequest(BaseModel):
    """Register Personal Information schema (REQUEST)"""
    account_address: str
    key_manager: str
    name: Optional[str]
    postal_code: Optional[str]
    address: Optional[str]
    email: Optional[str]
    birth: Optional[str]
    is_corporate: Optional[bool]
    tax_category: Optional[int]

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v
