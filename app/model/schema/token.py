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

import math
from datetime import datetime
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Annotated, Optional, Self

from fastapi import Query
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.dataclasses import dataclass

from app.model import EthereumAddress, ValidatedDatetimeStr

from .base import (
    CURRENCY_str,
    EMPTY_str,
    IbetShareContractVersion,
    IbetStraightBondContractVersion,
    MMDD_constr,
    ResultSet,
    SortOrder,
    ValueOperator,
    YYYYMMDD_constr,
)
from .position import LockEvent, LockEventCategory


############################
# REQUEST
############################
class IbetStraightBondCreate(BaseModel):
    """ibet Straight Bond schema (Create)"""

    name: str = Field(max_length=100)
    total_supply: int = Field(..., ge=0, le=1_000_000_000_000)
    face_value: int = Field(..., ge=0, le=5_000_000_000)
    face_value_currency: str = Field(..., min_length=3, max_length=3)
    purpose: str = Field(max_length=2000)
    symbol: Optional[str] = Field(default=None, max_length=100)
    redemption_date: Optional[YYYYMMDD_constr] = None
    redemption_value: Optional[int] = Field(default=None, ge=0, le=5_000_000_000)
    redemption_value_currency: Optional[str] = Field(
        default=None, min_length=3, max_length=3
    )
    return_date: Optional[YYYYMMDD_constr] = None
    return_amount: Optional[str] = Field(default=None, max_length=2000)
    interest_rate: Optional[float] = Field(default=None, ge=0.0000, le=100.0000)
    interest_payment_date: Optional[list[MMDD_constr]] = None
    interest_payment_currency: Optional[str] = Field(
        default=None, min_length=3, max_length=3
    )
    base_fx_rate: Optional[float] = Field(default=None, ge=0.000000)
    transferable: Optional[bool] = None
    is_redeemed: Optional[bool] = None
    status: Optional[bool] = None
    is_offering: Optional[bool] = None
    tradable_exchange_contract_address: Optional[EthereumAddress] = None
    personal_info_contract_address: Optional[EthereumAddress] = None
    require_personal_info_registered: Optional[bool] = None
    image_url: Optional[list[str]] = None
    contact_information: Optional[str] = Field(default=None, max_length=2000)
    privacy_policy: Optional[str] = Field(default=None, max_length=5000)
    transfer_approval_required: Optional[bool] = None

    @field_validator("base_fx_rate")
    @classmethod
    def base_fx_rate_6_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**6)
            int_data = int(Decimal(str(v)) * 10**6)
            if not math.isclose(int_data, float_data):
                raise ValueError(
                    "base_fx_rate must be less than or equal to six decimal places"
                )
        return v

    @field_validator("interest_rate")
    @classmethod
    def interest_rate_4_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**4)
            int_data = int(Decimal(str(v)) * 10**4)
            if not math.isclose(int_data, float_data):
                raise ValueError(
                    "interest_rate must be less than or equal to four decimal places"
                )
        return v

    @field_validator("interest_payment_date")
    @classmethod
    def interest_payment_date_list_length_less_than_13(cls, v):
        if v is not None and len(v) >= 13:
            raise ValueError(
                "list length of interest_payment_date must be less than 13"
            )
        return v


class IbetStraightBondUpdate(BaseModel):
    """ibet Straight Bond schema (Update)"""

    face_value: Optional[int] = Field(None, ge=0, le=5_000_000_000)
    face_value_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    interest_rate: Optional[float] = Field(None, ge=0.0000, le=100.0000)
    interest_payment_date: Optional[list[MMDD_constr]] = None
    interest_payment_currency: Optional[CURRENCY_str | EMPTY_str] = Field(default=None)
    redemption_value: Optional[int] = Field(None, ge=0, le=5_000_000_000)
    redemption_value_currency: Optional[CURRENCY_str | EMPTY_str] = Field(default=None)
    base_fx_rate: Optional[float] = Field(default=None, ge=0.000000)
    transferable: Optional[bool] = None
    status: Optional[bool] = None
    is_offering: Optional[bool] = None
    is_redeemed: Optional[bool] = None
    tradable_exchange_contract_address: Optional[EthereumAddress] = None
    personal_info_contract_address: Optional[EthereumAddress] = None
    require_personal_info_registered: Optional[bool] = None
    contact_information: Optional[str] = Field(default=None, max_length=2000)
    privacy_policy: Optional[str] = Field(default=None, max_length=5000)
    transfer_approval_required: Optional[bool] = None
    memo: Optional[str] = Field(default=None, max_length=10000)

    @field_validator("base_fx_rate")
    @classmethod
    def base_fx_rate_6_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**6)
            int_data = int(Decimal(str(v)) * 10**6)
            if not math.isclose(int_data, float_data):
                raise ValueError(
                    "base_fx_rate must be less than or equal to six decimal places"
                )
        return v

    @field_validator("is_redeemed")
    @classmethod
    def is_redeemed_is_valid(cls, v):
        if v is not None and v is False:
            raise ValueError("is_redeemed cannot be updated to `false`")
        return v

    @field_validator("interest_rate")
    @classmethod
    def interest_rate_4_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**4)
            int_data = int(Decimal(str(v)) * 10**4)
            if not math.isclose(int_data, float_data):
                raise ValueError("interest_rate must be rounded to 4 decimal places")
        return v

    @field_validator("interest_payment_date")
    @classmethod
    def interest_payment_date_list_length_less_than_13(cls, v):
        if v is not None and len(v) >= 13:
            raise ValueError(
                "list length of interest_payment_date must be less than 13"
            )
        return v


