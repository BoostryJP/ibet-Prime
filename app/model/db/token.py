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

from datetime import datetime
from enum import IntEnum, StrEnum

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, naive_utcnow
from .ibet_wst import IbetWSTVersion


class TokenType(StrEnum):
    IBET_STRAIGHT_BOND = "IbetStraightBond"
    IBET_SHARE = "IbetShare"


class TokenVersion(StrEnum):
    V_22_12 = "22_12"
    V_23_12 = "23_12"
    V_24_06 = "24_06"
    V_24_09 = "24_09"
    V_25_06 = "25_06"
    V_25_09 = "25_09"


class TokenStatus(IntEnum):
    PENDING = 0
    SUCCEEDED = 1
    FAILED = 2


class IbetWSTBlockchain(StrEnum):
    ETHEREUM = "ethereum"
    AVALANCHE = "avalanche"


type IbetWSTActivatedStatusByBlockchain = dict[IbetWSTBlockchain, bool]
type IbetWSTDeployedStatusByBlockchain = dict[IbetWSTBlockchain, bool]
type IbetWSTAddressByBlockchain = dict[IbetWSTBlockchain, str]


class Token(Base):
    """Issued Token"""

    __tablename__ = "token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token type
    type: Mapped[TokenType] = mapped_column(String(40), nullable=False)
    # transaction hash
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=True)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=True)
    # contract version
    version: Mapped[TokenVersion] = mapped_column(String(5), nullable=False)
    # contract ABI
    abi: Mapped[dict] = mapped_column(JSON, nullable=False)
    # token processing status (pending:0, succeeded:1, failed:2)
    token_status: Mapped[TokenStatus | None] = mapped_column(
        Integer, default=TokenStatus.SUCCEEDED
    )
    # initial position synced
    initial_position_synced: Mapped[bool | None] = mapped_column(Boolean, default=False)

    # IbetWST activated by blockchain
    ibet_wst_activated_by_blockchain: Mapped[
        IbetWSTActivatedStatusByBlockchain | None
    ] = mapped_column(JSON, nullable=True)
    # IbetWST deployed by blockchain
    ibet_wst_deployed_by_blockchain: Mapped[
        IbetWSTDeployedStatusByBlockchain | None
    ] = mapped_column(JSON, nullable=True)
    # IbetWST contract address by blockchain
    ibet_wst_address_by_blockchain: Mapped[IbetWSTAddressByBlockchain | None] = (
        mapped_column(JSON, nullable=True)
    )
    # IbetWST version
    ibet_wst_version: Mapped[IbetWSTVersion | None] = mapped_column(
        String(2), nullable=True
    )
    # IbetWST name
    ibet_wst_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # IbetWST transaction ID
    # - This is the transaction ID of the IbetWST contract deployment
    ibet_wst_tx_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    @staticmethod
    def _normalize_ibet_wst_blockchain(
        blockchain: IbetWSTBlockchain | str,
    ) -> IbetWSTBlockchain:
        return IbetWSTBlockchain(str(blockchain))

    def set_ibet_wst_activated(
        self, blockchain: IbetWSTBlockchain | str, activated: bool
    ) -> None:
        blockchain_key = self._normalize_ibet_wst_blockchain(blockchain)
        status_map = dict(self.ibet_wst_activated_by_blockchain or {})
        status_map[blockchain_key] = activated
        self.ibet_wst_activated_by_blockchain = status_map

    def is_ibet_wst_activated(self, blockchain: IbetWSTBlockchain | str) -> bool:
        blockchain_key = self._normalize_ibet_wst_blockchain(blockchain)
        status_map = self.ibet_wst_activated_by_blockchain or {}
        return bool(status_map.get(blockchain_key))

    def set_ibet_wst_deployed(
        self, blockchain: IbetWSTBlockchain | str, deployed: bool
    ) -> None:
        blockchain_key = self._normalize_ibet_wst_blockchain(blockchain)
        status_map = dict(self.ibet_wst_deployed_by_blockchain or {})
        status_map[blockchain_key] = deployed
        self.ibet_wst_deployed_by_blockchain = status_map

    def is_ibet_wst_deployed(self, blockchain: IbetWSTBlockchain | str) -> bool:
        blockchain_key = self._normalize_ibet_wst_blockchain(blockchain)
        status_map = self.ibet_wst_deployed_by_blockchain or {}
        return bool(status_map.get(blockchain_key))

    def set_ibet_wst_address(
        self, blockchain: IbetWSTBlockchain | str, address: str | None
    ) -> None:
        blockchain_key = self._normalize_ibet_wst_blockchain(blockchain)
        address_map = dict(self.ibet_wst_address_by_blockchain or {})
        if address is None:
            address_map.pop(blockchain_key, None)
        else:
            address_map[blockchain_key] = address
        self.ibet_wst_address_by_blockchain = address_map

    def get_ibet_wst_address(self, blockchain: IbetWSTBlockchain | str) -> str | None:
        blockchain_key = self._normalize_ibet_wst_blockchain(blockchain)
        address_map = self.ibet_wst_address_by_blockchain or {}
        return address_map.get(blockchain_key)


class TokenAttrUpdate(Base):
    """Managed Token Attribute Update"""

    __tablename__ = "token_attr_update"

    # sequence id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address: Mapped[str | None] = mapped_column(String(42), index=True)
    # datetime when token attribute updated (UTC)
    updated_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class TokenCache(Base):
    """Token Cache"""

    __tablename__ = "token_cache"

    # token address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # token attributes
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False)
    # cached datetime
    cached_datetime: Mapped[datetime | None] = mapped_column(
        DateTime, default=naive_utcnow
    )
    # expiration datetime
    expiration_datetime: Mapped[datetime | None] = mapped_column(
        DateTime, default=naive_utcnow
    )
