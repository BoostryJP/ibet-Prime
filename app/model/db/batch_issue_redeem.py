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
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean
)

from .base import Base


class BatchIssueRedeemUpload(Base):
    """Batch Issue/Redeem Upload"""
    __tablename__ = 'batch_issue_redeem_upload'

    # upload id (UUID)
    upload_id = Column(String(36), primary_key=True)
    # issuer address
    issuer_address = Column(String(42), nullable=False, index=True)
    # token type
    token_type = Column(String(40), nullable=False)
    # token address
    token_address = Column(String(42), nullable=False)
    # processing category (BatchIssueRedeemProcessingCategory)
    category = Column(String(20), nullable=False)
    # processed status
    processed = Column(Boolean, default=False, index=True)


class BatchIssueRedeemProcessingCategory(Enum):
    """Batch Issue/Redeem Category"""
    ISSUE = "Issue"
    REDEEM = "Redeem"


class BatchIssueRedeem(Base):
    """Batch Issue/Redeem Data"""
    __tablename__ = "batch_issue_redeem"

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # upload id (UUID)
    upload_id = Column(String(36), index=True)
    # target account
    account_address = Column(String(42), nullable=False)
    # amount
    amount = Column(Integer, nullable=False)
    # processing status (pending:0, succeeded:1, failed:2)
    status = Column(Integer, nullable=False, index=True)