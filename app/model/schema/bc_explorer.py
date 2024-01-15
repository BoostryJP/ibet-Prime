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
from typing import Annotated, Optional

from fastapi import Query
from pydantic import BaseModel, Field, NonNegativeInt, RootModel
from pydantic.dataclasses import dataclass

from app.model import EthereumAddress

from .base import ResultSet, SortOrder

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
    to_address: Optional[str] = Field(...)


class TxDataDetail(BaseModel):
    hash: str = Field(description="Transaction hash")
    block_hash: str
    block_number: NonNegativeInt
    transaction_index: NonNegativeInt
    from_address: str
    to_address: Optional[str] = Field(...)
    contract_name: Optional[str] = Field(...)
    contract_function: Optional[str] = Field(...)
    contract_parameters: Optional[dict] = Field(...)
    gas: NonNegativeInt
    gas_price: NonNegativeInt
    value: NonNegativeInt
    nonce: NonNegativeInt


############################
# REQUEST
############################


@dataclass
class ListBlockDataQuery:
    offset: Annotated[
        Optional[NonNegativeInt], Query(description="start position")
    ] = None
    limit: Annotated[
        Optional[NonNegativeInt], Query(description="number of set")
    ] = None
    from_block_number: Annotated[Optional[NonNegativeInt], Query()] = None
    to_block_number: Annotated[Optional[NonNegativeInt], Query()] = None
    sort_order: Annotated[
        Optional[SortOrder], Query(description="sort order(0: ASC, 1: DESC)")
    ] = SortOrder.ASC


@dataclass
class ListTxDataQuery:
    offset: Annotated[
        Optional[NonNegativeInt], Query(description="start position")
    ] = None
    limit: Annotated[
        Optional[NonNegativeInt], Query(description="number of set")
    ] = None
    block_number: Annotated[
        Optional[NonNegativeInt], Query(description="block number")
    ] = None
    from_address: Annotated[
        Optional[EthereumAddress], Query(description="tx from")
    ] = None
    to_address: Annotated[Optional[EthereumAddress], Query(description="tx to")] = None


############################
# RESPONSE
############################


class BlockDataResponse(RootModel[BlockDataDetail]):
    pass


class BlockDataListResponse(BaseModel):
    result_set: ResultSet
    block_data: list[BlockData]


class TxDataResponse(RootModel[TxDataDetail]):
    pass


class TxDataListResponse(BaseModel):
    result_set: ResultSet
    tx_data: list[TxData]
