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
from datetime import datetime

import pytz
from sqlalchemy.orm import Session

path = os.path.join(os.path.dirname(__file__), '../../')
sys.path.append(path)

from config import (
    SYSTEM_LOCALE,
    TZ
)
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract
)
from app.model.db import (
    Token,
    TokenType,
    UTXO,
    IDXPersonalInfo,
    Ledger,
    LedgerRightsDetails,
    LedgerTemplate,
    LedgerTemplateRights
)
from batch.localized import create_ledger_JPN

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


def create_ledger(token_address: str, db: Session):
    """
    This function is executed by PROCESSOR-Create-UTXO.
    Because PROCESSOR-Create-UTXO registers a data to UTXO, When TokenContract Transfer Event.
    The total amount for each account address is taken from UTXO in that time cross section and record to ledger.
    """

    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        first()
    if _token.type != TokenType.IBET_SHARE and _token.type != TokenType.IBET_STRAIGHT_BOND:
        return

    _template = db.query(LedgerTemplate). \
        filter(LedgerTemplate.token_address == token_address). \
        first()

    if _template is not None:

        created_key, ledger_name_key, item_key, rights_key, rights_name_key, details_key = \
            "created", "ledger_name", "item", "rights", "rights_name", "details"
        if _template.country_code == "JPN":
            created_key, ledger_name_key, item_key, rights_key, rights_name_key, details_key = \
                create_ledger_JPN.get_ledger_keys()

        # Set ledger common key
        created_ymd = utc_tz.localize(datetime.utcnow()).astimezone(local_tz).strftime("%Y/%m/%d")
        ledger = {
            created_key: created_ymd,
            ledger_name_key: _template.ledger_name,
            item_key: _template.item
        }

        # Set ledger rights
        _rights_list = db.query(LedgerTemplateRights). \
            filter(LedgerTemplateRights.token_address == token_address). \
            order_by(LedgerTemplateRights.id). \
            all()
        ledger_rights = []
        for _rights in _rights_list:
            # Set ledger rights common key
            rights = {
                rights_name_key: _rights.rights_name,
                item_key: _rights.item
            }

            # Set ledger rights details
            details = __get_rights_details(_rights, _token.type, _template.country_code, db)
            rights[details_key] = details

            ledger_rights.append(rights)

        ledger[rights_key] = ledger_rights
        country_code = _template.country_code
    else:
        if "JPN" in SYSTEM_LOCALE and _token.type == TokenType.IBET_STRAIGHT_BOND:
            # Create default corporate bond ledger
            details = __get_rights_blockchain_details(token_address, _token.type, db)
            ledger = create_ledger_JPN.get_default_corporate_bond_ledger(details)
            country_code = "JPN"
        else:
            return

    # Register ledger data to the DB
    # NOTE: DB commit is executed by the caller
    _ledger = Ledger()
    _ledger.token_address = token_address
    _ledger.token_type = _token.type
    _ledger.ledger = ledger
    _ledger.country_code = country_code
    db.add(_ledger)


def __get_rights_details(_rights: LedgerTemplateRights, token_type: str, country_code: str, db: Session):
    if _rights.is_uploaded_details:
        _rights_details_list = db.query(LedgerRightsDetails). \
            filter(LedgerRightsDetails.token_address == _rights.token_address). \
            filter(LedgerRightsDetails.rights_name == _rights.rights_name). \
            order_by(LedgerRightsDetails.id). \
            all()
        details = []
        for _rights_details in _rights_details_list:
            details.append({
                "account_address": _rights_details.account_address,
                "name": _rights_details.name,
                "address": _rights_details.address,
                "amount": _rights_details.amount,
                "price": _rights_details.price,
                "balance": _rights_details.balance,
                "acquisition_date": _rights_details.acquisition_date,
            })
    else:
        # from blockchain
        details = __get_rights_blockchain_details(_rights.token_address, token_type, db)

    # Set ledger rights details item
    for detail in details:
        detail.update(_rights.details_item)

    # Convert structured item key language
    if country_code == "JPN":
        details = create_ledger_JPN.convert_details_item(details)

    return details


def __get_rights_blockchain_details(token_address: str, token_type: str, db: Session):
    if token_type == TokenType.IBET_SHARE:
        token_contract = IbetShareContract.get(token_address)
        price = token_contract.principal_value
    elif token_type == TokenType.IBET_STRAIGHT_BOND:
        token_contract = IbetStraightBondContract.get(token_address)
        price = token_contract.face_value

    issuer_address = token_contract.issuer_address
    personal_info_contract = PersonalInfoContract(
        db, issuer_address, contract_address=token_contract.personal_info_contract_address)

    # Get token holders from UTXO
    _utxo_list = db.query(UTXO). \
        filter(UTXO.token_address == token_contract.token_address). \
        filter(UTXO.amount > 0). \
        order_by(UTXO.account_address, UTXO.block_timestamp). \
        all()

    # NOTE: UTXO grouping
    #       account_address
    #       - block_timestamp(YYYY/MM/DD)
    #         - sum(amount)
    utxo_grouped = {}
    for _utxo in _utxo_list:
        date_ymd = utc_tz.localize(_utxo.block_timestamp).astimezone(local_tz).strftime("%Y/%m/%d")
        if _utxo.account_address not in utxo_grouped:
            utxo_grouped[_utxo.account_address] = {
                date_ymd: _utxo.amount
            }
        else:
            if date_ymd not in utxo_grouped[_utxo.account_address]:
                utxo_grouped[_utxo.account_address][date_ymd] = _utxo.amount
            else:
                utxo_grouped[_utxo.account_address][date_ymd] += _utxo.amount

    details = []
    for account_address, date_ymd_amount in utxo_grouped.items():
        for date_ymd, amount in date_ymd_amount.items():
            detail = {
                "account_address": account_address,
                "name": "",
                "address": "",
                "amount": amount,
                "price": price,
                "balance": price * amount,
                "acquisition_date": date_ymd,
            }

            # Update PersonalInfo
            personal_info = __get_personal_info(account_address, issuer_address, personal_info_contract, db)
            detail["name"] = personal_info.get("name", "")
            detail["address"] = personal_info.get("address", "")

            details.append(detail)

    return details


def __get_personal_info(account_address: str, issuer_address: str, personal_info_contract: PersonalInfoContract,
                        db: Session):
    _idx_personal_info = db.query(IDXPersonalInfo). \
        filter(IDXPersonalInfo.account_address == account_address). \
        filter(IDXPersonalInfo.issuer_address == issuer_address). \
        first()

    if _idx_personal_info is None:  # Get PersonalInfo to Contract
        personal_info = personal_info_contract.get_info(account_address, default_value="")
    else:
        personal_info = _idx_personal_info.personal_info

    return personal_info