class IbetStraightBondAdditionalIssue(BaseModel):
    """ibet Straight Bond schema (Additional Issue)"""

    account_address: EthereumAddress
    amount: int = Field(..., ge=1, le=1_000_000_000_000)


class IbetStraightBondRedeem(BaseModel):
    """ibet Straight Bond schema (Redeem)"""

    account_address: EthereumAddress
    amount: int = Field(..., ge=1, le=1_000_000_000_000)


class IbetStraightBondTransfer(BaseModel):
    """ibet Straight Bond schema (Transfer)"""

    token_address: EthereumAddress
    from_address: EthereumAddress
    to_address: EthereumAddress
    amount: int = Field(..., ge=1, le=1_000_000_000_000)


class IbetShareCreate(BaseModel):
    """ibet Share schema (Create)"""

    name: str = Field(max_length=100)
    issue_price: int = Field(..., ge=0, le=5_000_000_000)
    principal_value: int = Field(..., ge=0, le=5_000_000_000)
    total_supply: int = Field(..., ge=0, le=1_000_000_000_000)
    symbol: Optional[str] = Field(default=None, max_length=100)
    dividends: Optional[float] = Field(default=None, ge=0.00, le=5_000_000_000.00)
    dividend_record_date: Optional[YYYYMMDD_constr | EMPTY_str] = None
    dividend_payment_date: Optional[YYYYMMDD_constr | EMPTY_str] = None
    cancellation_date: Optional[YYYYMMDD_constr | EMPTY_str] = None
    transferable: Optional[bool] = None
    status: Optional[bool] = None
    is_offering: Optional[bool] = None
    tradable_exchange_contract_address: Optional[EthereumAddress] = None
    personal_info_contract_address: Optional[EthereumAddress] = None
    require_personal_info_registered: Optional[bool] = None
    contact_information: Optional[str] = Field(default=None, max_length=2000)
    privacy_policy: Optional[str] = Field(default=None, max_length=5000)
    transfer_approval_required: Optional[bool] = None
    is_canceled: Optional[bool] = None

    @field_validator("dividends")
    @classmethod
    def dividends_13_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**13)
            int_data = int(Decimal(str(v)) * 10**13)
            if not math.isclose(int_data, float_data):
                raise ValueError("dividends must be rounded to 13 decimal places")
        return v


class IbetShareUpdate(BaseModel):
    """ibet Share schema (Update)"""

    cancellation_date: Optional[YYYYMMDD_constr | EMPTY_str] = None
    dividend_record_date: Optional[YYYYMMDD_constr | EMPTY_str] = None
    dividend_payment_date: Optional[YYYYMMDD_constr | EMPTY_str] = None
    dividends: Optional[float] = Field(default=None, ge=0.00, le=5_000_000_000.00)
    tradable_exchange_contract_address: Optional[EthereumAddress] = None
    personal_info_contract_address: Optional[EthereumAddress] = None
    require_personal_info_registered: Optional[bool] = None
    transferable: Optional[bool] = None
    status: Optional[bool] = None
    is_offering: Optional[bool] = None
    contact_information: Optional[str] = Field(default=None, max_length=2000)
    privacy_policy: Optional[str] = Field(default=None, max_length=5000)
    transfer_approval_required: Optional[bool] = None
    principal_value: Optional[int] = Field(default=None, ge=0, le=5_000_000_000)
    is_canceled: Optional[bool] = None
    memo: Optional[str] = Field(default=None, max_length=10000)

    @field_validator("is_canceled")
    @classmethod
    def is_canceled_is_valid(cls, v):
        if v is not None and v is False:
            raise ValueError("is_canceled cannot be updated to `false`")
        return v

    @field_validator("dividends")
    @classmethod
    def dividends_13_decimal_places(cls, v):
        if v is not None:
            float_data = float(Decimal(str(v)) * 10**13)
            int_data = int(Decimal(str(v)) * 10**13)
            if not math.isclose(int_data, float_data):
                raise ValueError("dividends must be rounded to 13 decimal places")
        return v

    @model_validator(mode="after")
    @classmethod
    def dividend_information_all_required(cls, v: Self):
        if v.dividends:
            if v.dividend_record_date is None or v.dividend_payment_date is None:
                raise ValueError(
                    "all items are required to update the dividend information"
                )
        return v


