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

from pydantic import BaseModel

class IbetStandardTokenInterface(BaseModel):
    """Standard Token Interface schema"""
    issuer_address: str
    name: str
    symbol: str
    total_supply: int
    image_url: Optional[Dict[str, str]]
    contact_information: Optional[str]
    privacy_policy: Optional[str]


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
    certification: Optional[str]
    initial_offering_status: Optional[bool]
    is_redeemed: Optional[bool]
