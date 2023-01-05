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
from typing import (
    List,
    Optional
)

from fastapi import (
    APIRouter,
    Header,
    Query,
    Depends
)
from fastapi.exceptions import HTTPException
from sqlalchemy import (
    func,
    desc
)
from sqlalchemy.orm import Session

from config import TZ
from app.database import db_session
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract
)
from app.utils.fastapi import json_response
from app.utils.check_utils import (
    validate_headers,
    address_is_valid_address
)
from app.utils.ledger_utils import create_ledger
from app.utils.docs_utils import get_routers_responses
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
    tags=["token_common"],
)

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /ledger/{token_address}/history
@router.get(
    "/{token_address}/history",
    response_model=ListAllLedgerHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_all_ledger_history(
        token_address: str,
        issuer_address: Optional[str] = Header(None),
        offset: int = Query(None),
        limit: int = Query(None),
        db: Session = Depends(db_session)):
    """List all Ledger"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.token_status != 2). \
            first()
    else:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_status != 2). \
            first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    query = db.query(Ledger). \
        filter(Ledger.token_address == token_address). \
        order_by(desc(Ledger.id))
    total = query.count()

    # NOTE: Because it don`t filter, `total` and `count` will be the same.
    count = total

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
            "total": total
        },
        "ledgers": ledgers
    }

    return json_response(resp)


# GET: /ledger/{token_address}/history/{ledger_id}
@router.get(
    "/{token_address}/history/{ledger_id}",
    response_model=RetrieveLedgerHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def retrieve_ledger_history(
        token_address: str,
        ledger_id: int,
        issuer_address: Optional[str] = Header(None),
        latest_flg: int = Query(..., ge=0, le=1),
        db: Session = Depends(db_session)):
    """Retrieve Ledger"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.token_status != 2). \
            first()
    else:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_status != 2). \
            first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Ledger Exist Check
    _ledger = db.query(Ledger). \
        filter(Ledger.id == ledger_id). \
        filter(Ledger.token_address == token_address). \
        first()
    if _ledger is None:
        raise HTTPException(status_code=404, detail="ledger does not exist")

    resp = _ledger.ledger

    if latest_flg == 1:  # Get the latest personal info
        # Get ibet fin token_detail_type
        _ibet_fin_details_list = db.query(LedgerDetailsTemplate). \
            filter(LedgerDetailsTemplate.token_address == token_address). \
            filter(LedgerDetailsTemplate.data_type == LedgerDetailsDataType.IBET_FIN.value). \
            order_by(LedgerDetailsTemplate.id). \
            all()
        _ibet_fin_token_detail_type_list = [_details.token_detail_type for _details in _ibet_fin_details_list]
        # Update PersonalInfo
        for details in resp["details"]:
            if details["token_detail_type"] in _ibet_fin_token_detail_type_list:
                for data in details["data"]:
                    personal_info = __get_personal_info(
                        token_address=token_address,
                        token_type=_token.type,
                        account_address=data["account_address"],
                        db=db
                    )
                    if personal_info is not None:
                        data["name"] = personal_info.get("name", None)
                        data["address"] = personal_info.get("address", None)

    return json_response(resp)


