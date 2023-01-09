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
from pydantic import (
    validator,
    BaseModel
)
from web3 import Web3


class TransferParams(BaseModel):
    from_address: str
    to_address: str
    amount: int

    @validator("from_address")
    def from_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("from_address is not a valid address")
        return v

    @validator("to_address")
    def to_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("to_address is not a valid address")
        return v


class AdditionalIssueParams(BaseModel):
    account_address: str
    amount: int

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v


class RedeemParams(BaseModel):
    account_address: str
    amount: int

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v


class ApproveTransferParams(BaseModel):
    application_id: int
    data: str


class CancelTransferParams(BaseModel):
    application_id: int
    data: str
