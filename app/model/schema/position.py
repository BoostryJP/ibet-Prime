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

from .types import ResultSet
from app.model.db import TokenType


############################
# REQUEST
############################


############################
# RESPONSE
############################

class PositionResponse(BaseModel):
    """Position schema (Response)"""
    issuer_address: str
    token_address: str
    token_type: TokenType
    token_name: str
    balance: int
    exchange_balance: int
    exchange_commitment: int
    pending_transfer: int
    locked: int


class ListAllPositionResponse(BaseModel):
    """List All Position schema (Response)"""
    result_set: ResultSet
    positions: List[PositionResponse]


class LockedPosition(BaseModel):
    """Locked Position"""
    issuer_address: str
    token_address: str
    token_type: TokenType
    token_name: str
    lock_address: str
    locked: int


class ListAllLockedPositionResponse(BaseModel):
    """List All Locked Position schema (Response)"""
    result_set: ResultSet
    locked_positions: List[LockedPosition]
