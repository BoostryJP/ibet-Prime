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
from typing import Optional
from pydantic import BaseModel, validator


############################
# REQUEST
############################
class CreateUpdateBondLedgerTemplateRequestJPN(BaseModel):
    """Create or Update Bond Ledger Template schema (REQUEST JPN)"""
    bond_name: str
    bond_description: str
    bond_type: str
    total_amount: int
    face_value: int
    payment_amount: Optional[int]
    payment_date: Optional[str]
    payment_status: Optional[bool]
    hq_name: str
    hq_address: str
    hq_office_address: str

    @validator("bond_name")
    def bond_name_length_is_less_than_200(cls, v):
        if len(v) > 200:
            raise ValueError("The length must be less than or equal to 200")
        return v

    @validator("bond_description")
    def bond_description_length_is_less_than_1000(cls, v):
        if len(v) > 1000:
            raise ValueError("The length must be less than or equal to 1000")
        return v

    @validator("bond_type")
    def bond_type_length_is_less_than_1000(cls, v):
        if len(v) > 1000:
            raise ValueError("The length must be less than or equal to 1000")
        return v

    @validator("total_amount")
    def total_amount_range_is_0_to_1_000_000_000_000(cls, v):
        if v < 0 or v > 1_000_000_000_000:
            raise ValueError("The range must be 0 to 1,000,000,000,000")
        return v

    @validator("face_value")
    def face_value_range_is_0_to_100_000_000(cls, v):
        if v < 0 or v > 100_000_000:
            raise ValueError("The range must be 0 to 100,000,000")
        return v

    @validator("payment_amount")
    def payment_amount_range_is_0_to_1_000_000_000_000(cls, v):
        if v is not None:
            if v < 0 or v > 1_000_000_000_000:
                raise ValueError("The range must be 0 to 1,000,000,000,000")
        return v

    @validator("payment_date")
    def payment_date_format_is_YYYYMMDD(cls, v):
        if v is not None:
            try:
                if len(v) != 8:
                    raise ValueError
                datetime.strptime(v, "%Y%m%d")
            except ValueError:
                raise ValueError("The date format must be YYYYMMDD")
        return v

    @validator("hq_name")
    def hq_name_length_is_less_than_200(cls, v):
        if len(v) > 200:
            raise ValueError("The length must be less than or equal to 200")
        return v

    @validator("hq_address")
    def hq_address_length_is_less_than_200(cls, v):
        if len(v) > 200:
            raise ValueError("The length must be less than or equal to 200")
        return v

    @validator("hq_office_address")
    def hq_office_address_length_is_less_than_200(cls, v):
        if len(v) > 200:
            raise ValueError("The length must be less than or equal to 200")
        return v
