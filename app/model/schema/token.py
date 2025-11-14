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
from enum import StrEnum
from typing import Annotated, Literal, Optional, Self

from fastapi import Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.model import EthereumAddress, ValidatedDatetimeStr

from .base import (
    BasePaginationQuery,
    CURRENCY_str,
    EMPTY_str,
    IbetShare,
    IbetShareContractVersion,
    IbetStraightBond,
    IbetStraightBondContractVersion,
    KeyManagerType,
    MMDD_constr,
    ResultSet,
    SortOrder,
    TokenStatus,
    TokenType,
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

    activate_ibet_wst: Optional[Literal[True]] = Field(
        default=None, description="Activate IbetWST"
    )
    wst_name: Optional[str] = Field(
        default=None, max_length=100, description="IbetWST name"
    )

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

    @model_validator(mode="after")
    @classmethod
    def wst_name_required_if_activated(cls, v: Self):
        if v.activate_ibet_wst:
            if v.wst_name is None:
                raise ValueError("wst_name is required when activate_ibet_wst is true")
        return v


class IbetStraightBondUpdate(BaseModel):
    """ibet Straight Bond schema (Update)"""

    face_value: Optional[int] = Field(None, ge=0, le=5_000_000_000)
    face_value_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    purpose: Optional[str] = Field(default=None, max_length=2000)
    interest_rate: Optional[float] = Field(None, ge=0.0000, le=100.0000)
    interest_payment_date: Optional[list[MMDD_constr]] = None
    interest_payment_currency: Optional[CURRENCY_str | EMPTY_str] = Field(default=None)
    redemption_value: Optional[int] = Field(None, ge=0, le=5_000_000_000)
    redemption_value_currency: Optional[CURRENCY_str | EMPTY_str] = Field(default=None)
    redemption_date: Optional[YYYYMMDD_constr | EMPTY_str] = None
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

    activate_ibet_wst: Optional[Literal[True]] = Field(
        default=None, description="Activate IbetWST"
    )

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

    activate_ibet_wst: Optional[Literal[True]] = Field(
        default=None, description="Activate IbetWST"
    )
    wst_name: Optional[str] = Field(
        default=None, max_length=100, description="IbetWST name"
    )

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
    def wst_name_required_if_activated(cls, v: Self):
        if v.activate_ibet_wst:
            if v.wst_name is None:
                raise ValueError("wst_name is required when activate_ibet_wst is true")
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

    activate_ibet_wst: Optional[Literal[True]] = Field(
        default=None, description="Activate IbetWST"
    )

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


class ListAllIssuedTokensSortItem(StrEnum):
    CREATED = "created"
    TOKEN_ADDRESS = "token_address"


class ListAllIssuedTokensQuery(BasePaginationQuery):
    """ListAllIssuedTokens query parameters"""

    token_address_list: Optional[list[EthereumAddress]] = Field(
        None, description="Token address to filter (**this affects total number**)"
    )
    token_type: Optional[TokenType] = Field(None, description="Token type")

    sort_item: Optional[ListAllIssuedTokensSortItem] = Field(
        ListAllIssuedTokensSortItem.CREATED
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class IssueRedeemSortItem(StrEnum):
    """Issue/Redeem sort item"""

    BLOCK_TIMESTAMP = "block_timestamp"
    LOCKED_ADDRESS = "locked_address"
    TARGET_ADDRESS = "target_address"
    AMOUNT = "amount"


class ListAdditionalIssuanceHistoryQuery(BasePaginationQuery):
    sort_item: Optional[IssueRedeemSortItem] = Field(
        IssueRedeemSortItem.BLOCK_TIMESTAMP
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class ListAllAdditionalIssueUploadQuery(BasePaginationQuery):
    processed: Optional[bool] = Field(None, description="Process status")
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class ListRedeemHistoryQuery(BasePaginationQuery):
    sort_item: Optional[IssueRedeemSortItem] = Field(
        IssueRedeemSortItem.BLOCK_TIMESTAMP
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class ListAllRedeemUploadQuery(BasePaginationQuery):
    processed: Optional[bool] = Field(None, description="Process status")
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class ListAllHoldersSortItem(StrEnum):
    created = "created"
    account_address = "account_address"
    balance = "balance"
    pending_transfer = "pending_transfer"
    locked = "locked"
    balance_and_pending_transfer = "balance_and_pending_transfer"
    key_manager = "key_manager"
    holder_name = "holder_name"


class ListAllHoldersQuery(BasePaginationQuery):
    include_former_holder: bool = Field(default=False)
    key_manager_type: Optional[KeyManagerType] = Field(
        None, description="Key manager type (**this affects total number**)"
    )
    key_manager: Optional[str] = Field(None, description="key manager(partial match)")
    balance: Optional[int] = Field(None, description="Token balance")
    balance_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="Search condition of balance(0:equal, 1:greater than or equal, 2:less than or equal）",
    )
    pending_transfer: Optional[int] = Field(None, description="Pending transfer amount")
    pending_transfer_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="Search condition of pending transfer(0:equal, 1:greater than or equal, 2:less than or equal）",
    )
    locked: Optional[int] = Field(None, description="Locked amount")
    locked_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="search condition of locked amount(0:equal, 1:greater than or equal, 2:less than or equal）",
    )

    balance_and_pending_transfer: Optional[int] = Field(
        None, description="number of balance plus pending transfer amount"
    )
    balance_and_pending_transfer_operator: Optional[ValueOperator] = Field(
        ValueOperator.EQUAL,
        description="search condition of balance plus pending transfer(0:equal, 1:greater than or equal, 2:less than or equal）",
    )
    account_address: Optional[str] = Field(
        None, description="account address(partial match)"
    )
    holder_name: Optional[str] = Field(None, description="holder name(partial match)")

    sort_item: Annotated[ListAllHoldersSortItem, Query(description="Sort Item")] = (
        ListAllHoldersSortItem.created
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.ASC, description=SortOrder.__doc__
    )


class ListAllTokenLockEventsSortItem(StrEnum):
    account_address = "account_address"
    lock_address = "lock_address"
    recipient_address = "recipient_address"
    value = "value"
    block_timestamp = "block_timestamp"


class ListAllTokenLockEventsQuery(BasePaginationQuery):
    account_address: Optional[str] = Field(None, description="Account address")
    msg_sender: Optional[str] = Field(None, description="Msg sender")
    lock_address: Optional[str] = Field(None, description="Lock address")
    recipient_address: Optional[str] = Field(None, description="Recipient address")
    category: Optional[LockEventCategory] = Field(None, description="Event category")

    sort_item: Optional[ListAllTokenLockEventsSortItem] = Field(
        ListAllTokenLockEventsSortItem.block_timestamp, description="Sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class TokenUpdateOperationCategory(StrEnum):
    """Operation category of update token"""

    ISSUE = "Issue"
    UPDATE = "Update"


class ListTokenHistorySortItem(StrEnum):
    """Sort item of token history"""

    created = "created"
    operation_category = "operation_category"


class ListTokenOperationLogHistoryQuery(BasePaginationQuery):
    modified_contents: Optional[str] = Field(
        None, description="Modified contents query"
    )
    operation_category: Optional[TokenUpdateOperationCategory] = Field(
        None, description="Trigger of change"
    )
    created_from: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (From)"
    )
    created_to: Optional[ValidatedDatetimeStr] = Field(
        None, description="Created datetime (To)"
    )

    sort_item: Optional[ListTokenHistorySortItem] = Field(
        ListTokenHistorySortItem.created, description="Sort item"
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


############################
# RESPONSE
############################
class IssuedToken(BaseModel):
    """Issued Token"""

    issuer_address: str = Field(description="Issuer address")
    token_address: str = Field(description="Token address")
    token_type: TokenType = Field(description="Token type")
    created: str = Field(description="Created(Issued) datetime")
    token_status: Optional[TokenStatus] = Field(description="Token status")
    contract_version: IbetStraightBondContractVersion | IbetShareContractVersion = (
        Field(description="Contract version")
    )
    token_attributes: IbetStraightBond | IbetShare = Field(
        description="Token attributes"
    )


class ListAllIssuedTokensResponse(BaseModel):
    """List issued tokens schema"""

    result_set: ResultSet
    tokens: list[IssuedToken]


class TokenAddressResponse(BaseModel):
    """token address"""

    token_address: str
    token_status: TokenStatus


class IbetStraightBondResponse(IbetStraightBond):
    """ibet Straight Bond schema (Response)"""

    issue_datetime: str = Field(..., description="Issue datetime (ISO 8601 format)")
    token_status: Optional[TokenStatus] = Field(..., description="Token deploy status")
    contract_version: IbetStraightBondContractVersion = Field(
        ..., description="Contract version"
    )
    ibet_wst_activated: bool = Field(..., description="IbetWST activated")
    ibet_wst_version: Optional[str] = Field(..., description="IbetWST version")
    ibet_wst_deployed: bool = Field(..., description="IbetWST deployed")
    ibet_wst_address: Optional[str] = Field(..., description="IbetWST contract address")


class IbetShareResponse(IbetShare):
    """ibet Share schema (Response)"""

    issue_datetime: str = Field(..., description="Issue datetime (ISO 8601 format)")
    token_status: Optional[TokenStatus] = Field(..., description="Token deploy status")
    contract_version: IbetShareContractVersion = Field(
        ..., description="Contract version"
    )
    ibet_wst_activated: bool = Field(..., description="IbetWST activated")
    ibet_wst_version: Optional[str] = Field(..., description="IbetWST version")
    ibet_wst_deployed: bool = Field(..., description="IbetWST deployed")
    ibet_wst_address: Optional[str] = Field(..., description="IbetWST contract address")


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
