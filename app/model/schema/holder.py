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
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .personal_info import PersonalInfo


############################
# RESPONSE
############################
class HolderResponse(BaseModel):
    """Holder schema (Response)"""

    account_address: str
    personal_information: PersonalInfo
    balance: int
    exchange_balance: int
    exchange_commitment: int
    pending_transfer: int
    locked: int
    modified: Optional[datetime]


class HolderCountResponse(BaseModel):
    """Holder count schema (Response)"""

    count: int
