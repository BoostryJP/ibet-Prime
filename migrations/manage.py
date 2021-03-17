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
import sys
import os

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from sqlalchemy import Table

from app.database import engine, get_db_schema
from app.model.db import Base


def reset():
    meta = Base.metadata
    meta.bind = engine
    table = Table("alembic_version", meta, schema=get_db_schema())
    if table.exists():
        table.drop()


argv = sys.argv

if len(argv) > 0:
    if argv[1] == "reset":
        reset()
