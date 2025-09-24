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

from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field, PositiveInt, RootModel

from app.model import ChecksumEthereumAddress, ValidatedDatetimeStr
from app.model.schema.base import (
    BasePaginationQuery,
    IbetShare,
    IbetStraightBond,
    ResultSet,
    SortOrder,
    TokenType,
)
from app.model.schema.personal_info import PersonalInfo


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


IbetWSTTxType = Literal[
    "deploy",
    "mint",
    "burn",
    "force_burn",
    "add_whitelist",
    "delete_whitelist",
    "transfer",
    "request_trade",
    "cancel_trade",
    "accept_trade",
    "reject_trade",
]


class IbetWSTTxStatus(IntEnum):
    """IbetWST Transaction Status Enum"""

    PENDING = 0
    SENT = 1
    SUCCEEDED = 2
    FAILED = 3


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

    issuer_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="Issuer address (**This affects total number**)"
    )
    ibet_wst_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="IbetWST contract address"
    )
    ibet_token_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="ibet token contract address"
    )
    token_type: Optional[TokenType] = Field(None, description="Token type")

    sort_item: Optional[ListAllIbetWSTTokensSortItem] = Field(
        ListAllIbetWSTTokensSortItem.CREATED
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class ListIbetWSTTransactionsQuery(BasePaginationQuery):
    """ListIbetWSTTransactions request query schema"""

    ibet_wst_address: ChecksumEthereumAddress = Field(
        description="IbetWST contract address (**This affects total number**) "
    )
    tx_id: Optional[str] = Field(None, description="Transaction ID")
    tx_type: Optional[IbetWSTTxType] = Field(None, description="Transaction type")
    status: Optional[IbetWSTTxStatus] = Field(
        None,
        description="Transaction status (0: PENDING, 1: SENT, 2: SUCCEEDED, 3: FAILED)",
    )
    tx_hash: Optional[str] = Field(None, description="Transaction hash")
    authorizer: Optional[ChecksumEthereumAddress] = Field(
        None, description="Authorizer address"
    )
    finalized: Optional[bool] = Field(
        None, description="True if the block is finalized, False otherwise"
    )
    created_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (From)"
    )
    created_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (To)"
    )


class AddIbetWSTWhitelistRequest(BaseModel):
    """AddIbetWSTWhitelist request schema"""

    st_account_address: ChecksumEthereumAddress = Field(
        description="ST account address to be added to the whitelist"
    )
    sc_account_address_in: ChecksumEthereumAddress = Field(
        description="SC account address for deposits"
    )
    sc_account_address_out: ChecksumEthereumAddress = Field(
        description="SC account address for withdrawals"
    )


class DeleteIbetWSTWhitelistRequest(BaseModel):
    """DeleteIbetWSTWhitelist request schema"""

    st_account_address: ChecksumEthereumAddress = Field(
        description="ST account address to be removed from the whitelist"
    )


class BurnIbetWSTRequest(BaseModel):
    """BurnIbetWST request schema"""

    value: PositiveInt = Field(description="Amount of IbetWST to burn")
    authorizer: ChecksumEthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class ForceBurnIbetWSTRequest(BaseModel):
    """ForceBurnIbetWST request schema"""

    account_address: ChecksumEthereumAddress = Field(
        description="Account address from which to force burn IbetWST"
    )
    value: PositiveInt = Field(description="Amount of IbetWST to force burn")


class TransferIbetWSTRequest(BaseModel):
    """TransferIbetWST request schema"""

    from_address: ChecksumEthereumAddress = Field(description="Sender address")
    to_address: ChecksumEthereumAddress = Field(description="Recipient address")
    value: PositiveInt = Field(description="Amount of IbetWST to transfer")
    valid_after: PositiveInt = Field(
        default=1, description="Valid after timestamp (Unix time)"
    )
    valid_before: PositiveInt = Field(
        default=2**64 - 1,
        description="Valid before timestamp (Unix time)",
        le=2**64 - 1,
    )
    authorizer: ChecksumEthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class RequestIbetWSTTradeRequest(BaseModel):
    """RequestIbetWSTTrade request schema"""

    seller_st_account_address: ChecksumEthereumAddress = Field(
        description="IbetWST seller account address"
    )
    buyer_st_account_address: ChecksumEthereumAddress = Field(
        description="IbetWST buyer account address"
    )
    sc_token_address: ChecksumEthereumAddress = Field(
        description="SC token contract address"
    )
    st_value: PositiveInt = Field(description="Value of IbetWST to trade")
    sc_value: PositiveInt = Field(description="Value of SC token to trade")
    memo: str = Field(description="Memo for the trade")
    authorizer: ChecksumEthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class CancelIbetWSTTradeRequest(BaseModel):
    """CancelIbetWSTTrade request schema"""

    index: PositiveInt = Field(description="Trade index")
    authorizer: ChecksumEthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class AcceptIbetWSTTradeRequest(BaseModel):
    """AcceptIbetWSTTrade request schema"""

    index: PositiveInt = Field(description="Trade index")
    authorizer: ChecksumEthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class RejectIbetWSTTradeRequest(BaseModel):
    """RejectIbetWSTTrade request schema"""

    index: PositiveInt = Field(description="Trade index")
    authorizer: ChecksumEthereumAddress = Field(description="Authorizer address")
    authorization: IbetWSTAuthorization = Field(
        description="Authorization for the transaction"
    )


