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
from enum import Enum
from typing import Optional

from pydantic import (
    BaseModel,
    constr
)


MMDD_constr = constr(regex="^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$")
YYYYMMDD_constr = constr(regex="^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$")


class ResultSet(BaseModel):
    """result set for pagination"""
    count: Optional[int]
    offset: Optional[int]
    limit: Optional[int]
    total: Optional[int]


class TransferApprovalsSortItem(str, Enum):
    ID = "id"
    APPLICATION_ID = "application_id"
    FROM_ADDRESS = "from_address"
    TO_ADDRESS = "to_address"
    AMOUNT = "amount"
    APPLICATION_DATETIME = "application_datetime"
    APPROVAL_DATETIME = "approval_datetime"
    STATUS = "status"
