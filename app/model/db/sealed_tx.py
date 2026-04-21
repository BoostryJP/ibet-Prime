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

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IbetWSTWhitelistKYCDelegatedEoa(Base):
    """EOAs delegated to execute KYC operations for IbetWST whitelist management."""

    __tablename__ = "ibet_wst_whitelist_kyc_delegated_eoa"

    # delegated key manager
    key_manager: Mapped[str] = mapped_column(String(42), primary_key=True)
    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
