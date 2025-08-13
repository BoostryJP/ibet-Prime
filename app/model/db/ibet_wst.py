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

from enum import IntEnum, StrEnum
from typing import Literal, TypedDict

from sqlalchemy import JSON, BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IbetWSTVersion(StrEnum):
    V_1 = "1"


############################################################
# Transaction Management
############################################################
class IbetWSTTxType(StrEnum):
    """Transaction Type"""

    DEPLOY = "deploy"
    MINT = "mint"
    BURN = "burn"
    FORCE_BURN = "force_burn"
    ADD_WHITELIST = "add_whitelist"
    DELETE_WHITELIST = "delete_whitelist"
    TRANSFER = "transfer"
    REQUEST_TRADE = "request_trade"
    CANCEL_TRADE = "cancel_trade"
    ACCEPT_TRADE = "accept_trade"
    REJECT_TRADE = "reject_trade"


class IbetWSTTxStatus(IntEnum):
    """Transaction Status"""

    PENDING = 0
    SENT = 1
    SUCCEEDED = 2
    FAILED = 3


class IbetWSTAuthorization(TypedDict):
    nonce: str  # Nonce for the authorization (Hexadecimal string)
    v: int  # v value for the authorization signature
    r: str  # r value for the authorization signature (Hexadecimal string)
    s: str  # s value for the authorization signature (Hexadecimal string)


class IbetWSTTxParamsDeploy(TypedDict):
    """Parameters for IbetWST Deploy Transaction"""

    name: str  # Name of the IbetWST token
    initial_owner: str  # Initial owner of the IbetWST token


class IbetWSTTxParamsAddAccountWhiteList(TypedDict):
    """Parameters for IbetWST addAccountWhiteListWithAuthorization Transaction"""

    st_account: str  # ST account address
    sc_account_in: str  # SC account address for deposits
    sc_account_out: str  # SC account address for withdrawals


class IbetWSTTxParamsDeleteAccountWhiteList(TypedDict):
    """Parameters for IbetWST deleteAccountWhiteListWithAuthorization Transaction"""

    st_account: str  # ST account address to be removed from the whitelist


class IbetWSTTxParamsTransfer(TypedDict):
    """Parameters for IbetWST transferWithAuthorization Transaction"""

    from_address: str  # Address from which the tokens will be transferred
    to_address: str  # Address to which the tokens will be transferred
    value: int  # Amount of IbetWST to be transferred
    valid_after: int  # Timestamp after which the transaction is valid
    valid_before: int  # Timestamp before which the transaction is valid


class IbetWSTTxParamsMint(TypedDict):
    """Parameters for IbetWST mintWithAuthorization Transaction"""

    to_address: str  # Address to which the tokens will be minted
    value: int  # Amount of IbetWST to be minted


class IbetWSTTxParamsBurn(TypedDict):
    """Parameters for IbetWST burnWithAuthorization Transaction"""

    from_address: str  # Address from which the tokens will be burned
    value: int  # Amount of IbetWST to be burned


class IbetWSTTxParamsForceBurn(TypedDict):
    """Parameters for IbetWST forceBurnWithAuthorization Transaction"""

    account: str  # Address from which the tokens will be forcefully burned
    value: int  # Amount of IbetWST to be forcefully burned


class IbetWSTTxParamsRequestTrade(TypedDict):
    """Parameters for IbetWST requestTradeWithAuthorization Transaction"""

    seller_st_account: str  # Seller's IbetWST account address
    buyer_st_account: str  # Buyer's IbetWST account address
    sc_token_address: str  # StableCoin contract address
    st_value: int  # Amount of IbetWST to be traded
    sc_value: int  # Amount of StableCoin to be traded
    memo: str  # Memo for the trade request


class IbetWSTTxParamsCancelTrade(TypedDict):
    """Parameters for IbetWST cancelTradeWithAuthorization Transaction"""

    index: int  # Index of the trade to be cancelled


class IbetWSTTxParamsAcceptTrade(TypedDict):
    """Parameters for IbetWST acceptTradeWithAuthorization Transaction"""

    index: int  # Index of the trade to be accepted


