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

from pydantic import BaseModel

from app.model import EthereumAddress
from app.model.schema.personal_info import PersonalInfoInput


############################
# REQUEST
############################
class SealedTxPersonalInfoInput(PersonalInfoInput):
    """Personal Information Input schema for sealed tx"""

    key_manager: str


############################
# REQUEST
############################
class SealedTxRegisterPersonalInfoRequest(BaseModel):
    """Schema for personal information registration using sealed tx(REQUEST)"""

    link_address: EthereumAddress
    personal_information: SealedTxPersonalInfoInput
