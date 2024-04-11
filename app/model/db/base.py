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

import time
from datetime import UTC, date as datetime_date, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.database import get_db_schema


def aware_utcnow():
    return datetime.now(UTC)


def naive_utcnow():
    return aware_utcnow().replace(tzinfo=None)


class Base(DeclarativeBase):
    # created datetime(UTC)
    created: Mapped[datetime | None] = mapped_column(DateTime, default=naive_utcnow)
    # modified datetime(UTC)
    modified: Mapped[datetime | None] = mapped_column(
        DateTime, default=naive_utcnow, onupdate=naive_utcnow
    )

    @staticmethod
    def datetime_to_timestamp(date):
        if isinstance(date, datetime_date):
            return int(time.mktime(date.timetuple()))
        else:
            return None


schema = get_db_schema()
if schema is not None:
    setattr(Base, "__table_args__", {"schema": schema})