class IbetWSTTxParamsRejectTrade(TypedDict):
    """Parameters for IbetWST rejectTradeWithAuthorization Transaction"""

    index: int  # Index of the trade to be rejected


class IbetWSTEventLogMint(TypedDict):
    """Event log for IbetWST Mint event"""

    to_address: str  # Address to which the tokens were minted
    value: int  # Amount of IbetWST minted


class IbetWSTEventLogBurn(TypedDict):
    """Event log for IbetWST Burn event"""

    from_address: str  # Address from which the tokens were burned
    value: int  # Amount of IbetWST burned


class IbetWSTEventLogAccountWhiteListAdded(TypedDict):
    """Event log for IbetWST AccountWhiteListAdded event"""

    account_address: str  # Address that was added to the whitelist


class IbetWSTEventLogAccountWhiteListDeleted(TypedDict):
    """Event log for IbetWST AccountWhiteListDeleted event"""

    account_address: str  # Address that was removed from the whitelist


class IbetWSTEventLogTransfer(TypedDict):
    """Event log for IbetWST Transfer event"""

    from_address: str  # Address from which the tokens were transferred
    to_address: str  # Address to which the tokens were transferred
    value: int  # Amount of IbetWST transferred


class IbetWSTEventLogTradeRequested(TypedDict):
    """Event log for IbetWST TradeRequested event"""

    index: int  # Index of the trade
    seller_st_account_address: str  # Seller's IbetWST account address
    buyer_st_account_address: str  # Buyer's IbetWST account address
    sc_token_address: str  # StableCoin contract address
    seller_sc_account_address: str  # Seller's StableCoin account address
    buyer_sc_account_address: str  # Buyer's StableCoin account address
    st_value: int  # Amount of IbetWST traded
    sc_value: int  # Amount of StableCoin traded


class IbetWSTEventLogTradeCancelled(TypedDict):
    """Event log for IbetWST TradeCancelled event"""

    index: int  # Index of the trade
    seller_st_account_address: str  # Seller's IbetWST account address
    buyer_st_account_address: str  # Buyer's IbetWST account address
    sc_token_address: str  # StableCoin contract address
    seller_sc_account_address: str  # Seller's StableCoin account address
    buyer_sc_account_address: str  # Buyer's StableCoin account address
    st_value: int  # Amount of IbetWST traded
    sc_value: int  # Amount of StableCoin traded


class IbetWSTEventLogTradeAccepted(TypedDict):
    """Event log for IbetWST TradeAccepted event"""

    index: int  # Index of the trade
    seller_st_account_address: str  # Seller's IbetWST account address
    buyer_st_account_address: str  # Buyer's IbetWST account address
    sc_token_address: str  # StableCoin contract address
    seller_sc_account_address: str  # Seller's StableCoin account address
    buyer_sc_account_address: str  # Buyer's StableCoin account address
    st_value: int  # Amount of IbetWST traded
    sc_value: int  # Amount of StableCoin traded


class IbetWSTEventLogTradeRejected(TypedDict):
    """Event log for IbetWST TradeRejected event"""

    index: int  # Index of the trade
    seller_st_account_address: str  # Seller's IbetWST account address
    buyer_st_account_address: str  # Buyer's IbetWST account address
    sc_token_address: str  # StableCoin contract address
    seller_sc_account_address: str  # Seller's StableCoin account address
    buyer_sc_account_address: str  # Buyer's StableCoin account address
    st_value: int  # Amount of IbetWST traded
    sc_value: int  # Amount of StableCoin traded


