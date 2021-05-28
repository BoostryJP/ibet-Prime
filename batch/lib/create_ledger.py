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

from config import TZ
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
    LedgerTemplate,
    LedgerDetailsTemplate,
    LedgerDetailsDataType
)

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
    if _template is None:
        return

    # Get ledger details
    _details_list = db.query(LedgerDetailsTemplate). \
        filter(LedgerDetailsTemplate.token_address == token_address). \
        order_by(LedgerDetailsTemplate.id). \
        all()
    ledger_details = []
    for _details in _details_list:
        data_list  = []
        if _details.data_type == LedgerDetailsDataType.IBET_FIN:
            # Get ledger details dataibetfin)
            data_list = __get_details_data_list_from_ibetfin(token_address, _token.type, db)

        # NOTE: Merge with template with ledger GET API
        details = {
            "token_detail_type": _details.token_detail_type,
            "headers": [],
            "data": data_list,
            "footers": [],
        }
        ledger_details.append(details)

    created_ymd = utc_tz.localize(datetime.utcnow()).astimezone(local_tz).strftime("%Y/%m/%d")
    # NOTE: Merge with template with ledger GET API
    ledger = {
        "created": created_ymd,
        "token_name": "",
        "headers": [],
        "details": ledger_details,
        "footers": [],
    }

    # Register ledger data to the DB
    # NOTE: DB commit is executed by the caller
    _ledger = Ledger()
    _ledger.token_address = token_address
    _ledger.token_type = _token.type
    _ledger.ledger = ledger
    db.add(_ledger)


def __get_details_data_list_from_ibetfin(token_address: str, token_type: str, db: Session):
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

    data_list = []
    for account_address, date_ymd_amount in utxo_grouped.items():
        for date_ymd, amount in date_ymd_amount.items():
            details_data = {
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
            details_data["name"] = personal_info.get("name", "")
            details_data["address"] = personal_info.get("address", "")

            data_list.append(details_data)

    return data_list


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
