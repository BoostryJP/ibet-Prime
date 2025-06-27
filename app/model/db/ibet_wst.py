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
    ADD_WHITELIST = "add_whitelist"
    DELETE_WHITELIST = "delete_whitelist"
    REQUEST_TRADE = "request_trade"
    CANCEL_TRADE = "cancel_trade"
    ACCEPT_TRADE = "accept_trade"


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
    # - This field is set if the transaction is for the deployed IbetWST contract
    ibet_wst_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    # Transaction parameters
    # - JSON object containing the parameters for the transaction
    tx_params: Mapped[dict] = mapped_column(JSON, nullable=False)
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
    # Transaction hash
    # - Hash of the transaction on the Ethereum network
    # - Set to None if the transaction is not yet sent
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    # Block number
    # - Block number when the transaction was mined
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Block finalized
    # - True if the block is finalized, False otherwise
    finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


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
    tx_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Transaction sender
    # - Address of the sender who initiated the transaction
    tx_sender: Mapped[str] = mapped_column(String(42), nullable=False)
    # ibet transaction hash
    # - Hash of the transaction on the Ibet network
    # - Set to None if the transaction is not yet sent or not applicable
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    # Block number
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
