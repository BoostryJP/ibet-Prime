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

from typing import Optional

from pydantic import BaseModel, Field

from app.model import EthereumAddress
from app.model.schema.personal_info import PersonalInfoInput


############################
# COMMON
############################
class SealedTxPersonalInfoInput(PersonalInfoInput):
    """Personal Information Input schema for sealed tx"""

    key_manager: str


############################
# REQUEST
############################
class SealedTxRegisterPersonalInfoRequest(BaseModel):
    """Schema for personal information registration using sealed tx (REQUEST)"""

    link_address: EthereumAddress
    personal_information: SealedTxPersonalInfoInput


class SealedTxRegisterHolderExtraInfoRequest(BaseModel):
    """Schema for holder's extra information registration using sealed tx (REQUEST)"""

    token_address: EthereumAddress
    external_id1_type: Optional[str] = Field(
        None, description="The type of external-id1", max_length=50
    )
    external_id1: Optional[str] = Field(None, description="external-id1", max_length=50)
    external_id2_type: Optional[str] = Field(
        None, description="The type of external-id2", max_length=50
    )
    external_id2: Optional[str] = Field(None, description="external-id2", max_length=50)
    external_id3_type: Optional[str] = Field(
        None, description="The type of external-id3", max_length=50
    )
    external_id3: Optional[str] = Field(None, description="external-id3", max_length=50)
