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
from sqlalchemy.orm import Session

from app.model.blockchain import (
    IbetStraightBondContract,
    PersonalInfoContract
)
from app.model.db import IDXPersonalInfo


def get_ledger_keys():
    return "原簿作成日", "原簿名称", "項目", "権利", "権利名称", "明細"


def get_ledger_rights_details_structure_keys():
    return "アカウントアドレス", "氏名または名称", "住所", "保有口数", "一口あたりの金額", "保有残高", "取得日"


def get_recent_default_corporate_bond_ledger(token_address: str, ledger: dict, db: Session):
    _, _, _, rights_key, _, details_key = get_ledger_keys()
    details = ledger[rights_key][0][details_key]
    for detail in details:
        account_address = detail["アカウントアドレス"]
        personal_info = __get_personal_info(token_address, account_address, db)
        detail["氏名または名称"] = personal_info["name"]
        detail["住所"] = personal_info["address"]

    return ledger


def __get_personal_info(token_address: str, account_address: str, db: Session):
    token_contract = IbetStraightBondContract.get(token_address)
    issuer_address = token_contract.issuer_address
    personal_info_contract = PersonalInfoContract(
        db, issuer_address, contract_address=token_contract.personal_info_contract_address)

    _idx_personal_info = db.query(IDXPersonalInfo). \
        filter(IDXPersonalInfo.account_address == account_address). \
        filter(IDXPersonalInfo.issuer_address == issuer_address). \
        first()

    if _idx_personal_info is None:  # Get PersonalInfo to Contract
        personal_info = personal_info_contract.get_info(account_address, default_value="")
    else:
        personal_info = _idx_personal_info.personal_info

    return personal_info