class EthIbetWSTTx(Base):
    """Ethereum IbetWST Transaction Management"""

    __tablename__ = "eth_ibet_wst_tx"

    # Transaction ID
    # - Unique identifier for the transaction
    # - Format: UUID4
    tx_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Transaction Type
    tx_type: Mapped[IbetWSTTxType] = mapped_column(String(20), nullable=False)
    # IbetWST Version
    # - Version of the IbetWST contract used for the transaction
    version: Mapped[IbetWSTVersion] = mapped_column(String(2), nullable=False)
    # Transaction status
    # - PENDING: Transaction is created but not yet sent
    # - SENT: Transaction is sent to the Ethereum network
    # - SUCCEEDED: Transaction is mined and succeeded
    # - FAILED: Transaction failed (e.g., due to insufficient gas or revert)
    status: Mapped[IbetWSTTxStatus] = mapped_column(Integer, nullable=False)
    # IbetWST contract address
    # - Address of the IbetWST contract on the Ethereum network
    # - For deploy transactions: The contract address is set when the contract is deployed.
    # - For other transactions: The contract address is set at the time the transaction is instructed.
    ibet_wst_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    # Transaction parameters
    # - JSON object containing the parameters for the transaction
    tx_params: Mapped[
        IbetWSTTxParamsDeploy
        | IbetWSTTxParamsAddAccountWhiteList
        | IbetWSTTxParamsDeleteAccountWhiteList
        | IbetWSTTxParamsTransfer
        | IbetWSTTxParamsMint
        | IbetWSTTxParamsBurn
        | IbetWSTTxParamsForceBurn
        | IbetWSTTxParamsRequestTrade
        | IbetWSTTxParamsCancelTrade
        | IbetWSTTxParamsAcceptTrade
        | IbetWSTTxParamsRejectTrade
    ] = mapped_column(JSON, nullable=False)
    # Transaction sender
    # - Address of the sender who initiated the transaction
    tx_sender: Mapped[str] = mapped_column(String(42), nullable=False)
    # Authorizer
    # - Address of the authorizer who created the authorization for the transaction
    # - This field is set if the transaction requires authorization
    authorizer: Mapped[str | None] = mapped_column(String(42), nullable=True)
    # Authorization data
    # - JSON object containing additional data for authorization
    # - This field is set if the transaction requires authorization
    authorization: Mapped[IbetWSTAuthorization | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    # Client IP address
    # - IP address of the client who initiated the transaction
    # - This field is set when the transaction is executed directly via API call.
    client_ip: Mapped[str | None] = mapped_column(String(40))
    # Transaction hash
    # - Hash of the transaction on the Ethereum network
    # - Set to None if the transaction is not yet sent
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    # Block number
    # - Block number when the transaction was mined
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Gas used
    gas_used: Mapped[int | None] = mapped_column(BigInteger)
    # Block finalized
    # - True if the block is finalized, False otherwise
    finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Event log of the transaction
    # - Set if the transaction emits events and the block is finalized
    # - Not set if the tx_tye is "DEPLOY"
    event_log: Mapped[
        IbetWSTEventLogMint
        | IbetWSTEventLogBurn
        | IbetWSTEventLogAccountWhiteListAdded
        | IbetWSTEventLogAccountWhiteListDeleted
        | IbetWSTEventLogTransfer
        | IbetWSTEventLogTradeRequested
        | IbetWSTEventLogTradeCancelled
        | IbetWSTEventLogTradeAccepted
        | IbetWSTEventLogTradeRejected
        | None
    ] = mapped_column(JSON, nullable=True, default=None)


############################################################
# Trade Management
############################################################
class IDXEthIbetWSTTradeBlockNumber(Base):
    """Synchronized blockNumber of IDXEthIbetWSTTrade"""

    __tablename__ = "idx_eth_ibet_wst_trade_block_number"

    # Record ID
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Synchronized block number
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)


class IDXEthIbetWSTTradeState(StrEnum):
    """IbetWST Trade State"""

    PENDING = "Pending"
    EXECUTED = "Executed"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


