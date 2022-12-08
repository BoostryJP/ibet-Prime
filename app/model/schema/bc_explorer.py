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
from typing import Optional

from fastapi import Query
from pydantic import (
    BaseModel,
    Field,
    NonNegativeInt,
    validator
)
from pydantic.dataclasses import dataclass
from web3 import Web3

from .types import ResultSet


############################
# COMMON
############################

class BlockData(BaseModel):
    number: NonNegativeInt = Field(description="Block number")
    hash: str = Field(description="Block hash")
    transactions: list[str] = Field(description="Transaction list")
    timestamp: int
    gas_limit: int
    gas_used: int
    size: NonNegativeInt

class BlockDataDetail(BaseModel):
    number: NonNegativeInt = Field(description="Block number")
    parent_hash: str
    sha3_uncles: str
    miner: str
    state_root: str
    transactions_root: str
    receipts_root: str
    logs_bloom: str
    difficulty: int
    gas_limit: int
    gas_used: int
    timestamp: int
    proof_of_authority_data: str
    mix_hash: str
    nonce: str
    hash: str = Field(description="Block hash")
    size: NonNegativeInt
    transactions: list[str] = Field(description="Transaction list")

class TxData(BaseModel):
    hash: str = Field(description="Transaction hash")
    block_hash: str
    block_number: NonNegativeInt
    transaction_index: NonNegativeInt
    from_address: str
    to_address: Optional[str]

class TxDataDetail(BaseModel):
    hash: str = Field(description="Transaction hash")
    block_hash: str
    block_number: NonNegativeInt
    transaction_index: NonNegativeInt
    from_address: str
    to_address: Optional[str]
    contract_name: Optional[str]
    contract_function: Optional[str]
    contract_parameters: Optional[dict]
    gas: NonNegativeInt
    gas_price: NonNegativeInt
    value: NonNegativeInt
    nonce: NonNegativeInt

############################
# REQUEST
############################

@dataclass
class ListBlockDataQuery:
    offset: Optional[NonNegativeInt] = Query(default=None, description="start position")
    limit: Optional[NonNegativeInt] = Query(default=None, description="number of set")
    from_block_number: Optional[NonNegativeInt] = Query(default=None)
    to_block_number: Optional[NonNegativeInt] = Query(default=None)

@dataclass
class ListTxDataQuery:
    offset: Optional[NonNegativeInt] = Query(default=None, description="start position")
    limit: Optional[NonNegativeInt] = Query(default=None, description="number of set")
    block_number: Optional[NonNegativeInt] = Query(default=None, description="block number")
    from_address: Optional[str] = Query(default=None, description="tx from")
    to_address: Optional[str] = Query(default=None, description="tx to")

    @validator("from_address")
    def from_address_is_valid_address(cls, v):
        if v is not None:
            if not Web3.isAddress(v):
                raise ValueError("from_address is not a valid address")
        return v

    @validator("to_address")
    def to_address_is_valid_address(cls, v):
        if v is not None:
            if not Web3.isAddress(v):
                raise ValueError("to_address is not a valid address")
        return v

############################
# RESPONSE
############################

class BlockDataResponse(BaseModel):
    __root__: BlockDataDetail

class BlockDataListResponse(BaseModel):
    result_set: ResultSet
    block_data: list[BlockData]

class TxDataResponse(BaseModel):
    __root__: TxDataDetail

class TxDataListResponse(BaseModel):
    result_set: ResultSet
    tx_data: list[TxData]
