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

from enum import IntEnum, StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field, NonNegativeInt, StringConstraints
from typing_extensions import Annotated


############################
# COMMON
############################
class IbetStraightBondContractVersion(StrEnum):
    V_22_12 = "22_12"
    V_23_12 = "23_12"
    V_24_06 = "24_06"
    V_24_09 = "24_09"


class IbetShareContractVersion(StrEnum):
    V_22_12 = "22_12"
    V_24_06 = "24_06"
    V_24_09 = "24_09"


MMDD_constr = Annotated[
    str, StringConstraints(pattern="^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$")
]
YYYYMMDD_constr = Annotated[
    str,
    StringConstraints(
        pattern="^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
    ),
]
CURRENCY_str = Annotated[str, StringConstraints(min_length=3, max_length=3)]
EMPTY_str = Literal[""]


class TokenType(StrEnum):
    IBET_STRAIGHT_BOND = "IbetStraightBond"
    IBET_SHARE = "IbetShare"


class KeyManagerType(StrEnum):
    SELF = "SELF"
    OTHERS = "OTHERS"


class ValueOperator(IntEnum):
    EQUAL = 0
    GTE = 1
    LTE = 2


############################
# REQUEST
############################
class SortOrder(IntEnum):
    """Sort order (0: ASC, 1: DESC)"""

    ASC = 0
    DESC = 1


class BasePaginationQuery(BaseModel):
    offset: Optional[NonNegativeInt] = Field(None, description="Offset for pagination")
    limit: Optional[NonNegativeInt] = Field(None, description="Limit for pagination")


############################
# RESPONSE
############################
class ResultSet(BaseModel):
    """result set for pagination"""

    count: Optional[int] = Field(...)
    offset: Optional[int] = Field(...)
    limit: Optional[int] = Field(...)
    total: Optional[int] = Field(...)
