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
from typing import Annotated, Any

from pydantic import WrapValidator
from pydantic_core.core_schema import ValidatorFunctionWrapHandler
from web3 import Web3

from config import ZERO_ADDRESS


def ethereum_address_validator(
    value: Any, handler: ValidatorFunctionWrapHandler, *args, **kwargs
):
    """Validator for ethereum address"""
    if value is not None:
        if not isinstance(value, str):
            raise ValueError("value must be of string")
        if not Web3.is_address(value):
            raise ValueError("invalid ethereum address")
    return value


EthereumAddress = Annotated[str, WrapValidator(ethereum_address_validator)]


def checksum_ethereum_address_validator(
    value: Any, handler: ValidatorFunctionWrapHandler, *args, **kwargs
):
    """Validator for ethereum address in checksum format"""
    if value is not None:
        if not isinstance(value, str):
            raise ValueError("value must be of string")
        if not Web3.is_address(value):
            raise ValueError("invalid ethereum address")
        if not Web3.to_checksum_address(value) == value:
            raise ValueError("ethereum address must be in checksum format")
        if value == ZERO_ADDRESS:
            raise ValueError("ethereum address must not be zero address")
    return value


ChecksumEthereumAddress = Annotated[
    str, WrapValidator(checksum_ethereum_address_validator)
]


def datetime_string_validator(
    value: Any, handler: ValidatorFunctionWrapHandler, *args, **kwargs
):
    """Validate string datetime format

    - %Y/%m/%d %H:%M:%S
    """
    if value is not None:
        datetime_format = "%Y-%m-%d %H:%M:%S"

        if not isinstance(value, str):
            raise ValueError("value must be of string datetime format")

        try:
            converted = datetime.strptime(value, datetime_format)
            if value != converted.strftime(datetime_format):
                raise ValueError("value must be string datetime format")
        except ValueError:
            raise ValueError("value must be of string datetime format")
    return value


ValidatedDatetimeStr = Annotated[str, WrapValidator(datetime_string_validator)]
