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
import uuid
from datetime import datetime

import pytz
from sqlalchemy.orm import Session

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
    LedgerDetailsData,
    LedgerTemplate,
    LedgerDetailsTemplate,
    LedgerDetailsDataType,
    Notification,
    NotificationType
)

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


def create_ledger(token_address: str, db: Session):
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status == 1). \
        first()
    if _token.type != TokenType.IBET_SHARE.value and _token.type != TokenType.IBET_STRAIGHT_BOND.value:
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
        # Get ledger details data
        data_list = __get_details_data_list(token_address, _token.type, _details.data_type,
                                            _details.data_source, db)

        # NOTE: Merge with template with ledger GET API
        details = {
            "token_detail_type": _details.token_detail_type,
            "headers": _details.headers,
            "data": data_list,
            "footers": _details.footers,
        }
        ledger_details.append(details)

    created_ymd = utc_tz.localize(datetime.utcnow()).astimezone(local_tz).strftime("%Y/%m/%d")
    # NOTE: Merge with template with ledger GET API
    ledger = {
        "created": created_ymd,
        "token_name": _template.token_name,
        "headers": _template.headers,
        "details": ledger_details,
        "footers": _template.footers,
    }

    # Register ledger data to the DB
    # NOTE: DB commit is executed by the caller
    _ledger = Ledger()
    _ledger.token_address = token_address
    _ledger.token_type = _token.type
    _ledger.ledger = ledger
    db.add(_ledger)

    # Although autoflush is enabled, there is no operation invoking flush.
    # Execute flush here to get ledger id which is auto incremented.
    db.flush()
    
    # Register Notification to the DB
    # NOTE: DB commit is executed by the caller
    _notification = Notification()
    _notification.notice_id = uuid.uuid4()
    _notification.issuer_address = _token.issuer_address
    _notification.priority = 0  # Low
    _notification.type = NotificationType.CREATE_LEDGER_INFO
    _notification.code = 0
    _notification.metainfo = {
        "token_address": token_address,
        "token_type": _token.type,
        "ledger_id": _ledger.id
    }
    db.add(_notification)


def __get_details_data_list(token_address: str, token_type: str, data_type: str, data_source: str, db: Session):
    data_list = []
    if data_type == LedgerDetailsDataType.DB.value:
        data_list = []
        # Get Ledger Details Data from DB
        _details_data_list = db.query(LedgerDetailsData). \
            filter(LedgerDetailsData.token_address == token_address). \
            filter(LedgerDetailsData.data_id == data_source). \
            order_by(LedgerDetailsData.id). \
            all()
        for _details_data in _details_data_list:
            data_list.append({
                "account_address": None,
                "name": _details_data.name,
                "address": _details_data.address,
                "amount": _details_data.amount,
                "price": _details_data.price,
                "balance": _details_data.balance,
                "acquisition_date": _details_data.acquisition_date,
            })
    elif data_type == LedgerDetailsDataType.IBET_FIN.value:
        data_list = __get_details_data_list_from_ibetfin(token_address, token_type, db)

    return data_list


def __get_details_data_list_from_ibetfin(token_address: str, token_type: str, db: Session):
    if token_type == TokenType.IBET_SHARE.value:
        token_contract = IbetShareContract.get(token_address)
        price = token_contract.principal_value
    elif token_type == TokenType.IBET_STRAIGHT_BOND.value:
        token_contract = IbetStraightBondContract.get(token_address)
        price = token_contract.face_value

    issuer_address = token_contract.issuer_address
    personal_info_contract = PersonalInfoContract(
        db,
        issuer_address,
        contract_address=token_contract.personal_info_contract_address
    )

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
                "name": None,
                "address": None,
                "amount": amount,
                "price": price,
                "balance": price * amount,
                "acquisition_date": date_ymd,
            }

            # Update PersonalInfo
            personal_info = __get_personal_info(account_address, issuer_address, personal_info_contract, db)
            details_data["name"] = personal_info.get("name", None)
            details_data["address"] = personal_info.get("address", None)

            data_list.append(details_data)

    return data_list


def __get_personal_info(account_address: str, issuer_address: str, personal_info_contract: PersonalInfoContract,
                        db: Session):
    _idx_personal_info = db.query(IDXPersonalInfo). \
        filter(IDXPersonalInfo.account_address == account_address). \
        filter(IDXPersonalInfo.issuer_address == issuer_address). \
        first()

    if _idx_personal_info is None:  # Get PersonalInfo to Contract
        personal_info = personal_info_contract.get_info(account_address, default_value=None)
    else:
        personal_info = _idx_personal_info.personal_info

    return personal_info
