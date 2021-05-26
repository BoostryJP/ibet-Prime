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
import pytz
from typing import List
from fastapi import (
    APIRouter,
    Header,
    Query,
    Depends
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import TZ
from app.database import db_session
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract
)
from app.model.utils import (
    validate_headers,
    address_is_valid_address
)
from app.model.db import (
    Token,
    TokenType,
    IDXPersonalInfo,
    Ledger,
    LedgerDetailsData,
    LedgerTemplate,
    LedgerDetailsTemplate,
    LedgerDetailsDataType
)
from app.model.schema import (
    CreateUpdateLedgerTemplateRequest,
    CreateUpdateLedgerDetailsDataRequest,
    ListAllLedgerHistoryResponse,
    RetrieveLedgerHistoryResponse,
    LedgerTemplateResponse,
    ListAllLedgerDetailsDataResponse,
    LedgerDetailsDataResponse,
    RetrieveLedgerDetailsDataResponse
)
from app.exceptions import InvalidParameterError

router = APIRouter(
    prefix="/ledger",
    tags=["ledger"],
    responses={404: {"description": "Not found"}},
)

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /ledger/{token_address}/history
@router.get("/{token_address}/history", response_model=ListAllLedgerHistoryResponse)
async def list_all_ledger_history(
        token_address: str,
        issuer_address: str = Header(...),
        offset: int = Query(None),
        limit: int = Query(None),
        db: Session = Depends(db_session)):
    """List all Ledger"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    query = db.query(Ledger). \
        filter(Ledger.token_address == token_address). \
        order_by(Ledger.id)
    count = query.count()

    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _ledger_list = query.all()

    ledgers = []
    for _ledger in _ledger_list:
        created_formatted = utc_tz.localize(_ledger.ledger_created).astimezone(local_tz).isoformat()
        ledgers.append({
            "id": _ledger.id,
            "token_address": _ledger.token_address,
            "token_type": _ledger.token_type,
            "created": created_formatted,
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": count
        },
        "ledgers": ledgers
    }

    return resp


# GET: /ledger/{token_address}/history/{ledger_id}
@router.get("/{token_address}/history/{ledger_id}", response_model=RetrieveLedgerHistoryResponse)
async def retrieve_ledger_history(
        token_address: str,
        ledger_id: int,
        issuer_address: str = Header(...),
        latest_flg: int = Query(..., ge=0, le=1),
        db: Session = Depends(db_session)):
    """Retrieve Ledger"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Ledger Exist Check
    _ledger = db.query(Ledger). \
        filter(Ledger.id == ledger_id). \
        filter(Ledger.token_address == token_address). \
        first()
    if _ledger is None:
        raise InvalidParameterError("ledger does not exist")

    # Ledger Template Exist Check
    _template = db.query(LedgerTemplate). \
        filter(LedgerTemplate.token_address == token_address). \
        filter(LedgerTemplate.issuer_address == issuer_address). \
        first()
    if _template is None:
        raise InvalidParameterError("ledger template does not exist")

    ledger = _ledger.ledger

    # Merge Ledger Template
    ledger["token_name"] = _template.token_name
    ledger["headers"] = _template.headers
    ledger["footers"] = _template.footers

    # Merge Ledger Details Template
    _details_list = db.query(LedgerDetailsTemplate). \
        filter(LedgerDetailsTemplate.token_address == token_address). \
        order_by(LedgerDetailsTemplate.id). \
        all()
    tmp_details = ledger["details"]
    tmp_details_dict = {}
    for idx, detail in enumerate(tmp_details):
        tmp_details_dict[detail["token_detail_type"]] = idx

    ledger_details = []
    for _details in _details_list:
        data_list = []
        if _details.data_type == LedgerDetailsDataType.IBET_FIN:
            # Update existing details data in ledger(data with the same value of token_detail_type)
            # NOTE: token_detail_type not in ledger, details data is empty.
            idx = tmp_details_dict.get(_details.token_detail_type, None)
            if idx is not None:
                for data in tmp_details[idx]["data"]:
                    personal_info = {
                        "name": data["name"],
                        "address": data["address"],
                    }
                    if latest_flg == 1:  # most recent
                        personal_info = __get_personal_info(
                            token_address, _token.type, data["account_address"], db)
                    data_list.append({
                        "account_address": data["account_address"],
                        "name": personal_info["name"],
                        "address": personal_info["address"],
                        "amount": data["amount"],
                        "price": data["price"],
                        "balance": data["balance"],
                        "acquisition_date": data["acquisition_date"],
                    })
        elif _details.data_type == LedgerDetailsDataType.DB:
            # Get Ledger Details Data
            _details_data_list = db.query(LedgerDetailsData). \
                filter(LedgerDetailsData.token_address == token_address). \
                filter(LedgerDetailsData.data_id == _details.data_source). \
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

        ledger_details.append({
            "token_detail_type": _details.token_detail_type,
            "headers": _details.headers,
            "data": data_list,
            "footers": _details.footers,
        })

    ledger["details"] = ledger_details

    resp = ledger
    return resp


