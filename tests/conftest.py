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
import pytest

from fastapi.testclient import TestClient
from web3 import Web3
from web3.middleware import geth_poa_middleware

import config
from app import main
import app.database
from app.database import SessionLocal, engine, db_session

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope='session')
def client():
    client = TestClient(main.app)
    return client


# セッションの作成、テーブルの自動作成・自動削除
@pytest.fixture(scope='function')
def db():
    # セッションの作成
    db = SessionLocal()

    def override_inject_db_session():
        return db

    # テストメソッドのDBセッションと同一オブジェクトとなるようAPIのDIを上書き
    app.main.app.dependency_overrides[db_session] = override_inject_db_session

    # テーブルの自動作成
    from app.model.db import Base
    Base.metadata.create_all(engine)

    yield db

    # テーブルの自動削除
    db.rollback()
    Base.metadata.drop_all(engine)
    db.close()

    app.main.app.dependency_overrides[db_session] = db_session
