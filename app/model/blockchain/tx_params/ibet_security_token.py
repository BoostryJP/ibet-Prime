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

from pydantic import BaseModel, PositiveInt

from app.model import EthereumAddress


class ForcedTransferParams(BaseModel):
    from_address: EthereumAddress
    to_address: EthereumAddress
    amount: PositiveInt


class BulkTransferParams(BaseModel):
    to_address_list: list[EthereumAddress]
    amount_list: list[PositiveInt]


class AdditionalIssueParams(BaseModel):
    account_address: EthereumAddress
    amount: PositiveInt


class RedeemParams(BaseModel):
    account_address: EthereumAddress
    amount: PositiveInt


class ApproveTransferParams(BaseModel):
    application_id: int
    data: str


class CancelTransferParams(BaseModel):
    application_id: int
    data: str


class LockParams(BaseModel):
    lock_address: EthereumAddress
    value: PositiveInt
    data: str


class ForceLockParams(BaseModel):
    lock_address: EthereumAddress
    account_address: EthereumAddress
    value: PositiveInt
    data: str


class ForceUnlockParams(BaseModel):
    lock_address: EthereumAddress
    account_address: EthereumAddress
    recipient_address: EthereumAddress
    value: PositiveInt
    data: str


class ForceChangeLockedAccountParams(BaseModel):
    lock_address: EthereumAddress
    before_account_address: EthereumAddress
    after_account_address: EthereumAddress
    value: PositiveInt
    data: str
