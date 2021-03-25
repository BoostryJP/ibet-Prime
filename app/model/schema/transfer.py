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

from .result_set import ResultSet


############################
# RESPONSE
############################

class TransferResponse(BaseModel):
    """transfer data"""
    transaction_hash: str
    token_address: str
    from_address: str
    to_address: str
    amount: int
    block_timestamp: str


class TransferHistoryResponse(BaseModel):
    """transfer history"""
    result_set: ResultSet
    transfer_history: List[TransferResponse]