# GET: /ledger/{token_address}/template
@router.get("/{token_address}/template", response_model=LedgerTemplateResponse)
async def retrieve_ledger_template(
        token_address: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Retrieve Ledger Template"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Ledger Template Exist Check
    _template = db.query(LedgerTemplate). \
        filter(LedgerTemplate.token_address == token_address). \
        first()
    if _template is None:
        raise InvalidParameterError("ledger template does not exist")

    # Get Ledger Details Template
    _details_list = db.query(LedgerDetailsTemplate). \
        filter(LedgerDetailsTemplate.token_address == token_address). \
        order_by(LedgerDetailsTemplate.id). \
        all()
    details = []
    for _details in _details_list:
        details.append({
            "token_detail_type": _details.token_detail_type,
            "headers": _details.headers,
            "data": {
                "type": _details.data_type,
                "source": _details.data_source,
            },
            "footers": _details.footers,
        })

    resp = {
        "token_name": _template.token_name,
        "headers": _template.headers,
        "details": details,
        "footers": _template.footers,
    }

    return resp


# POST: /ledger/{token_address}/template
@router.post("/{token_address}/template")
async def create_update_ledger_template(
        token_address: str,
        data: CreateUpdateLedgerTemplateRequest,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Create or Update Ledger Template"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Get Ledger Template
    _template = db.query(LedgerTemplate). \
        filter(LedgerTemplate.token_address == token_address). \
        first()

    if _template is None:
        # Create Template:Ledger
        _template = LedgerTemplate()
        _template.token_address = token_address
        _template.issuer_address = issuer_address
        _template.token_name = data.token_name
        _template.headers = data.headers
        _template.footers = data.footers
        db.add(_template)
    else:
        # Update Template: Ledger
        _template.token_name = data.token_name
        _template.headers = data.headers
        _template.footers = data.footers
        db.merge(_template)

    # NOTE: Data that is not subject to the updater will be deleted later
    _details_list = db.query(LedgerDetailsTemplate). \
        filter(LedgerDetailsTemplate.token_address == token_address). \
        all()
    delete_details_token_detail_type = [_details.token_detail_type for _details in _details_list]

    for details in data.details:

        _details = db.query(LedgerDetailsTemplate). \
            filter(LedgerDetailsTemplate.token_address == token_address). \
            filter(LedgerDetailsTemplate.token_detail_type == details.token_detail_type). \
            first()
        if _details is None:
            # Create Ledger Details Template
            _details = LedgerDetailsTemplate()
            _details.token_address = token_address
            _details.token_detail_type = details.token_detail_type
            _details.headers = details.headers
            _details.data_type = details.data.type
            _details.data_source = details.data.source
            _details.footers = details.footers
            db.add(_details)
        else:
            # Update Ledger Details Template
            _details.headers = details.headers
            _details.data_type = details.data.type
            _details.data_source = details.data.source
            _details.footers = details.footers
            db.merge(_details)
            if details.token_detail_type in delete_details_token_detail_type:
                delete_details_token_detail_type.remove(details.token_detail_type)

    # Delete Ledger Details Template
    for token_detail_type in delete_details_token_detail_type:
        _details = db.query(LedgerDetailsTemplate). \
            filter(LedgerDetailsTemplate.token_address == token_address). \
            filter(LedgerDetailsTemplate.token_detail_type == token_detail_type). \
            first()
        db.delete(_details)

    db.commit()
    return


# GET: /ledger/{token_address}/details_data
@router.get("/{token_address}/details_data", response_model=ListAllLedgerDetailsDataResponse)
async def list_all_ledger_details_data(
        token_address: str,
        issuer_address: str = Header(...),
        offset: int = Query(None),
        limit: int = Query(None),
        db: Session = Depends(db_session)):
    """List all Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Get Ledger Details Data(summary data_id)
    query = db.query(LedgerDetailsData.data_id,
                     func.count(LedgerDetailsData.data_id),
                     func.max(LedgerDetailsData.data_created)). \
        filter(LedgerDetailsData.token_address == token_address). \
        group_by(LedgerDetailsData.data_id). \
        order_by(LedgerDetailsData.data_id)
    count = query.count()

    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _details_data_list = query.all()

    details_data = []
    for _data_id, _count, _created in _details_data_list:
        created_formatted = utc_tz.localize(_created).astimezone(local_tz).isoformat()
        details_data.append({
            "data_id": _data_id,
            "count": _count,
            "created": created_formatted,
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": count
        },
        "details_data": details_data
    }

    return resp


# POST: /ledger/{token_address}/details_data
@router.post("/{token_address}/details_data", response_model=LedgerDetailsDataResponse)
async def create_ledger_details_data(
        token_address: str,
        data_list: List[CreateUpdateLedgerDetailsDataRequest],
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Create Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    data_id = str(uuid.uuid4())
    for data in data_list:
        _details_data = LedgerDetailsData()
        _details_data.token_address = token_address
        _details_data.data_id = data_id
        _details_data.name = data.name
        _details_data.address = data.address
        _details_data.amount = data.amount
        _details_data.price = data.price
        _details_data.balance = data.balance
        _details_data.acquisition_date = data.acquisition_date
        db.add(_details_data)

    db.commit()
    return {"data_id": data_id}


# GET: /ledger/{token_address}/details_data/{data_id}
@router.get("/{token_address}/details_data/{data_id}", response_model=List[RetrieveLedgerDetailsDataResponse])
async def retrieve_ledger_details_data(
        token_address: str,
        data_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Retrieve Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Get Ledger Details Data
    _details_data_list = db.query(LedgerDetailsData). \
        filter(LedgerDetailsData.token_address == token_address). \
        filter(LedgerDetailsData.data_id == data_id). \
        all()

    resp = []
    for _details_data in _details_data_list:
        resp.append({
            "name": _details_data.name,
            "address": _details_data.address,
            "amount": _details_data.amount,
            "price": _details_data.price,
            "balance": _details_data.balance,
            "acquisition_date": _details_data.acquisition_date,
        })

    return resp


# POST: /ledger/{token_address}/details_data/{data_id}
@router.post("/{token_address}/details_data/{data_id}")
async def update_ledger_details_data(
        token_address: str,
        data_id: str,
        data_list: List[CreateUpdateLedgerDetailsDataRequest],
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Update Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Delete + Insert Ledger Details Data
    _details_data_list = db.query(LedgerDetailsData). \
        filter(LedgerDetailsData.token_address == token_address). \
        filter(LedgerDetailsData.data_id == data_id). \
        all()
    for _details_data in _details_data_list:
        db.delete(_details_data)
    for data_list in data_list:
        _details_data = LedgerDetailsData()
        _details_data.token_address = token_address
        _details_data.data_id = data_id
        _details_data.name = data_list.name
        _details_data.address = data_list.address
        _details_data.amount = data_list.amount
        _details_data.price = data_list.price
        _details_data.balance = data_list.balance
        _details_data.acquisition_date = data_list.acquisition_date
        db.add(_details_data)

    db.commit()
    return


# DELETE: /ledger/{token_address}/details_data/{data_id}
@router.delete("/{token_address}/details_data/{data_id}")
async def delete_ledger_details_data(
        token_address: str,
        data_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Update Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        first()
    if _token is None:
        raise InvalidParameterError("token does not exist")

    # Delete Ledger Details Data
    _details_data_list = db.query(LedgerDetailsData). \
        filter(LedgerDetailsData.token_address == token_address). \
        filter(LedgerDetailsData.data_id == data_id). \
        all()

    for _details_data in _details_data_list:
        db.delete(_details_data)

    db.commit()
    return


def __get_personal_info(token_address: str, token_type: str, account_address: str, db: Session):
    if token_type == TokenType.IBET_SHARE:
        token_contract = IbetShareContract.get(token_address)
    elif token_type == TokenType.IBET_STRAIGHT_BOND:
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
