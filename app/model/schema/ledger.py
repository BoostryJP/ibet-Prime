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
class CreateUpdateLedgerTemplateRightsRequest(BaseModel):
    """Create or Update Ledger Template Rights schema (Request)"""
    rights_name: str
    is_uploaded_details: Optional[bool]
    item: Optional[dict]
    details_item: Optional[dict]

    @validator("rights_name")
    def rights_name_length_is_less_than_100(cls, v):
        if len(v) > 100:
            raise ValueError("The length must be less than or equal to 100")
        return v


class CreateUpdateLedgerTemplateRequest(BaseModel):
    """Create or Update Ledger Template schema (Request)"""
    ledger_name: str
    country_code: str
    item: Optional[dict]
    rights: List[CreateUpdateLedgerTemplateRightsRequest]

    @validator("ledger_name")
    def ledger_name_length_is_less_than_200(cls, v):
        if len(v) > 200:
            raise ValueError("The length must be less than or equal to 200")
        return v

    @validator("country_code")
    def country_code_is_enabled(cls, v):
        upper = v.upper()
        if upper not in SYSTEM_LOCALE:
            raise ValueError("Not supported country_code")
        return v

    @validator("rights")
    def rights_length_is_greater_than_1(cls, v):
        if len(v) < 1:
            raise ValueError("The length must be greater than or equal to 1")
        return v


class CreateLedgerRightsDetailsStructureRequest(BaseModel):
    """Create Ledger Rights Details Structure schema (Request)"""
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


class CreateLedgerRightsDetailsRequest(BaseModel):
    """Create Ledger Rights Details schema (Request)"""
    rights_name: str
    details: List[CreateLedgerRightsDetailsStructureRequest]


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


class LedgerTemplateRightsResponse(BaseModel):
    """Ledger Template Rights schema (Response)"""
    rights_name: str
    is_uploaded_details: bool
    item: dict
    details_item: dict


class ListAllLedgerHistoryResponse(BaseModel):
    """List All Ledger History schema (Response)"""
    result_set: ResultSet
    ledgers: List[LedgerResponse]


class LedgerTemplateResponse(BaseModel):
    """Ledger Template schema (Response)"""
    ledger_name: str
    country_code: str
    item: dict
    rights: List[LedgerTemplateRightsResponse]
