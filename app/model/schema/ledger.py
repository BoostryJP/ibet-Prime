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
from typing import (
    List,
    Optional
)
from pydantic import (
    BaseModel,
    validator,
    Field
)
from datetime import datetime

from .types import ResultSet


############################
# REQUEST
############################

class CreateUpdateLedgerDetailsDataTemplateRequest(BaseModel):
    """Create or Update Ledger Details Data Template schema (Request)"""
    type: str = Field(..., regex="^ibetfin$|^db$")
    source: Optional[str] = Field(None, max_length=42)


class CreateUpdateLedgerDetailsTemplateRequest(BaseModel):
    """Create or Update Ledger Details Template schema (Request)"""
    token_detail_type: str = Field(..., max_length=100)
    headers: Optional[List[dict]]
    data: CreateUpdateLedgerDetailsDataTemplateRequest
    footers: Optional[List[dict]]


class CreateUpdateLedgerTemplateRequest(BaseModel):
    """Create or Update Ledger Template schema (Request)"""
    token_name: str = Field(..., max_length=200)
    headers: Optional[List[dict]]
    details: List[CreateUpdateLedgerDetailsTemplateRequest]
    footers: Optional[List[dict]]

    @validator("details")
    def details_length_is_greater_than_1(cls, v):
        if len(v) < 1:
            raise ValueError("The length must be greater than or equal to 1")
        return v


class CreateUpdateLedgerDetailsDataRequest(BaseModel):
    """Create or Update Ledger Details Data Structure schema (Request)"""
    name: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = Field(None, max_length=200)
    amount: Optional[int] = Field(None, ge=0, le=2 ** 31 - 1)
    price: Optional[int] = Field(None, ge=0, le=2 ** 31 - 1)
    balance: Optional[int] = Field(None, ge=0, le=2 ** 31 - 1)
    acquisition_date: Optional[str] = Field(None, min_length=10, max_length=10, description="YYYY/MM/DD")

    @validator("acquisition_date")
    def acquisition_date_format_is_YYYYMMDD_slash(cls, v):
        if v is not None and len(v) == 10:
            try:
                datetime.strptime(v, "%Y/%m/%d")
            except ValueError:
                raise ValueError("The date format must be YYYY/MM/DD")
        return v


############################
# RESPONSE
############################

class LedgerResponse(BaseModel):
    """Ledger schema (Response)"""
    id: int
    token_address: str
    token_type: str
    created: datetime


class ListAllLedgerHistoryResponse(BaseModel):
    """List All Ledger History schema (Response)"""
    result_set: ResultSet
    ledgers: List[LedgerResponse]


class RetrieveLedgerDetailsDataHistoryResponse(BaseModel):
    """Retrieve Ledger Details Data History schema (Response)"""
    account_address: Optional[str]
    name: str
    address: str
    amount: int
    price: int
    balance: int
    acquisition_date: str


class RetrieveLedgerDetailsHistoryResponse(BaseModel):
    """Retrieve Ledger Details History schema (Response)"""
    token_detail_type: str
    headers: List[dict]
    data: List[RetrieveLedgerDetailsDataHistoryResponse]
    footers: List[dict]


class RetrieveLedgerHistoryResponse(BaseModel):
    """Retrieve Ledger History schema (Response)"""
    created: str
    token_name: str
    headers: List[dict]
    details: List[RetrieveLedgerDetailsHistoryResponse]
    footers: List[dict]


class LedgerDetailsDataTemplateResponse(BaseModel):
    """Ledger Details Data Template schema (Response)"""
    type: str
    source: Optional[str]


class LedgerDetailsTemplateResponse(BaseModel):
    """Ledger Details Template schema (Response)"""
    token_detail_type: str
    headers: Optional[List[dict]]
    data: LedgerDetailsDataTemplateResponse
    footers: Optional[List[dict]]


class LedgerTemplateResponse(BaseModel):
    """Ledger Template schema (Response)"""
    token_name: str
    headers: Optional[List[dict]]
    details: List[LedgerDetailsTemplateResponse]
    footers: Optional[List[dict]]


class LedgerDetailsDataListAllResponse(BaseModel):
    """Ledger Details Data(List All) schema (Response)"""
    data_id: str
    count: int
    created: datetime


class ListAllLedgerDetailsDataResponse(BaseModel):
    """List All Ledger Details Data schema (Response)"""
    result_set: ResultSet
    details_data: List[LedgerDetailsDataListAllResponse]


class LedgerDetailsDataResponse(BaseModel):
    """Ledger Details Data schema (Response)"""
    data_id: str


class RetrieveLedgerDetailsDataResponse(BaseModel):
    """Retrieve Ledger Details Data schema (Response)"""
    name: str
    address: str
    amount: int
    price: int
    balance: int
    acquisition_date: str