class IbetShareTransfer(BaseModel):
    """ibet Share schema (Transfer)"""

    token_address: EthereumAddress
    from_address: EthereumAddress
    to_address: EthereumAddress
    amount: int = Field(..., ge=1, le=1_000_000_000_000)


class IbetShareAdditionalIssue(BaseModel):
    """ibet Share schema (Additional Issue)"""

    account_address: EthereumAddress
    amount: int = Field(..., ge=1, le=1_000_000_000_000)


class IbetShareRedeem(BaseModel):
    """ibet Share schema (Redeem)"""

    account_address: EthereumAddress
    amount: int = Field(..., ge=1, le=1_000_000_000_000)


class IssueRedeemSortItem(str, Enum):
    """Issue/Redeem sort item"""

    BLOCK_TIMESTAMP = "block_timestamp"
    LOCKED_ADDRESS = "locked_address"
    TARGET_ADDRESS = "target_address"
    AMOUNT = "amount"


@dataclass
class ListAdditionalIssuanceHistoryQuery:
    sort_item: Annotated[IssueRedeemSortItem, Query()] = (
        IssueRedeemSortItem.BLOCK_TIMESTAMP
    )
    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = (
        SortOrder.DESC
    )
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


@dataclass
class ListAllAdditionalIssueUploadQuery:
    processed: Annotated[Optional[bool], Query()] = None
    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = (
        SortOrder.DESC
    )
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


@dataclass
class ListRedeemHistoryQuery:
    sort_item: Annotated[IssueRedeemSortItem, Query()] = (
        IssueRedeemSortItem.BLOCK_TIMESTAMP
    )
    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = (
        SortOrder.DESC
    )
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


@dataclass
class ListAllRedeemUploadQuery:
    processed: Annotated[Optional[bool], Query()] = None
    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = (
        SortOrder.DESC
    )
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


class ListAllHoldersSortItem(StrEnum):
    created = "created"
    account_address = "account_address"
    balance = "balance"
    pending_transfer = "pending_transfer"
    locked = "locked"
    key_manager = "key_manager"
    holder_name = "holder_name"


@dataclass
class ListAllHoldersQuery:
    include_former_holder: Annotated[bool, Query()] = False
    balance: Annotated[Optional[int], Query(description="number of balance")] = None
    balance_operator: Annotated[
        Optional[ValueOperator],
        Query(
            description="search condition of balance(0:equal, 1:greater than or equal, 2:less than or equal）",
        ),
    ] = ValueOperator.EQUAL
    pending_transfer: Annotated[
        Optional[int], Query(description="number of pending transfer amount")
    ] = None
    pending_transfer_operator: Annotated[
        Optional[ValueOperator],
        Query(
            description="search condition of pending transfer(0:equal, 1:greater than or equal, 2:less than or equal）",
        ),
    ] = ValueOperator.EQUAL
    locked: Annotated[Optional[int], Query(description="number of locked amount")] = (
        None
    )
    locked_operator: Annotated[
        Optional[ValueOperator],
        Query(
            description="search condition of locked amount(0:equal, 1:greater than or equal, 2:less than or equal）",
        ),
    ] = ValueOperator.EQUAL
    account_address: Annotated[
        Optional[str], Query(description="account address(partial match)")
    ] = None
    holder_name: Annotated[
        Optional[str], Query(description="holder name(partial match)")
    ] = None
    key_manager: Annotated[
        Optional[str], Query(description="key manager(partial match)")
    ] = None
    sort_item: Annotated[ListAllHoldersSortItem, Query(description="Sort Item")] = (
        ListAllHoldersSortItem.created
    )
    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = SortOrder.ASC
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


