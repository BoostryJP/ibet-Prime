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
from typing import List, Optional
import math

from pydantic import BaseModel, validator
from web3 import Web3


############################
# REQUEST
############################

class IbetStraightBondCreate(BaseModel):
    """ibet Straight Bond schema (Create)"""
    name: str
    symbol: str
    total_supply: int
    face_value: int
    redemption_date: str
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    interest_rate: Optional[float]
    interest_payment_date: Optional[List[str]]
    transferable: Optional[bool]
    is_redeemed: Optional[bool]
    status: Optional[bool]
    initial_offering_status: Optional[bool]
    tradable_exchange_contract_address: Optional[str]
    personal_info_contract_address: Optional[str]
    image_url: Optional[List[str]]
    contact_information: Optional[str]
    privacy_policy: Optional[str]

    @validator("interest_rate")
    def interest_rate_4_decimal_places(cls, v):
        if v is not None:
            float_data = float(v * 10 ** 4)
            int_data = int(v * 10 ** 4)
            if not math.isclose(int_data, float_data):
                raise ValueError("interest_rate must be less than or equal to four decimal places")
        return v

    @validator("tradable_exchange_contract_address")
    def tradable_exchange_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("tradable_exchange_contract_address is not a valid address")
        return v

    @validator("personal_info_contract_address")
    def personal_info_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("personal_info_contract_address is not a valid address")
        return v

    @validator("image_url")
    def image_list_length_is_less_than_3(cls, v):
        if v is not None and len(v) >= 4:
            raise ValueError("The length of the list must be less than or equal to 3")


class IbetStraightBondUpdate(BaseModel):
    """ibet Straight Bond schema (Update)"""
    face_value: Optional[int]
    interest_rate: Optional[float]
    interest_payment_date: Optional[List[str]]
    redemption_value: Optional[int]
    transferable: Optional[bool]
    image_url: Optional[List[str]]
    status: Optional[bool]
    initial_offering_status: Optional[bool]
    is_redeemed: Optional[bool]
    tradable_exchange_contract_address: Optional[str]
    personal_info_contract_address: Optional[str]
    contact_information: Optional[str]
    privacy_policy: Optional[str]

    @validator("interest_rate")
    def interest_rate_4_decimal_places(cls, v):
        if v is not None:
            float_data = float(v * 10 ** 4)
            int_data = int(v * 10 ** 4)
            if not math.isclose(int_data, float_data):
                raise ValueError("interest_rate must be rounded to 4 decimal places")
        return v

    @validator("interest_payment_date")
    def interest_payment_date_list_length_less_than_13(cls, v):
        if v is not None and len(v) >= 13:
            raise ValueError("list length of interest_payment_date must be less than 13")
        return v

    @validator("tradable_exchange_contract_address")
    def tradable_exchange_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("tradable_exchange_contract_address is not a valid address")
        return v

    @validator("personal_info_contract_address")
    def personal_info_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("personal_info_contract_address is not a valid address")
        return v


class IbetStraightBondAdd(BaseModel):
    """ibet Straight Bond schema (Additional Issue)"""
    account_address: str
    amount: int

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v

    @validator("amount")
    def amount_must_be_greater_than_0(cls, v):
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class IbetStraightBondTransfer(BaseModel):
    """ibet Straight Bond schema (Transfer)"""
    token_address: str
    transfer_from: str
    transfer_to: str
    amount: int

    @validator("token_address")
    def token_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("token_address is not a valid address")
        return v

    @validator("transfer_from")
    def transfer_from_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("transfer_from is not a valid address")
        return v

    @validator("transfer_to")
    def transfer_to_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("transfer_to is not a valid address")
        return v

    @validator("amount")
    def amount_must_be_greater_than_0(cls, v):
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class IbetShareCreate(BaseModel):
    """ibet Share schema (Create)"""
    name: str
    symbol: str
    issue_price: int
    total_supply: int
    dividends: float
    dividend_record_date: str
    dividend_payment_date: str
    cancellation_date: str
    image_url: Optional[List[str]]
    transferable: Optional[bool]
    status: Optional[bool]
    offering_status: Optional[bool]
    tradable_exchange_contract_address: Optional[str]
    personal_info_contract_address: Optional[str]
    contact_information: Optional[str]
    privacy_policy: Optional[str]

    @validator("dividends")
    def dividends_2_decimal_places(cls, v):
        if v is not None:
            float_data = float(v * 10 ** 4)
            int_data = int(v * 10 ** 4)
            if not math.isclose(int_data, float_data):
                raise ValueError("dividends must be less than or equal to four decimal places")
        return v

    @validator("tradable_exchange_contract_address")
    def tradable_exchange_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("tradable_exchange_contract_address is not a valid address")
        return v

    @validator("personal_info_contract_address")
    def personal_info_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("personal_info_contract_address is not a valid address")
        return v

    @validator("image_url")
    def image_list_length_is_less_than_3(cls, v):
        if v is not None and len(v) >= 4:
            raise ValueError("The length of the list must be less than or equal to 3")


