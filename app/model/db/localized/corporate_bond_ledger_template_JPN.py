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
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Boolean
)

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
    # 社債情報.社債名称
    bond_name = Column(String(200), nullable=False)
    # corporate bond description
    # 社債情報.社債の説明
    bond_description = Column(String(1000), nullable=False)
    # corporate bond type
    # 社債情報.社債の種類
    bond_type = Column(String(1000), nullable=False)
    # corporate bond total amount
    # 社債情報.社債の総額
    total_amount = Column(BigInteger, nullable=False)
    # corporate bond face value
    # 社債情報.各社債の金額
    face_value = Column(Integer, nullable=False)
    # payment information - amount
    # 社債情報.払込情報.払込金額
    payment_amount = Column(BigInteger)
    # payment information - date
    # 社債情報.払込情報.払込日
    payment_date = Column(String(8))
    # payment information - status
    # 社債情報.払込情報.払込状況
    payment_status = Column(Boolean, nullable=False)
    # bond ledger administrator - name
    # 社債原簿管理人.氏名または名称
    ledger_admin_name = Column(String(200), nullable=False)
    # bond ledger administrator - headquarters
    # 社債原簿管理人.住所
    ledger_admin_headquarters = Column(String(200), nullable=False)
    # bond ledger administrator - office address
    # 社債原簿管理人.事務取扱場所
    ledger_admin_office_address = Column(String(200), nullable=False)
