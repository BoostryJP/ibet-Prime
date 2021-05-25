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
    validator
)
from datetime import datetime

from config import SYSTEM_LOCALE
from .result_set import ResultSet


############################
# REQUEST
############################

class CreateUpdateLedgerDetailsDataTemplateRequest(BaseModel):
    """Create or Update Ledger Details Data Template schema (Request)"""
    type: str
    source: Optional[str]

    @validator("type")
    def type_length_is_less_than_20(cls, v):
        if len(v) > 100:
            raise ValueError("The length must be less than or equal to 20")
        return v

    @validator("source")
    def source_length_is_less_than_42(cls, v):
        if len(v) > 42:
            raise ValueError("The length must be less than or equal to 42")
        return v


class CreateUpdateLedgerDetailsTemplateRequest(BaseModel):
    """Create or Update Ledger Details Template schema (Request)"""
    token_detail_type: str
    headers: Optional[dict]
    data: CreateUpdateLedgerDetailsDataTemplateRequest
    footers: Optional[dict]

    @validator("token_detail_type")
    def token_detail_type_length_is_less_than_100(cls, v):
        if len(v) > 100:
            raise ValueError("The length must be less than or equal to 100")
        return v


class CreateUpdateLedgerTemplateRequest(BaseModel):
    """Create or Update Ledger Template schema (Request)"""
    token_name: str
    country_code: str
    headers: Optional[dict]
    details: List[CreateUpdateLedgerDetailsTemplateRequest]
    footers: Optional[dict]

    @validator("token_name")
    def token_name_length_is_less_than_200(cls, v):
        if len(v) > 200:
            raise ValueError("The length must be less than or equal to 200")
        return v

    @validator("country_code")
    def country_code_length_is_less_than_200(cls, v):
        if len(v) > 3:
            raise ValueError("The length must be less than or equal to 3")
        return v

    @validator("details")
    def details_length_is_greater_than_1(cls, v):
        if len(v) < 1:
            raise ValueError("The length must be greater than or equal to 1")
        return v


class CreateUpdateLedgerDetailsDataStructureRequest(BaseModel):
    """Create or Update Ledger Details Data Structure schema (Request)"""
    account_address: Optional[str]
    name: Optional[str]
    address: Optional[str]
    amount: Optional[int]
    price: Optional[int]
    balance: Optional[int]
    acquisition_date: Optional[str]

    @validator("account_address")
    def account_address_length_is_less_than_42(cls, v):
        if v is not None:
            if len(v) > 42:
                raise ValueError("The length must be less than or equal to 42")
        return v

    @validator("name")
    def name_length_is_less_than_200(cls, v):
        if v is not None:
            if len(v) > 200:
                raise ValueError("The length must be less than or equal to 200")
        return v

    @validator("address")
    def address_length_is_less_than_200(cls, v):
        if v is not None:
            if len(v) > 200:
                raise ValueError("The length must be less than or equal to 200")
        return v

    @validator("acquisition_date")
    def acquisition_date_format_is_YYYYMMDD_slash(cls, v):
        if v is not None:
            try:
                if len(v) != 10:
                    raise ValueError
                datetime.strptime(v, "%Y/%m/%d")
            except ValueError:
                raise ValueError("The date format must be YYYY/MM/DD")
        return v


class CreateUpdateLedgerDetailsDataRequest(BaseModel):
    """Create or Update Ledger Details Data schema (Request)"""
    data: List[CreateUpdateLedgerDetailsDataStructureRequest]


############################
# RESPONSE
############################

class LedgerResponse(BaseModel):
    """Ledger schema (Response)"""
    id: int
    token_address: str
    token_type: str
    country_code: str
    created: datetime


class ListAllLedgerHistoryResponse(BaseModel):
    """List All Ledger History schema (Response)"""
    result_set: ResultSet
    ledgers: List[LedgerResponse]


class RetrieveLedgerDetailsDataHistoryResponse(BaseModel):
    """Retrieve Ledger Details Data History schema (Response)"""
    account_address: str
    name: str
    address: str
    amount: int
    price: int
    balance: int
    acquisition_date: str


class RetrieveLedgerDetailsHistoryResponse(BaseModel):
    """Retrieve Ledger Details History schema (Response)"""
    token_detail_type: str
    headers: dict
    data: List[RetrieveLedgerDetailsDataHistoryResponse]
    footers: dict


class RetrieveLedgerHistoryResponse(BaseModel):
    """Retrieve Ledger History schema (Response)"""
    created: str
    token_name: str
    headers: dict
    details: List[RetrieveLedgerDetailsHistoryResponse]
    footers: dict


class LedgerDetailsDataTemplateResponse(BaseModel):
    """Ledger Details Data Template schema (Response)"""
    type: str
    source: str


class LedgerDetailsTemplateResponse(BaseModel):
    """Ledger Details Template schema (Response)"""
    token_detail_type: str
    headers: dict
    data: LedgerDetailsDataTemplateResponse
    footers: dict


class LedgerTemplateResponse(BaseModel):
    """Ledger Template schema (Response)"""
    token_name: str
    country_code: str
    headers: dict
    details: List[LedgerDetailsTemplateResponse]
    footers: dict


class LedgerDetailsDataResponse(BaseModel):
    """Ledger Details Data schema (Response)"""
    data_id: str