class IDXEthIbetWSTTrade(Base):
    """INDEX IbetWST Trade (Ethereum)"""

    __tablename__ = "idx_eth_ibet_wst_trade"

    # IbetWST contract address
    ibet_wst_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # Index of the trade
    index: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Seller's IbetWST account address
    seller_st_account_address: Mapped[str] = mapped_column(
        String(42), nullable=False, index=True
    )
    # Buyer's IbetWST account address
    buyer_st_account_address: Mapped[str] = mapped_column(
        String(42), nullable=False, index=True
    )
    # StableCoin contract address
    sc_token_address: Mapped[str] = mapped_column(
        String(42), nullable=False, index=True
    )
    # Seller's StableCoin account address
    seller_sc_account_address: Mapped[str] = mapped_column(
        String(42), nullable=False, index=True
    )
    # Buyer's StableCoin account address
    buyer_sc_account_address: Mapped[str] = mapped_column(
        String(42), nullable=False, index=True
    )
    # IbetWST trade amount
    st_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # StableCoin trade amount
    sc_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Trade state
    state: Mapped[IDXEthIbetWSTTradeState] = mapped_column(
        String(20), nullable=False, index=True
    )
    # Memo
    memo: Mapped[str] = mapped_column(Text)


############################################################
# Bridge Management
############################################################
class IbetWSTBridgeSyncedBlockNumber(Base):
    """Synchronized block number for IbetWST Bridge"""

    __tablename__ = "ibet_wst_bridge_synced_block_number"

    # Network name
    # - Used to identify the network
    network: Mapped[Literal["ethereum", "ibetfin"]] = mapped_column(
        String(20), primary_key=True
    )
    # Synchronized block number
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)


class IbetBridgeTxParamsForceUnlock(TypedDict):
    """Parameters for ibetfin Force Unlock Transaction"""

    lock_address: str  # Address of the locked account
    account_address: str  # Address of the account to be unlocked
    recipient_address: str  # Address to receive the unlocked tokens
    value: int  # Amount to be unlocked
    data: dict  # Additional data for the transaction


class IbetBridgeTxParamsForceChangeLockedAccount(TypedDict):
    """Parameters for ibetfin Force Change Locked Account Transaction"""

    lock_address: str  # Address of the locked account
    before_account_address: str  # Address of the account before change
    after_account_address: str  # Address of the account after change
    value: int  # Amount to be changed
    data: dict  # Additional data for the transaction


class EthToIbetBridgeTxType(StrEnum):
    """Ethereum to Ibet Bridge Transaction Type"""

    FORCE_UNLOCK = "force_unlock"
    FORCE_CHANGE_LOCKED_ACCOUNT = "force_change_locked_account"


class EthToIbetBridgeTxStatus(IntEnum):
    """Ethereum to Ibet Bridge Transaction Status"""

    PENDING = 0
    SUCCEEDED = 1
    FAILED = 2


class EthToIbetBridgeTx(Base):
    """Ethereum to Ibet Bridge Transaction Management"""

    __tablename__ = "eth_to_ibet_bridge_tx"

    # Transaction ID
    tx_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Token address
    # - Token address on the ibetfin network
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # Transaction type
    tx_type: Mapped[EthToIbetBridgeTxType] = mapped_column(String(30), nullable=False)
    # Transaction status
    status: Mapped[EthToIbetBridgeTxStatus] = mapped_column(Integer, nullable=False)
    # Transaction parameters
    # - JSON object containing the parameters for the transaction
    tx_params: Mapped[
        IbetBridgeTxParamsForceUnlock | IbetBridgeTxParamsForceChangeLockedAccount
    ] = mapped_column(JSON, nullable=False)
    # Transaction sender
    # - Address of the sender who initiated the transaction
    tx_sender: Mapped[str] = mapped_column(String(42), nullable=False)
    # ibet transaction hash
    # - Hash of the transaction on the Ibet network
    # - Set to None if the transaction is not yet sent or not applicable
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    # Block number
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


############################################################
# Whitelist
############################################################
class IDXEthIbetWSTWhitelist(Base):
    """INDEX IbetWST Whitelist (Ethereum)"""

    __tablename__ = "idx_eth_ibet_wst_whitelist"

    # IbetWST contract address
    ibet_wst_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # ST account address
    st_account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # SC account address for deposits
    sc_account_address_in: Mapped[str] = mapped_column(String(42), nullable=False)
    # SC account address for withdrawals
    sc_account_address_out: Mapped[str] = mapped_column(String(42), nullable=False)
