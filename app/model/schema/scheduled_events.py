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
from typing import Any, Dict, Optional, Self

from pydantic import BaseModel, Field, RootModel, field_validator, model_validator

from app.model.db.scheduled_events import ScheduledEventStatus, ScheduledEventType

from .. import EthereumAddress
from .base import (
    BasePaginationQuery,
    CURRENCY_str,
    EMPTY_str,
    IbetShare,
    IbetStraightBond,
    MMDD_constr,
    ResultSet,
    SortOrder,
    TokenType,
    YYYYMMDD_constr,
)


############################
# COMMON
############################
class ScheduledEvent(BaseModel):
    """Scheduled event"""

    scheduled_event_id: str
    token_address: str
    token_type: TokenType
    scheduled_datetime: datetime
    event_type: ScheduledEventType
    status: ScheduledEventStatus
    data: Dict[str, Any]
    created: str
    is_soft_deleted: bool


class ScheduledEventWithTokenAttributes(ScheduledEvent):
    """Scheduled event with token attributes"""

    token_attributes: IbetStraightBond | IbetShare = Field(
        description="Token attributes"
    )


############################
# REQUEST
############################
class IbetStraightBondScheduledUpdateData(BaseModel):
    """ibet Straight Bond scheduled update data schema"""

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


class IbetStraightBondScheduledUpdate(BaseModel):
    """scheduled event (Request)"""

    scheduled_datetime: datetime
    event_type: ScheduledEventType = Field(...)
    data: IbetStraightBondScheduledUpdateData


class IbetShareScheduledUpdateData(BaseModel):
    """ibet Share scheduled update data schema"""

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


class IbetShareScheduledUpdate(BaseModel):
    """scheduled event (Request)"""

    scheduled_datetime: datetime
    event_type: ScheduledEventType = Field(...)
    data: IbetShareScheduledUpdateData


class ListAllScheduledEventsSortItem(StrEnum):
    CREATED = "created"
    SCHEDULED_DATETIME = "scheduled_datetime"
    TOKEN_ADDRESS = "token_address"


class ListAllScheduledEventsQuery(BasePaginationQuery):
    """ListAllScheduledEvents query parameters"""

    token_type: Optional[TokenType] = Field(None, description="Token type")
    token_address: Optional[EthereumAddress] = Field(None, description="Token address")
    status: Optional[ScheduledEventStatus] = Field(
        None, description="Scheduled event processing status"
    )

    sort_item: Optional[ListAllScheduledEventsSortItem] = Field(
        ListAllScheduledEventsSortItem.CREATED
    )
    sort_order: Optional[SortOrder] = Field(
        SortOrder.DESC, description=SortOrder.__doc__
    )


class DeleteScheduledEventQuery(BaseModel):
    """DeleteScheduledBondTokenUpdateEvent query parameters"""

    soft_delete: Optional[bool] = Field(False, description="Soft delete flag")


############################
# RESPONSE
############################
class ScheduledEventIdResponse(BaseModel):
    """scheduled event (Response)"""

    scheduled_event_id: str


class ScheduledEventIdListResponse(BaseModel):
    """scheduled event list (Response)"""

    scheduled_event_id_list: list[str]


class ScheduledEventResponse(RootModel[ScheduledEvent]):
    """scheduled event (Response)"""

    pass


class ListAllScheduledEventsResponse(BaseModel):
    """List scheduled events schema"""

    result_set: ResultSet
    scheduled_events: list[ScheduledEventWithTokenAttributes]
