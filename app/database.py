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

from typing import Annotated

from fastapi import Depends
from sqlalchemy import AsyncAdaptedQueuePool, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from config import ASYNC_DATABASE_URL, DATABASE_SCHEMA, DATABASE_URL, DB_ECHO


def get_engine(uri: str):
    options = {
        "pool_recycle": 3600,
        "pool_size": 10,
        "pool_timeout": 30,
        "pool_pre_ping": True,
        "max_overflow": 30,
        "echo": DB_ECHO,
    }
    return create_engine(uri, **options)


def get_async_engine(uri: str):
    options = {
        "poolclass": AsyncAdaptedQueuePool,
        "pool_recycle": 3600,
        "pool_size": 10,
        "pool_timeout": 30,
        "pool_pre_ping": True,
        "max_overflow": 30,
        "echo": DB_ECHO,
    }
    return create_async_engine(uri, **options)


def get_batch_async_engine(uri: str):
    options = {
        "poolclass": AsyncAdaptedQueuePool,
        "pool_pre_ping": True,
        "echo": False,
    }
    return create_async_engine(uri, **options)


# Create Engine
engine = get_engine(DATABASE_URL)
async_engine = get_async_engine(ASYNC_DATABASE_URL)
batch_async_engine = get_batch_async_engine(ASYNC_DATABASE_URL)

# Create Session Maker
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=True,
    expire_on_commit=False,
    bind=async_engine,
    class_=AsyncSession,
)
BatchAsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=True,
    expire_on_commit=False,
    bind=batch_async_engine,
    class_=AsyncSession,
)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def db_async_session():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


DBSession = Annotated[Session, Depends(db_session)]
DBAsyncSession = Annotated[AsyncSession, Depends(db_async_session)]


def get_db_schema():
    return DATABASE_SCHEMA
