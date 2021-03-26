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
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.model.db import Token, TokenType, UTXO, BondLedger, CorporateBondLedgerTemplateJPN, IDXPersonalInfo
from app.model.blockchain import IbetStraightBondContract, PersonalInfoContract

JST = timezone(timedelta(hours=+9), "JST")


def on_bond_ledger(token_address: str, db: Session):
    """
    This function is executed by PROCESSOR-Create-UTXO.
    Because PROCESSOR-Create-UTXO registers a data to UTXO, When TokenContract Transfer Event.
    The total amount for each account address is taken from UTXO in that time cross section and record to bond ledger.
    """

    # Token Type Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
        first()
    if _token is None:
        return
    token_contract = IbetStraightBondContract.get(token_address)

    created_date = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(JST).strftime("%Y/%m/%d")

    # Get bond ledger template
    _template = db.query(CorporateBondLedgerTemplateJPN). \
        filter(CorporateBondLedgerTemplateJPN.token_address == token_contract.token_address). \
        first()

    bond_info = __get_bond_info(_template)
    headquarters = __get_headquarters(_template)
    creditors = __get_creditors(token_contract, db)

    ledger = {
        "社債原簿作成日": created_date,
        "社債情報": bond_info,
        "社債原簿管理人": headquarters,
        "社債権者": creditors
    }

    # Create bond ledger
    _bond_ledger = BondLedger()
    _bond_ledger.token_address = token_contract.token_address
    _bond_ledger.ledger = ledger
    _bond_ledger.country_code = "JPN"
    db.add(_bond_ledger)


def __get_bond_info(_template: CorporateBondLedgerTemplateJPN):
    bond_info = {
        "社債名称": "",
        "社債の説明": "",
        "社債の総額": None,
        "各社債の金額": None,
        "払込情報": {
            "払込金額": None,
            "払込日": "",
            "払込状況": None
        },
        "社債の種類": ""
    }
    if _template is not None:
        # Update with template
        bond_info["社債名称"] = _template.bond_name
        bond_info["社債の説明"] = _template.bond_description
        bond_info["社債の総額"] = _template.total_amount
        bond_info["各社債の金額"] = _template.face_value
        payment_info = bond_info["払込情報"]
        payment_info["払込金額"] = _template.payment_amount
        payment_info["払込日"] = _template.payment_date
        payment_info["払込状況"] = _template.payment_status
        bond_info["社債の種類"] = _template.bond_type

    return bond_info


def __get_headquarters(_template: CorporateBondLedgerTemplateJPN):
    headquarters = {
        "氏名または名称": "",
        "住所": "",
        "事務取扱場所": ""
    }
    if _template is not None:
        # Update with template
        headquarters["氏名または名称"] = _template.hq_name
        headquarters["住所"] = _template.hq_address
        headquarters["事務取扱場所"] = _template.hq_office_address

    return headquarters


def __get_creditors(token_contract: IbetStraightBondContract, db: Session):
    issuer_address = token_contract.issuer_address
    face_value = token_contract.face_value
    personal_info_contract = PersonalInfoContract(
        db, issuer_address, contract_address=token_contract.personal_info_contract_address)

    _utxo_list = db.query(UTXO). \
        filter(UTXO.token_address == token_contract.token_address). \
        filter(UTXO.amount > 0). \
        order_by(UTXO.account_address, UTXO.block_timestamp). \
        all()

    # NOTE: UTXO grouping
    #       account_address
    #       - block_timestamp(YYYY/MM/DD JST)
    #         - sum(amount)
    utxo_grouped = {}
    for _utxo in _utxo_list:
        block_timestamp_jst = _utxo.block_timestamp.replace(tzinfo=timezone.utc).astimezone(JST)
        date_jst = block_timestamp_jst.strftime("%Y/%m/%d")
        if _utxo.account_address not in utxo_grouped:
            utxo_grouped[_utxo.account_address] = {
                date_jst: _utxo.amount
            }
        else:
            if date_jst not in utxo_grouped[_utxo.account_address]:
                utxo_grouped[_utxo.account_address][date_jst] = _utxo.amount
            else:
                utxo_grouped[_utxo.account_address][date_jst] += _utxo.amount

    creditors = []
    for account_address, date_jst_amount in utxo_grouped.items():
        for date_jst, amount in date_jst_amount.items():
            creditor = {
                "アカウントアドレス": account_address,
                "氏名または名称": "",
                "住所": "",
                "社債金額": face_value * amount,
                "取得日": date_jst,
                "金銭以外の財産給付情報": {
                    "財産の価格": "-",
                    "給付日": "-"
                },
                "債権相殺情報": {
                    "相殺する債権額": "-",
                    "相殺日": "-"
                },
                "質権情報": {
                    "質権者の氏名または名称": "-",
                    "質権者の住所": "-",
                    "質権の目的である債券": "-"
                },
                "備考": "-"
            }

            # Update PersonalInfo
            personal_info = __get_personal_info(account_address, issuer_address, personal_info_contract, db)
            creditor["氏名または名称"] = personal_info.get("name")
            creditor["住所"] = personal_info.get("address")

            creditors.append(creditor)

    return creditors


def __get_personal_info(account_address: str, issuer_address: str,
                        personal_info_contract: PersonalInfoContract, db: Session):
    _idx_personal_info = db.query(IDXPersonalInfo). \
        filter(IDXPersonalInfo.account_address == account_address). \
        filter(IDXPersonalInfo.issuer_address == issuer_address). \
        first()

    if _idx_personal_info is None:  # Get PersonalInfo to Contract
        personal_info = personal_info_contract.get_info(account_address, default_value="")
    else:
        personal_info = _idx_personal_info.personal_info

    return personal_info
