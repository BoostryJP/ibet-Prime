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
from typing import Optional

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
    cancellation_date: Optional[str] = None
    dividend_record_date: Optional[str] = None
    dividend_payment_date: Optional[str] = None
    dividends: Optional[float] = None
    tradable_exchange_contract_address: Optional[EthereumAddress] = None
    personal_info_contract_address: Optional[EthereumAddress] = None
    transferable: Optional[bool] = None
    status: Optional[bool] = None
    is_offering: Optional[bool] = None
    contact_information: Optional[str] = None
    privacy_policy: Optional[str] = None
    transfer_approval_required: Optional[bool] = None
    principal_value: Optional[int] = None
    is_canceled: Optional[bool] = None
    memo: Optional[str] = None

    @field_validator("dividends")
    @classmethod
    def dividends_13_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**13)
            int_data = int(Decimal(str(v)) * 10**13)
            if not math.isclose(int_data, float_data):
                raise ValueError("dividends must be rounded to 13 decimal places")
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