class ListAllTokenLockEventsSortItem(str, Enum):
    account_address = "account_address"
    lock_address = "lock_address"
    recipient_address = "recipient_address"
    value = "value"
    block_timestamp = "block_timestamp"


@dataclass
class ListAllTokenLockEventsQuery:
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None

    account_address: Annotated[Optional[str], Query(description="Account address")] = (
        None
    )
    msg_sender: Annotated[Optional[str], Query(description="Msg sender")] = None
    lock_address: Annotated[Optional[str], Query(description="Lock address")] = None
    recipient_address: Annotated[
        Optional[str], Query(description="Recipient address")
    ] = None
    category: Annotated[
        Optional[LockEventCategory], Query(description="Event category")
    ] = None

    sort_item: Annotated[
        ListAllTokenLockEventsSortItem, Query(description="Sort item")
    ] = ListAllTokenLockEventsSortItem.block_timestamp
    sort_order: Annotated[
        SortOrder, Query(description="Sort order(0: ASC, 1: DESC)")
    ] = SortOrder.DESC


class TokenUpdateOperationCategory(StrEnum):
    """Operation category of update token"""

    ISSUE = "Issue"
    UPDATE = "Update"


class ListTokenHistorySortItem(StrEnum):
    """Sort item of token history"""

    created = "created"
    operation_category = "operation_category"


@dataclass
class ListTokenOperationLogHistoryQuery:
    modified_contents: Annotated[
        Optional[str], Query(description="Modified contents query")
    ] = None
    operation_category: Annotated[
        Optional[TokenUpdateOperationCategory], Query(description="Trigger of change")
    ] = None
    created_from: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="created datetime (From)")
    ] = None
    created_to: Annotated[
        Optional[ValidatedDatetimeStr], Query(description="created datetime (To)")
    ] = None
    sort_item: Annotated[ListTokenHistorySortItem, Query(description="Sort item")] = (
        ListTokenHistorySortItem.created
    )
    sort_order: Annotated[
        SortOrder, Query(description="Sort order(0: ASC, 1: DESC)")
    ] = SortOrder.DESC
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


############################
# RESPONSE
############################
class TokenAddressResponse(BaseModel):
    """token address"""

    token_address: str
    token_status: int


class IbetStraightBondResponse(BaseModel):
    """ibet Straight Bond schema (Response)"""

    issuer_address: str
    token_address: str
    name: str
    symbol: str
    total_supply: int
    face_value: int
    face_value_currency: str
    redemption_date: str
    redemption_value: int
    redemption_value_currency: str
    return_date: str
    return_amount: str
    purpose: str
    interest_rate: float
    interest_payment_date: list[str]
    interest_payment_currency: str
    base_fx_rate: float
    transferable: bool
    is_redeemed: bool
    status: bool
    is_offering: bool
    tradable_exchange_contract_address: str
    personal_info_contract_address: str
    require_personal_info_registered: bool
    contact_information: str
    privacy_policy: str
    issue_datetime: str
    token_status: int
    transfer_approval_required: bool
    memo: str
    contract_version: IbetStraightBondContractVersion


class IbetShareResponse(BaseModel):
    """ibet Share schema (Response)"""

    issuer_address: str
    token_address: str
    name: str
    symbol: str
    issue_price: int
    principal_value: int
    total_supply: int
    dividends: float
    dividend_record_date: str
    dividend_payment_date: str
    cancellation_date: str
    transferable: bool
    transfer_approval_required: bool
    status: bool
    is_offering: bool
    tradable_exchange_contract_address: str
    personal_info_contract_address: str
    require_personal_info_registered: bool
    contact_information: str
    privacy_policy: str
    issue_datetime: str
    token_status: int
    is_canceled: bool
    memo: str
    contract_version: IbetShareContractVersion


class TokenOperationLogResponse(BaseModel):
    original_contents: dict | None = Field(
        default=None, description="original attributes before update"
    )
    modified_contents: dict = Field(..., description="update attributes")
    operation_category: TokenUpdateOperationCategory
    created: datetime


class ListTokenOperationLogHistoryResponse(BaseModel):
    result_set: ResultSet
    history: list[TokenOperationLogResponse] = Field(
        default=[], description="token update histories"
    )


class ListAllTokenLockEventsResponse(BaseModel):
    """List All Lock/Unlock events (Response)"""

    result_set: ResultSet
    events: list[LockEvent] = Field(description="Lock/Unlock event list")
