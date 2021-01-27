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
from typing import Dict, List, Optional
import math

from pydantic import BaseModel, validator
from web3 import Web3


class IbetStandardTokenInterface(BaseModel):
    """Standard Token Interface schema"""
    issuer_address: str
    name: str
    symbol: str
    total_supply: int
    image_url: Optional[List[Dict[str, str]]]
    contact_information: Optional[str]
    privacy_policy: Optional[str]
    tradable_exchange_contract_address: Optional[str]
    status: Optional[bool]

    @validator("issuer_address")
    def issuer_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("issuer_address is not a valid address")
        return v

    @validator("tradable_exchange_contract_address")
    def tradable_exchange_contract_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("tradable_exchange_contract_address is not a valid address")
        return v


class IbetStraightBond(IbetStandardTokenInterface):
    """ibet Straight Bond schema"""
    face_value: int
    redemption_date: str
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    interest_rate: Optional[float]
    interest_payment_date: Optional[List[str]]
    transferable: Optional[bool]
    initial_offering_status: Optional[bool]
    is_redeemed: Optional[bool]
    personal_info_contract_address: Optional[str]

    @validator("interest_rate")
    def interest_rate_4_decimal_places(cls, v):
        float_data = float(v * 10 ** 4)
        int_data = int(v * 10 ** 4)
        if not math.isclose(int_data, float_data):
            raise ValueError("interest_rate must be less than or equal to four decimal places")
        return v

    @validator("personal_info_contract_address")
    def personal_info_contract_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("personal_info_contract_address is not a valid address")
        return v
