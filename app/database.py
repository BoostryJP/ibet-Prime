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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL, DATABASE_SCHEMA, DB_ECHO, DB_AUTOCOMMIT

options = {
    "pool_recycle": 3600,
    "pool_size": 10,
    "pool_timeout": 30,
    "max_overflow": 30,
    "echo": DB_ECHO,
    "execution_options": {
        "autocommit": DB_AUTOCOMMIT
    }
}
engine = create_engine(DATABASE_URL, **options)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_schema():
    if DATABASE_SCHEMA and engine.name != "mysql":
        return DATABASE_SCHEMA
    else:
        return None
