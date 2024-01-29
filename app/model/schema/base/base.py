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

from enum import Enum, IntEnum, StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated


############################
# COMMON
############################
class IbetStraightBondContractVersion(StrEnum):
    V_22_12 = "22_12"
    V_23_12 = "23_12"


class IbetShareContractVersion(StrEnum):
    V_22_12 = "22_12"


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


class TokenType(str, Enum):
    IBET_STRAIGHT_BOND = "IbetStraightBond"
    IBET_SHARE = "IbetShare"


############################
# REQUEST
############################
class SortOrder(IntEnum):
    ASC = 0
    DESC = 1


############################
# RESPONSE
############################
class ResultSet(BaseModel):
    """result set for pagination"""

    count: Optional[int] = Field(...)
    offset: Optional[int] = Field(...)
    limit: Optional[int] = Field(...)
    total: Optional[int] = Field(...)
