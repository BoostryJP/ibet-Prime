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
from typing import List
from pydantic import BaseModel

from app.model.schema import ResultSetResponse


############################
# REQUEST
############################

############################
# RESPONSE
############################

class BondLedgerResponse(BaseModel):
    """Bond Ledger schema (Response)"""
    id: int
    token_address: str
    country_code: str
    created: str


class ListAllBondLedgerHistoryResponse(BaseModel):
    """List All Bond Ledger History schema (Response)"""
    result_set: ResultSetResponse
    bond_ledgers: List[BondLedgerResponse]