class ListIbetWSTTradesQuery(BasePaginationQuery):
    """ListIbetWSTTrades request query schema"""

    seller_st_account_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="IbetWST seller account address"
    )
    buyer_st_account_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="IbetWST buyer account address"
    )
    sc_token_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="SC token contract address"
    )
    seller_sc_account_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="SC seller account address"
    )
    buyer_sc_account_address: Optional[ChecksumEthereumAddress] = Field(
        None, description="SC buyer account address"
    )
    state: Optional[Literal["Pending", "Executed", "Cancelled"]] = Field(
        None, description="Trade state"
    )


class GetERC20BalanceQuery(BaseModel):
    """GetERC20Balance request query schema"""

    token_address: ChecksumEthereumAddress = Field(
        description="Token contract address to check balance"
    )
    account_address: ChecksumEthereumAddress = Field(
        description="Account address to check balance"
    )


class GetERC20AllowanceQuery(BaseModel):
    """GetERC20Allowance request query schema"""

    token_address: ChecksumEthereumAddress = Field(
        description="Token contract address to check allowance"
    )
    account_address: ChecksumEthereumAddress = Field(
        description="Account address to check allowance"
    )
    spender_address: ChecksumEthereumAddress = Field(
        description="Spender address to check allowance"
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


class IbetWSTEventLogMint(BaseModel):
    """IbetWST Mint event log schema"""

    to_address: ChecksumEthereumAddress = Field(
        ..., description="Address to which the tokens were minted"
    )
    value: int = Field(..., description="Amount of tokens minted")


class IbetWSTEventLogBurn(BaseModel):
    """IbetWST Burn event log schema"""

    from_address: ChecksumEthereumAddress = Field(
        ..., description="Address from which the tokens were burned"
    )
    value: int = Field(..., description="Amount of tokens burned")


class IbetWSTEventLogTransfer(BaseModel):
    """IbetWST Transfer event log schema"""

    from_address: ChecksumEthereumAddress = Field(
        ..., description="Address from which the tokens were transferred"
    )
    to_address: ChecksumEthereumAddress = Field(
        ..., description="Address to which the tokens were transferred"
    )
    value: int = Field(..., description="Amount of tokens transferred")


class IbetWSTEventLogAccountWhiteList(BaseModel):
    """IbetWST AccountWhiteList event log schema"""

    account_address: ChecksumEthereumAddress = Field(
        ..., description="Address of the account added to/removed from the whitelist"
    )


class IbetWSTEventLogTrade(BaseModel):
    """IbetWST TradeRequested/TradeCancelled/TradeAccepted/TradeRejected event log schema"""

    index: int = Field(..., description="Trade index")
    seller_st_account_address: ChecksumEthereumAddress = Field(
        ..., description="IbetWST seller account address"
    )
    buyer_st_account_address: ChecksumEthereumAddress = Field(
        ..., description="IbetWST buyer account address"
    )
    sc_token_address: ChecksumEthereumAddress = Field(
        ..., description="SC token contract address"
    )
    seller_sc_account_address: ChecksumEthereumAddress = Field(
        ..., description="SC seller account address"
    )
    buyer_sc_account_address: ChecksumEthereumAddress = Field(
        ..., description="SC buyer account address"
    )
    st_value: int = Field(..., description="Value of IbetWST to trade")
    sc_value: int = Field(..., description="Value of SC token to trade")
    display_sc_value: Decimal = Field(
        ..., description="Value of SC token to trade (decimals considered)"
    )
    sc_decimals: int = Field(..., description="Decimals of the SC token")


class GetIbetWSTTransactionResponse(BaseModel):
    """GetIbetWSTTransaction response schema"""

    tx_id: str = Field(description="Transaction ID")
    tx_type: IbetWSTTxType = Field(description="Transaction type")
    version: str = Field(description="IbetWST version")
    status: IbetWSTTxStatus = Field(
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
    event_log: Optional[
        IbetWSTEventLogMint
        | IbetWSTEventLogBurn
        | IbetWSTEventLogTransfer
        | IbetWSTEventLogAccountWhiteList
        | IbetWSTEventLogTrade
    ] = Field(None, description="Event log for the transaction (if applicable)")
    created: str = Field(description="Transaction created datetime")


class ListIbetWSTTransactionsResponse(BaseModel):
    """ListIbetWSTTransactions response schema"""

    result_set: ResultSet
    transactions: list[GetIbetWSTTransactionResponse] = Field(
        description="List of IbetWST transactions"
    )


class IbetWSTWhitelistAccount(BaseModel):
    """IbetWST Whitelist Account schema"""

    st_account_address: ChecksumEthereumAddress = Field(
        description="ST account address of the whitelisted account"
    )
    sc_account_address_in: ChecksumEthereumAddress = Field(
        description="SC account address for deposits"
    )
    sc_account_address_out: ChecksumEthereumAddress = Field(
        description="SC account address for withdrawals"
    )


class IbetWSTWhitelistAccountWithPersonalInfo(BaseModel):
    """IbetWST Whitelist Account schema"""

    st_account_address: ChecksumEthereumAddress = Field(
        description="ST account address of the whitelisted account"
    )
    st_account_personal_info: PersonalInfo | None = Field(
        description="Personal information of the ST account"
    )
    sc_account_address_in: ChecksumEthereumAddress = Field(
        description="SC account address for deposits"
    )
    sc_account_address_out: ChecksumEthereumAddress = Field(
        description="SC account address for withdrawals"
    )


class RetrieveIbetWSTWhitelistAccountsResponse(BaseModel):
    """RetrieveIbetWSTWhitelistAccounts response schema"""

    whitelist_accounts: list[IbetWSTWhitelistAccount] = Field(
        description="List of whitelisted accounts"
    )


class RetrieveIbetWSTWhitelistAccountsWithPersonalInfoResponse(BaseModel):
    """RetrieveIbetWSTWhitelistAccountsWithPersonalInfo response schema"""

    whitelist_accounts: list[IbetWSTWhitelistAccountWithPersonalInfo] = Field(
        description="List of whitelisted accounts with personal information"
    )


class GetIbetWSTWhitelistResponse(BaseModel):
    """GetIbetWSTWhitelist response schema"""

    st_account_address: str = Field(
        description="ST account address of the whitelisted account"
    )
    sc_account_address_in: str = Field(description="SC account address for deposits")
    sc_account_address_out: str = Field(
        description="SC account address for withdrawals"
    )
    listed: bool = Field(
        description="True if the account is listed in the whitelist, False otherwise"
    )


class GetIbetWSTWhitelistWithPersonalInfoResponse(BaseModel):
    """GetIbetWSTWhitelistWithPersonalInfo response schema"""

    st_account_address: str = Field(
        description="ST account address of the whitelisted account"
    )
    st_account_personal_info: PersonalInfo | None = Field(
        description="Personal information of the ST account"
    )
    sc_account_address_in: str = Field(description="SC account address for deposits")
    sc_account_address_out: str = Field(
        description="SC account address for withdrawals"
    )
    listed: bool = Field(
        description="True if the account is listed in the whitelist, False otherwise"
    )


class ListIbetWSTTradesResponse(BaseModel):
    """ListIbetWSTTrades response schema"""

    result_set: ResultSet
    trades: list[IbetWSTTrade] = Field(description="List of IbetWST trades")


class GetIbetWSTTradeResponse(RootModel[IbetWSTTrade]):
    """IbetWSTToken response schema"""

    pass


class GetERC20BalanceResponse(BaseModel):
    """GetERC20Balance response schema"""

    balance: int = Field(..., description="ERC20 token balance")


class GetERC20AllowanceResponse(BaseModel):
    """GetERC20Allowance response schema"""

    allowance: int = Field(..., description="ERC20 token allowance")
