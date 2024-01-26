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

from typing import List

from pydantic import BaseModel

from app.model.schema.base import ResultSet

############################
# REQUEST
############################


############################
# RESPONSE
############################


class IssueRedeemEvent(BaseModel):
    """Issue/Redeem event"""

    transaction_hash: str
    token_address: str
    locked_address: str
    target_address: str
    amount: int
    block_timestamp: str


class IssueRedeemHistoryResponse(BaseModel):
    """Issue/Redeem history"""

    result_set: ResultSet
    history: List[IssueRedeemEvent]
