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
    Optional
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
    cancellation_date: Optional[str]
    dividend_record_date: Optional[str]
    dividend_payment_date: Optional[str]
    dividends: Optional[float]
    tradable_exchange_contract_address: Optional[str]
    personal_info_contract_address: Optional[str]
    transferable: Optional[bool]
    status: Optional[bool]
    is_offering: Optional[bool]
    contact_information: Optional[str]
    privacy_policy: Optional[str]
    transfer_approval_required: Optional[bool]
    principal_value: Optional[int]
    is_canceled: Optional[bool]
    memo: Optional[str]

    @validator("dividends")
    def dividends_13_decimal_places(cls, v):
        if v is not None:
            float_data = float(v * 10 ** 13)
            int_data = int(v * 10 ** 13)
            if not math.isclose(int_data, float_data):
                raise ValueError("dividends must be rounded to 13 decimal places")
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
