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
from enum import IntEnum
from typing import Annotated, Literal, Optional

from fastapi import Query
from pydantic import BaseModel, Field, RootModel, field_validator
from pydantic.dataclasses import dataclass

from app.model import EthereumAddress
from app.model.schema.base import ResultSet, SortOrder
from app.model.schema.personal_info import PersonalInfo
from app.utils.check_utils import check_value_is_encrypted
from config import E2EE_REQUEST_ENABLED

############################
# COMMON
############################


class DeliveryStatus(IntEnum):
    """DVP Delivery Status"""

    DELIVERY_CREATED = 0
    DELIVERY_CANCELED = 1
    DELIVERY_CONFIRMED = 2
    DELIVERY_FINISHED = 3
    DELIVERY_ABORTED = 4


############################
# REQUEST
############################
class CreateDVPAgentAccountRequest(BaseModel):
    """DVP agent account create schema (REQUEST)"""

    eoa_password: str = Field(..., description="EOA keyfile password")

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


class DVPAgentAccountChangeEOAPasswordRequest(BaseModel):
    """DVP agent account change EOA password schema (REQUEST)"""

    old_eoa_password: str = Field(..., description="EOA keyfile password (old)")
    eoa_password: str = Field(..., description="EOA keyfile password (new)")

    @field_validator("old_eoa_password")
    @classmethod
    def old_eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("old_eoa_password", v)
        return v

    @field_validator("eoa_password")
    @classmethod
    def eoa_password_is_encrypted_value(cls, v):
        if E2EE_REQUEST_ENABLED:
            check_value_is_encrypted("eoa_password", v)
        return v


@dataclass
class ListAllDVPDeliveriesQuery:
    token_address: Annotated[Optional[str], Query(description="Token address")] = None
    seller_address: Annotated[Optional[str], Query(description="Seller address")] = None
    buyer_address: Annotated[Optional[str], Query(description="Buyer address")] = None
    agent_address: Annotated[Optional[str], Query(description="Agent address")] = None
    valid: Annotated[Optional[bool], Query(description="Valid flag")] = None
    status: Annotated[
        Optional[DeliveryStatus], Query(description="Delivery status")
    ] = None
    create_blocktimestamp_from: Annotated[
        Optional[datetime], Query(description="Create block timestamp filter(From)")
    ] = None
    create_blocktimestamp_to: Annotated[
        Optional[datetime], Query(description="Create block timestamp filter(To)")
    ] = None

    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = (
        SortOrder.DESC
    )
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


@dataclass
class ListAllDVPAgentDeliveriesQuery:
    agent_address: Annotated[str, Query(description="Agent address")]
    token_address: Annotated[Optional[str], Query(description="Token address")] = None
    seller_address: Annotated[Optional[str], Query(description="Seller address")] = None
    buyer_address: Annotated[Optional[str], Query(description="Buyer address")] = None
    valid: Annotated[Optional[bool], Query(description="Valid flag")] = None
    status: Annotated[
        Optional[DeliveryStatus], Query(description="Delivery status")
    ] = None
    create_blocktimestamp_from: Annotated[
        Optional[datetime], Query(description="Create block timestamp filter(From)")
    ] = None
    create_blocktimestamp_to: Annotated[
        Optional[datetime], Query(description="Create block timestamp filter(To)")
    ] = None

    sort_order: Annotated[SortOrder, Query(description="0:asc, 1:desc")] = (
        SortOrder.DESC
    )
    offset: Annotated[Optional[int], Query(description="Start position", ge=0)] = None
    limit: Annotated[Optional[int], Query(description="Number of set", ge=0)] = None


class CreateDVPDeliveryRequest(BaseModel):
    """DVP delivery create schema (REQUEST)"""

    token_address: EthereumAddress
    buyer_address: EthereumAddress
    amount: int = Field(..., ge=1, le=1_000_000_000_000)
    agent_address: EthereumAddress
    data: str


class CancelDVPDeliveryRequest(BaseModel):
    """DVP delivery cancel schema (REQUEST)"""

    operation_type: Literal["Cancel"]


class FinishDVPDeliveryRequest(BaseModel):
    """DVP delivery finish schema (REQUEST)"""

    operation_type: Literal["Finish"]
    account_address: EthereumAddress = Field(..., description="Agent account address")
    eoa_password: str = Field(..., description="Agent account key file password")


class AbortDVPDeliveryRequest(BaseModel):
    """DVP delivery abort schema (REQUEST)"""

    operation_type: Literal["Abort"]
    account_address: EthereumAddress = Field(..., description="Agent account address")
    eoa_password: str = Field(..., description="Agent account key file password")


############################
# RESPONSE
############################
class DVPAgentAccountResponse(BaseModel):
    """DVP agent account reference schema (RESPONSE)"""

    account_address: str
    is_deleted: bool


class ListAllDVPAgentAccountResponse(RootModel[list[DVPAgentAccountResponse]]):
    """DVP agent account list reference schema (RESPONSE)"""

    pass


class CreateDVPDeliveryResponse(BaseModel):
    """Create DVP delivery schema (RESPONSE)"""

    delivery_id: int


class RetrieveDVPDeliveryResponse(BaseModel):
    """Retrieve DVP delivery schema (Response)"""

    exchange_address: str
    delivery_id: int
    token_address: str
    buyer_address: str
    buyer_personal_information: Optional[PersonalInfo] = Field(...)
    seller_address: str
    seller_personal_information: Optional[PersonalInfo] = Field(...)
    amount: int
    agent_address: str
    data: str = Field(examples=["{}", '{"type": "primary"}'])
    create_blocktimestamp: str
    create_transaction_hash: str
    cancel_blocktimestamp: Optional[str] = Field(...)
    cancel_transaction_hash: Optional[str] = Field(...)
    confirm_blocktimestamp: Optional[str] = Field(...)
    confirm_transaction_hash: Optional[str] = Field(...)
    finish_blocktimestamp: Optional[str] = Field(...)
    finish_transaction_hash: Optional[str] = Field(...)
    abort_blocktimestamp: Optional[str] = Field(...)
    abort_transaction_hash: Optional[str] = Field(...)
    confirmed: bool
    valid: bool
    status: DeliveryStatus


class ListAllDVPDeliveriesResponse(BaseModel):
    """List all DVP delivery schema (Response)"""

    result_set: ResultSet
    deliveries: list[RetrieveDVPDeliveryResponse]
