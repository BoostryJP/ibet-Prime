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
    Optional, List
)
import math

from pydantic import (
    validator,
    BaseModel
)
from web3 import Web3

from .ibet_security_token import (
    TransferParams as IbetSecurityTokenTransferParams,
    AdditionalIssueParams as IbetSecurityTokenAdditionalIssueParams,
    RedeemParams as IbetSecurityTokenRedeemParams,
    ApproveTransferParams as IbetSecurityTokenApproveTransferParams,
    CancelTransferParams as IbetSecurityTokenCancelTransferParams
)


class UpdateParams(BaseModel):
    face_value: Optional[int]
    interest_rate: Optional[float]
    interest_payment_date: Optional[List[str]]
    redemption_value: Optional[int]
    transferable: Optional[bool]
    status: Optional[bool]
    is_offering: Optional[bool]
    is_redeemed: Optional[bool]
    tradable_exchange_contract_address: Optional[str]
    personal_info_contract_address: Optional[str]
    contact_information: Optional[str]
    privacy_policy: Optional[str]
    transfer_approval_required: Optional[bool]
    memo: Optional[str]

    @validator("interest_rate")
    def interest_rate_4_decimal_places(cls, v):
        if v is not None:
            float_data = float(v * 10 ** 4)
            int_data = int(v * 10 ** 4)
            if not math.isclose(int_data, float_data):
                raise ValueError("interest_rate must be rounded to 4 decimal places")
        return v

    @validator("interest_payment_date")
    def interest_payment_date_list_length_less_than_13(cls, v):
        if v is not None and len(v) >= 13:
            raise ValueError("list length of interest_payment_date must be less than 13")
        return v

    @validator("tradable_exchange_contract_address")
    def tradable_exchange_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("tradable_exchange_contract_address is not a valid address")
        return v

    @validator("personal_info_contract_address")
    def personal_info_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("personal_info_contract_address is not a valid address")
        return v


class TransferParams(IbetSecurityTokenTransferParams):
    pass


class AdditionalIssueParams(IbetSecurityTokenAdditionalIssueParams):
    pass


class RedeemParams(IbetSecurityTokenRedeemParams):
    pass


class ApproveTransferParams(IbetSecurityTokenApproveTransferParams):
    pass


class CancelTransferParams(IbetSecurityTokenCancelTransferParams):
    pass
