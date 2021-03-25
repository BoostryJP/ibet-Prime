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
from sqlalchemy import Column, String, Integer, BigInteger, Boolean

from ..base import Base


class CorporateBondLedgerTemplateJPN(Base):
    """Corporate Bond Ledger Template (JPN)"""
    __tablename__ = 'corporate_bond_ledger_template_jpn'

    # sequence id
    id = Column(Integer, primary_key=True, autoincrement=True)
    # token address
    token_address = Column(String(42), index=True)
    # issuer address
    issuer_address = Column(String(42), index=True)
    # corporate bond name
    bond_name = Column(String(200), nullable=False)
    # corporate bond description
    bond_description = Column(String(1000), nullable=False)
    # corporate bond type
    bond_type = Column(String(1000), nullable=False)
    # corporate bond total amount
    total_amount = Column(BigInteger, nullable=False)
    # corporate bond face value
    face_value = Column(Integer, nullable=False)
    # payment information - amount
    payment_amount = Column(BigInteger)
    # payment information - date
    payment_date = Column(String(8))
    # payment information - status
    payment_status = Column(Boolean, nullable=False)
    # bond ledger admin name
    ledger_admin_name = Column(String(200), nullable=False)
    # bond ledger admin address
    ledger_admin_address = Column(String(200), nullable=False)
    # bond ledger admin location
    ledger_admin_location = Column(String(200), nullable=False)
