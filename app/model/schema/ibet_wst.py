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

from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.model import EthereumAddress
from app.model.schema.base import (
    BasePaginationQuery,
    IbetShare,
    IbetStraightBond,
    ResultSet,
    SortOrder,
    TokenType,
)


############################
# COMMON
############################
class IbetWSTToken(BaseModel):
    """IbetWST Token schema"""

    issuer_address: str = Field(description="Issuer address")
    ibet_wst_address: str = Field(description="IbetWST contract address")
    ibet_token_address: str = Field(description="ibet token contract address")
    ibet_token_type: TokenType = Field(description="ibet token type")
    ibet_token_attributes: IbetStraightBond | IbetShare = Field(
        description="ibet token attributes"
    )
    created: str = Field(description="Created datetime")


############################
# REQUEST
############################
class ListAllIbetWSTTokensSortItem(StrEnum):
    CREATED = "created"
    TOKEN_ADDRESS = "token_address"


class ListAllIbetWSTTokensQuery(BasePaginationQuery):
    """ListAllIbetWSTTokens request query schema"""

    issuer_address: Optional[EthereumAddress] = Field(
        None, description="Issuer address (**This affects total number**)"
    )
    ibet_wst_address: Optional[EthereumAddress] = Field(
        None, description="IbetWST contract address"
    )
    ibet_token_address: Optional[EthereumAddress] = Field(
        None, description="ibet token contract address"
    )
    token_type: Optional[TokenType] = Field(None, description="Token type")

    sort_item: Optional[ListAllIbetWSTTokensSortItem] = Field(
        ListAllIbetWSTTokensSortItem.CREATED
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class AddIbetWSTWhitelistRequest(BaseModel):
    """AddIbetWSTWhitelist request schema"""

    account_address: EthereumAddress = Field(description="Account address to whitelist")


class DeleteIbetWSTWhitelistRequest(BaseModel):
    """DeleteIbetWSTWhitelist request schema"""

    account_address: EthereumAddress = Field(description="Account address to whitelist")


############################
# RESPONSE
############################
class IbetWSTTransactionResponse(BaseModel):
    """Common response schema for APIs that send IbetWST transactions"""

    tx_id: str = Field(..., description="Transaction ID")


class ListAllIbetWSTTokensResponse(BaseModel):
    """ListAllIbetWSTTokens response schema"""

    result_set: ResultSet
    tokens: list[IbetWSTToken]


class GetIbetWSTBalanceResponse(BaseModel):
    """GetIbetWSTBalance response schema"""

    balance: int = Field(..., description="IbetWST balance")


class GetIbetWSTTransactionResponse(BaseModel):
    """GetIbetWSTTransaction response schema"""

    tx_id: str = Field(description="Transaction ID")
    tx_type: Literal[
        "deploy",
        "mint",
        "burn",
        "add_whitelist",
        "delete_whitelist",
        "request_trade",
        "cancel_trade",
        "accept_trade",
    ] = Field(description="Transaction type")
    version: str = Field(description="IbetWST version")
    status: Literal[0, 1, 2, 3] = Field(
        description="Transaction status(0: PENDING, 1: SENT, 2: SUCCEEDED, 3: FAILED)"
    )
    ibet_wst_address: Optional[str] = Field(..., description="IbetWST contract address")
    tx_sender: str = Field(description="Transaction sender address")
    authorizer: Optional[str] = Field(..., description="Authorizer address")
    tx_hash: Optional[str] = Field(..., description="Transaction hash")
    block_number: Optional[int] = Field(
        ..., description="Block number when transaction was mined"
    )
    finalized: bool = Field(
        description="True if the block is finalized, False otherwise"
    )


class GetIbetWSTWhitelistResponse(BaseModel):
    """GetIbetWSTWhitelist response schema"""

    whitelisted: bool = Field(
        description="True if the account is whitelisted, False otherwise"
    )
