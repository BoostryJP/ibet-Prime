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

from pydantic import BaseModel, Field, PositiveInt, RootModel

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


class IbetWSTAuthorization(BaseModel):
    """IbetWST Authorization schema"""

    nonce: str = Field(
        ..., description="Nonce for the authorization (Hexadecimal string)"
    )
    v: int = Field(..., description="v value for the authorization signature")
    r: str = Field(
        ..., description="r value for the authorization signature (Hexadecimal string)"
    )
    s: str = Field(
        ..., description="s value for the authorization signature (Hexadecimal string)"
    )


class IbetWSTTrade(BaseModel):
    """IbetWST Trade schema"""

    index: int = Field(description="Trade index")
    seller_st_account_address: str = Field(description="IbetWST seller account address")
    buyer_st_account_address: str = Field(description="IbetWST buyer account address")
    sc_token_address: str = Field(description="SC token contract address")
    seller_sc_account_address: str = Field(description="SC seller account address")
    buyer_sc_account_address: str = Field(description="SC buyer account address")
    st_value: int = Field(description="Value of IbetWST to trade")
    sc_value: int = Field(description="Value of SC token to trade")
    state: Literal["Pending", "Executed", "Cancelled"] = Field(
        description="Trade state"
    )
    memo: str = Field(description="Memo for the trade")


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


class BurnIbetWSTRequest(BaseModel):
    """BurnIbetWST request schema"""

    value: PositiveInt = Field(description="Amount of IbetWST to burn")
    authorizer: EthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class RequestIbetWSTTradeRequest(BaseModel):
    """RequestIbetWSTTrade request schema"""

    seller_st_account_address: EthereumAddress = Field(
        description="IbetWST seller account address"
    )
    buyer_st_account_address: EthereumAddress = Field(
        description="IbetWST buyer account address"
    )
    sc_token_address: EthereumAddress = Field(description="SC token contract address")
    seller_sc_account_address: EthereumAddress = Field(
        description="SC seller account address"
    )
    buyer_sc_account_address: EthereumAddress = Field(
        description="SC buyer account address"
    )
    st_value: PositiveInt = Field(description="Value of IbetWST to trade")
    sc_value: PositiveInt = Field(description="Value of SC token to trade")
    memo: str = Field(description="Memo for the trade")
    authorizer: EthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class CancelIbetWSTTradeRequest(BaseModel):
    """CancelIbetWSTTrade request schema"""

    index: PositiveInt = Field(description="Trade index")
    authorizer: EthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class AcceptIbetWSTTradeRequest(BaseModel):
    """AcceptIbetWSTTrade request schema"""

    index: PositiveInt = Field(description="Trade index")
    authorizer: EthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class RejectIbetWSTTradeRequest(BaseModel):
    """RejectIbetWSTTrade request schema"""

    index: PositiveInt = Field(description="Trade index")
    authorizer: EthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class ListIbetWSTTradesQuery(BasePaginationQuery):
    """ListIbetWSTTrades request query schema"""

    seller_st_account_address: Optional[EthereumAddress] = Field(
        None, description="IbetWST seller account address"
    )
    buyer_st_account_address: Optional[EthereumAddress] = Field(
        None, description="IbetWST buyer account address"
    )
    sc_token_address: Optional[EthereumAddress] = Field(
        None, description="SC token contract address"
    )
    seller_sc_account_address: Optional[EthereumAddress] = Field(
        None, description="SC seller account address"
    )
    buyer_sc_account_address: Optional[EthereumAddress] = Field(
        None, description="SC buyer account address"
    )
    state: Optional[Literal["Pending", "Executed", "Cancelled"]] = Field(
        None, description="Trade state"
    )


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


class ListIbetWSTTradesResponse(BaseModel):
    """ListIbetWSTTrades response schema"""

    result_set: ResultSet
    trades: list[IbetWSTTrade] = Field(description="List of IbetWST trades")


class GetIbetWSTTradeResponse(RootModel[IbetWSTTrade]):
    """IbetWSTToken response schema"""

    pass
