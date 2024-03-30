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

import math
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.model import EthereumAddress

from .ibet_security_token import (
    AdditionalIssueParams as IbetSecurityTokenAdditionalIssueParams,
    ApproveTransferParams as IbetSecurityTokenApproveTransferParams,
    BulkTransferParams as IbetSecurityTokenBulkTransferParams,
    CancelTransferParams as IbetSecurityTokenCancelTransferParams,
    ForceUnlockParams as IbetSecurityTokenForceUnlockParams,
    LockParams as IbetSecurityTokenLockParams,
    RedeemParams as IbetSecurityTokenRedeemParams,
    TransferParams as IbetSecurityTokenTransferParams,
)


class UpdateParams(BaseModel):
    face_value: Optional[int] = None
    face_value_currency: Optional[str] = None
    interest_rate: Optional[float] = None
    interest_payment_date: Optional[List[str]] = None
    interest_payment_currency: Optional[str] = None
    redemption_value: Optional[int] = None
    redemption_value_currency: Optional[str] = None
    base_fx_rate: Optional[float] = None
    transferable: Optional[bool] = None
    status: Optional[bool] = None
    is_offering: Optional[bool] = None
    is_redeemed: Optional[bool] = None
    tradable_exchange_contract_address: Optional[EthereumAddress] = None
    personal_info_contract_address: Optional[EthereumAddress] = None
    contact_information: Optional[str] = None
    privacy_policy: Optional[str] = None
    transfer_approval_required: Optional[bool] = None
    memo: Optional[str] = None

    @field_validator("base_fx_rate")
    @classmethod
    def base_fx_rate_6_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**6)
            int_data = int(Decimal(str(v)) * 10**6)
            if not math.isclose(int_data, float_data):
                raise ValueError("base_fx_rate must be rounded to 6 decimal places")
        return v

    @field_validator("interest_rate")
    @classmethod
    def interest_rate_4_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**4)
            int_data = int(Decimal(str(v)) * 10**4)
            if not math.isclose(int_data, float_data):
                raise ValueError("interest_rate must be rounded to 4 decimal places")
        return v

    @field_validator("interest_payment_date")
    @classmethod
    def interest_payment_date_list_length_less_than_13(cls, v):
        if v is not None and len(v) >= 13:
            raise ValueError(
                "list length of interest_payment_date must be less than 13"
            )
        return v


class TransferParams(IbetSecurityTokenTransferParams):
    pass


class BulkTransferParams(IbetSecurityTokenBulkTransferParams):
    pass


class AdditionalIssueParams(IbetSecurityTokenAdditionalIssueParams):
    pass


class RedeemParams(IbetSecurityTokenRedeemParams):
    pass


class ApproveTransferParams(IbetSecurityTokenApproveTransferParams):
    pass


class CancelTransferParams(IbetSecurityTokenCancelTransferParams):
    pass


class LockParams(IbetSecurityTokenLockParams):
    pass


class ForceUnlockPrams(IbetSecurityTokenForceUnlockParams):
    pass
