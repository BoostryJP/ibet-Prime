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
from datetime import timezone, timedelta

from sqlalchemy.orm import Session

from app.model.blockchain import IbetStraightBondContract, PersonalInfoContract
from app.model.db import BondLedger, IDXPersonalInfo, CorporateBondLedgerTemplateJPN
from app.model.schema import CreateUpdateBondLedgerTemplateRequestJPN
from app.exceptions import InvalidParameterError

JST = timezone(timedelta(hours=+9), "JST")


# GET: /bond_ledger/{token_address}/history
def list_all_bond_ledger_history(
        token_address: str,
        db: Session):
    """List all Bond Ledger (JPN)"""

    _bond_ledger_list = db.query(BondLedger). \
        filter(BondLedger.token_address == token_address). \
        filter(BondLedger.country_code == "JPN"). \
        order_by(BondLedger.id). \
        all()

    resp = []
    for _bond_ledger in _bond_ledger_list:
        created_jst = _bond_ledger.bond_ledger_created.replace(tzinfo=timezone.utc).astimezone(JST)
        created_formatted = created_jst.strftime("%Y/%m/%d %H:%M:%S %z")
        bond_ledger_dict = {
            "id": _bond_ledger.id,
            "token_address": _bond_ledger.token_address,
            "country_code": _bond_ledger.country_code,
            "created": created_formatted,
        }
        resp.append(bond_ledger_dict)

    return resp


# GET: /bond_ledger/{token_address}/history/{ledger_id}
def retrieve_bond_ledger_history(
        token_address: str,
        ledger_id: int,
        issuer_address: str,
        latest_flg: int,
        db: Session):
    """Retrieve Bond Ledger (JPN)"""

    _bond_ledger = db.query(BondLedger). \
        filter(BondLedger.id == ledger_id). \
        filter(BondLedger.token_address == token_address). \
        filter(BondLedger.country_code == "JPN"). \
        first()

    resp = _bond_ledger.ledger
    if latest_flg == 1:  # most recent

        _ledger_template = db.query(CorporateBondLedgerTemplateJPN). \
            filter(CorporateBondLedgerTemplateJPN.token_address == token_address). \
            filter(CorporateBondLedgerTemplateJPN.issuer_address == issuer_address). \
            first()
        if _ledger_template is None:
            raise InvalidParameterError("ledger template does not exist")

        # Update Corporate Bond Information
        bond_info = resp["社債情報"]
        bond_info["社債名称"] = _ledger_template.bond_name
        bond_info["社債の説明"] = _ledger_template.bond_description
        bond_info["社債の総額"] = _ledger_template.total_amount
        bond_info["各社債の金額"] = _ledger_template.face_value
        payment_info = bond_info["払込情報"]
        payment_info["払込金額"] = _ledger_template.payment_amount
        payment_info["払込日"] = _ledger_template.payment_date
        payment_info["払込状況"] = _ledger_template.payment_status
        bond_info["社債の種類"] = _ledger_template.bond_type

        # Update Ledger Admin
        ledger_admin = resp["社債原簿管理人"]
        ledger_admin["氏名または名称"] = _ledger_template.ledger_admin_name
        ledger_admin["住所"] = _ledger_template.ledger_admin_address
        ledger_admin["事務取扱場所"] = _ledger_template.ledger_admin_location

        # Update Corporate Creditors
        _token_contract = IbetStraightBondContract.get(token_address)
        _personal_info_contract = PersonalInfoContract(
            db, issuer_address, contract_address=_token_contract.personal_info_contract_address)
        for creditor in resp["社債権者"]:
            account_address = creditor["アカウントアドレス"]

            _idx_personal_info = db.query(IDXPersonalInfo). \
                filter(IDXPersonalInfo.account_address == account_address). \
                filter(IDXPersonalInfo.issuer_address == issuer_address). \
                first()

            if _idx_personal_info is None:  # Get PersonalInfo to Contract
                personal_info = _personal_info_contract.get_info(account_address, default_value="")
            else:
                personal_info = _idx_personal_info.personal_info

            creditor["氏名または名称"] = personal_info.get("name", "")
            creditor["住所"] = personal_info.get("address", "")

    return resp


# GET: /bond_ledger/{token_address}/template
def retrieve_bond_ledger_template(
        token_address: str,
        issuer_address: str,
        db: Session):
    """Retrieve Bond Ledger Template (JPN)"""

    _ledger_template = db.query(CorporateBondLedgerTemplateJPN). \
        filter(CorporateBondLedgerTemplateJPN.token_address == token_address). \
        filter(CorporateBondLedgerTemplateJPN.issuer_address == issuer_address). \
        first()
    if _ledger_template is None:
        raise InvalidParameterError("ledger template does not exist")

    resp = {
        "token_address": _ledger_template.token_address,
        "bond_name": _ledger_template.bond_name,
        "bond_description": _ledger_template.bond_description,
        "bond_type": _ledger_template.bond_type,
        "total_amount": _ledger_template.total_amount,
        "face_value": _ledger_template.face_value,
        "payment_amount": _ledger_template.payment_amount,
        "payment_date": _ledger_template.payment_date,
        "payment_status": _ledger_template.payment_status,
        "ledger_admin_name": _ledger_template.ledger_admin_name,
        "ledger_admin_address": _ledger_template.ledger_admin_address,
        "ledger_admin_location": _ledger_template.ledger_admin_location,
    }

    return resp


# POST: /bond_ledger/{token_address}/template
def create_update_bond_ledger_template(
        token_address: str,
        template: CreateUpdateBondLedgerTemplateRequestJPN,
        issuer_address,
        db: Session):
    """Create or Update Bond Ledger Template (JPN)"""

    _ledger_template = db.query(CorporateBondLedgerTemplateJPN). \
        filter(CorporateBondLedgerTemplateJPN.token_address == token_address). \
        filter(CorporateBondLedgerTemplateJPN.issuer_address == issuer_address). \
        first()

    if _ledger_template is None:
        _ledger_template = CorporateBondLedgerTemplateJPN()
        _ledger_template.token_address = token_address
        _ledger_template.issuer_address = issuer_address

    # Set request param
    _ledger_template.bond_name = template.bond_name
    _ledger_template.bond_description = template.bond_description
    _ledger_template.bond_type = template.bond_type
    _ledger_template.total_amount = template.total_amount
    _ledger_template.face_value = template.face_value
    _ledger_template.payment_amount = template.payment_amount
    _ledger_template.payment_date = template.payment_date
    _ledger_template.payment_status = template.payment_status
    _ledger_template.ledger_admin_name = template.ledger_admin_name
    _ledger_template.ledger_admin_address = template.ledger_admin_address
    _ledger_template.ledger_admin_location = template.ledger_admin_location

    db.merge(_ledger_template)
    db.commit()

    return