class IbetShareUpdate(BaseModel):
    """ibet Share schema (Update)"""
    cancellation_date: Optional[str]
    dividend_record_date: Optional[str]
    dividend_payment_date: Optional[str]
    dividends: Optional[float]
    tradable_exchange_contract_address: Optional[str]
    personal_info_contract_address: Optional[str]
    image_url: Optional[List[str]]
    transferable: Optional[bool]
    status: Optional[bool]
    offering_status: Optional[bool]
    contact_information: Optional[str]
    privacy_policy: Optional[str]

    @validator("dividends")
    def dividends_2_decimal_places(cls, v):
        if v is not None:
            float_data = float(v * 10 ** 2)
            int_data = int(v * 10 ** 2)
            if not math.isclose(int_data, float_data):
                raise ValueError("dividends must be rounded to 2 decimal places")
        return v

    @validator("dividends")
    def dividend_information_all_required(cls, v, values, **kwargs):
        if v is not None:
            if values["dividend_record_date"] is None or values["dividend_payment_date"] is None:
                raise ValueError("all items are required to update the dividend information")
        return v

    @validator("tradable_exchange_contract_address")
    def tradable_exchange_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("tradable_exchange_contract_address is not a valid address")
        return v

    @validator("personal_info_contract_address")
    def personal_info_contract_address_is_valid_address(cls, v):
        if v is not None and not Web3.isAddress(v):
            raise ValueError("personal_info_contract_address is not a valid address")
        return v


class IbetShareTransfer(BaseModel):
    """ibet Share schema (Transfer)"""
    token_address: str
    transfer_from: str
    transfer_to: str
    amount: int

    @validator("token_address")
    def token_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("token_address is not a valid address")
        return v

    @validator("transfer_from")
    def transfer_from_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("transfer_from is not a valid address")
        return v

    @validator("transfer_to")
    def transfer_to_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("transfer_to is not a valid address")
        return v

    @validator("amount")
    def amount_must_be_greater_than_0(cls, v):
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class IbetShareAdd(BaseModel):
    """ibet Share schema (Additional Issue)"""
    account_address: str
    amount: int

    @validator("account_address")
    def account_address_is_valid_address(cls, v):
        if not Web3.isAddress(v):
            raise ValueError("account_address is not a valid address")
        return v

    @validator("amount")
    def amount_must_be_greater_than_0(cls, v):
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


############################
# RESPONSE
############################

class TokenAddressResponse(BaseModel):
    """token address"""
    token_address: str


class IbetStraightBondResponse(BaseModel):
    """ibet Straight Bond schema (Response)"""
    issuer_address: str
    token_address: str
    name: str
    symbol: str
    total_supply: int
    face_value: int
    redemption_date: str
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    interest_rate: float
    interest_payment_date: List[str]
    transferable: bool
    is_redeemed: bool
    status: bool
    initial_offering_status: bool
    tradable_exchange_contract_address: str
    personal_info_contract_address: str
    image_url: List[str]
    contact_information: str
    privacy_policy: str


class IbetShareResponse(BaseModel):
    """ibet Share schema (Response)"""
    issuer_address: str
    token_address: str
    name: str
    symbol: str
    issue_price: int
    total_supply: int
    dividends: float
    dividend_record_date: str
    dividend_payment_date: str
    cancellation_date: str
    image_url: List[str]
    transferable: bool
    status: bool
    offering_status: bool
    tradable_exchange_contract_address: str
    personal_info_contract_address: str
    contact_information: str
    privacy_policy: str
