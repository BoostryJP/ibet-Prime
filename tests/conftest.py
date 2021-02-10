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
import os
import sys
import pytest

from fastapi.testclient import TestClient

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.main import app
from app.database import SessionLocal, engine, db_session


@pytest.fixture(scope='session')
def client():
    client = TestClient(app)
    return client


@pytest.fixture(scope='function')
def db():
    # Create DB session
    db = SessionLocal()

    def override_inject_db_session():
        return db

    # Replace target API's dependency DB session.
    app.dependency_overrides[db_session] = override_inject_db_session

    # Create DB tables
    from app.model.db import Base
    Base.metadata.create_all(engine)

    yield db

    # Remove DB tables
    db.rollback()
    Base.metadata.drop_all(engine)
    db.close()

    app.dependency_overrides[db_session] = db_session
