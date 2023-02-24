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
from datetime import date as datetime_date
import time

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.orm import declarative_base

from app.database import get_db_schema


class BaseModel(object):
    # created datetime(UTC)
    created = Column(DateTime, default=datetime.utcnow)
    # modified datetime(UTC)
    modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def datetime_to_timestamp(date):
        if isinstance(date, datetime_date):
            return int(time.mktime(date.timetuple()))
        else:
            return None


Base = declarative_base(cls=BaseModel)

schema = get_db_schema()
if schema is not None:
    setattr(Base, "__table_args__", {"schema": schema})