# GET: /ledger/{token_address}/template
@router.get(
    "/{token_address}/template",
    response_model=LedgerTemplateResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def retrieve_ledger_template(
        token_address: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve Ledger Template"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.token_status != 2). \
            first()
    else:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_status != 2). \
            first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Ledger Template Exist Check
    _template = db.query(LedgerTemplate). \
        filter(LedgerTemplate.token_address == token_address). \
        first()
    if _template is None:
        raise HTTPException(status_code=404, detail="ledger template does not exist")

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

    return json_response(resp)


# POST: /ledger/{token_address}/template
@router.post(
    "/{token_address}/template",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def create_update_ledger_template(
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
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

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
            _details.data_type = details.data.type.value
            _details.data_source = details.data.source
            _details.footers = details.footers
            db.add(_details)
        else:
            # Update Ledger Details Template
            _details.headers = details.headers
            _details.data_type = details.data.type.value
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

    # Create Ledger
    create_ledger(token_address, db)

    db.commit()
    return


# DELETE: /ledger/{token_address}/template
@router.delete(
    "/{token_address}/template",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def delete_ledger_template(
        token_address: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Delete Ledger Template"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Delete Ledger Template
    _template = db.query(LedgerTemplate). \
        filter(LedgerTemplate.token_address == token_address). \
        first()
    if _template is None:
        raise HTTPException(status_code=404, detail="ledger template does not exist")
    db.delete(_template)

    # Delete Ledger Details Template
    _details_list = db.query(LedgerDetailsTemplate). \
        filter(LedgerDetailsTemplate.token_address == token_address). \
        all()
    for _details in _details_list:
        db.delete(_details)

    db.commit()
    return


# GET: /ledger/{token_address}/details_data
@router.get(
    "/{token_address}/details_data",
    response_model=ListAllLedgerDetailsDataResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_all_ledger_details_data(
        token_address: str,
        issuer_address: Optional[str] = Header(None),
        offset: int = Query(None),
        limit: int = Query(None),
        db: Session = Depends(db_session)):
    """List all Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.token_status != 2). \
            first()
    else:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_status != 2). \
            first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Ledger Details Data(summary data_id)
    query = db.query(LedgerDetailsData.data_id,
                     func.count(LedgerDetailsData.data_id),
                     func.max(LedgerDetailsData.data_created)). \
        filter(LedgerDetailsData.token_address == token_address). \
        group_by(LedgerDetailsData.data_id). \
        order_by(LedgerDetailsData.data_id)
    total = query.count()

    # NOTE: Because it don`t filter, `total` and `count` will be the same.
    count = total

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
            "total": total
        },
        "details_data": details_data
    }

    return json_response(resp)


# POST: /ledger/{token_address}/details_data
@router.post(
    "/{token_address}/details_data",
    response_model=LedgerDetailsDataResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def create_ledger_details_data(
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
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    data_id = str(uuid.uuid4())
    for data in data_list:
        _details_data = LedgerDetailsData()
        _details_data.token_address = token_address
        _details_data.data_id = data_id
        _details_data.name = getattr(data, "name") or ""
        _details_data.address = getattr(data, "address") or ""
        _details_data.amount = data.amount
        _details_data.price = data.price
        _details_data.balance = data.balance
        _details_data.acquisition_date = data.acquisition_date
        db.add(_details_data)

    db.commit()
    return json_response({
        "data_id": data_id
    })


# GET: /ledger/{token_address}/details_data/{data_id}
@router.get(
    "/{token_address}/details_data/{data_id}",
    response_model=List[RetrieveLedgerDetailsDataResponse],
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def retrieve_ledger_details_data(
        token_address: str,
        data_id: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.token_status != 2). \
            first()
    else:
        _token = db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_status != 2). \
            first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

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

    return json_response(resp)


# POST: /ledger/{token_address}/details_data/{data_id}
@router.post(
    "/{token_address}/details_data/{data_id}",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def update_ledger_details_data(
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
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

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

    # Create Ledger
    create_ledger(token_address, db)

    db.commit()
    return


# DELETE: /ledger/{token_address}/details_data/{data_id}
@router.delete(
    "/{token_address}/details_data/{data_id}",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def delete_ledger_details_data(
        token_address: str,
        data_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Delete Ledger Details Data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = db.query(Token). \
        filter(Token.token_address == token_address). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

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
    token = db.query(Token). \
        filter(Token.token_address == token_address). \
        first()
    if token is None:
        return None
    else:
        issuer_address = token.issuer_address
        _idx_personal_info = db.query(IDXPersonalInfo). \
            filter(IDXPersonalInfo.account_address == account_address). \
            filter(IDXPersonalInfo.issuer_address == issuer_address). \
            first()
        if _idx_personal_info is not None:
            # Get personal info from DB
            personal_info = _idx_personal_info.personal_info
        else:
            # Get personal info from contract
            token_contract = None
            if token_type == TokenType.IBET_SHARE.value:
                token_contract = IbetShareContract.get(token_address)
            elif token_type == TokenType.IBET_STRAIGHT_BOND.value:
                token_contract = IbetStraightBondContract.get(token_address)
            personal_info_contract = PersonalInfoContract(
                db=db,
                issuer_address=issuer_address,
                contract_address=token_contract.personal_info_contract_address
            )
            personal_info = personal_info_contract.get_info(
                account_address=account_address,
                default_value=None
            )
        return personal_info
