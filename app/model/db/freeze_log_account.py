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

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class FreezeLogAccount(Base):
    """Account for Freeze-Logging"""

    __tablename__ = "freeze_log_account"

    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # ethereum keyfile
    keyfile: Mapped[dict | None] = mapped_column(JSON)
    # ethereum account password(encrypted)
    eoa_password: Mapped[str | None] = mapped_column(String(2000))
    # delete flag
    is_deleted: Mapped[bool | None] = mapped_column(Boolean, default=False)
