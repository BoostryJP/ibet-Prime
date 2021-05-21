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
from typing import (
    Dict,
    Any
)

import pytz
from fastapi import (
    APIRouter,
    Header,
    Query,
    Depends
)
from sqlalchemy.orm import Session

from config import (
    TZ,
    SYSTEM_LOCALE
)
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
    LedgerRightsDetails,
    LedgerTemplate,
    LedgerTemplateRights
)
from app.model.schema import (
    CreateUpdateLedgerTemplateRequest,
    CreateLedgerRightsDetailsRequest,
    ListAllLedgerHistoryResponse,
    LedgerTemplateResponse,
)
from app.routers.localized import ledger_JPN
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
            "country_code": _ledger.country_code,
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
@router.get("/{token_address}/history/{ledger_id}", response_model=Dict[str, Any],
            response_description="Successful Response (structures differs depending on template country code.)")
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

    resp = _ledger.ledger
    if latest_flg == 1:  # most recent

        _template = db.query(LedgerTemplate). \
            filter(LedgerTemplate.token_address == token_address). \
            filter(LedgerTemplate.issuer_address == issuer_address). \
            first()

        if _template is not None:

            if _ledger.country_code != _template.country_code:
                raise InvalidParameterError("cannot be updated because country_code has changed")

            created_key, ledger_name_key, item_key, rights_key, rights_name_key, details_key = \
                "created", "ledger_name", "item", "rights", "rights_name", "details"
            account_address_key, name_key, address_key, amount_key, price_key, balance_key, acquisition_date_key = \
                "account_address", "name", "address", "amount", "price", "balance", "acquisition_date"
            if _template.country_code == "JPN":
                created_key, ledger_name_key, item_key, rights_key, rights_name_key, details_key = \
                    ledger_JPN.get_ledger_keys()
                account_address_key, name_key, address_key, amount_key, price_key, balance_key, acquisition_date_key = \
                    ledger_JPN.get_ledger_rights_details_structure_keys()

            # Update Ledger Common Key
            resp[ledger_name_key] = _template.ledger_name
            resp[item_key] = _template.item

            # Update Ledger Rights
            _rights_list = db.query(LedgerTemplateRights). \
                filter(LedgerTemplateRights.token_address == token_address). \
                order_by(LedgerTemplateRights.id). \
                all()
            ledger_rights = []
            resp_rights_name_dict = {}
            for i, rights in enumerate(resp[rights_key]):
                resp_rights_name_dict[rights[rights_name_key]] = i
            for _rights in _rights_list:
                details = []
                if not _rights.is_uploaded_details:  # From Blockchain
                    if _rights.rights_name in resp_rights_name_dict:
                        # Update existing details in ledger
                        i = resp_rights_name_dict[_rights.rights_name]
                        for detail in resp[rights_key][i][details_key]:
                            personal_info = __get_personal_info(
                                token_address, _token.type, detail[account_address_key], db)
                            detail = {
                                account_address_key: detail[account_address_key],
                                name_key: personal_info["name"],
                                address_key: personal_info["address"],
                                amount_key: detail[amount_key],
                                price_key: detail[price_key],
                                balance_key: detail[balance_key],
                                acquisition_date_key: detail[acquisition_date_key],
                            }
                            details.append(detail)
                else:  # From Database
                    _details_list = db.query(LedgerRightsDetails). \
                        filter(LedgerRightsDetails.token_address == token_address). \
                        filter(LedgerRightsDetails.rights_name == _rights.rights_name). \
                        order_by(LedgerRightsDetails.id). \
                        all()
                    for detail in _details_list:
                        detail = {
                            account_address_key: detail.account_address,
                            name_key: detail.name,
                            address_key: detail.address,
                            amount_key: detail.amount,
                            price_key: detail.price,
                            balance_key: detail.balance,
                            acquisition_date_key: detail.acquisition_date,
                        }
                        details.append(detail)

                # Set details item
                for detail in details:
                    detail.update(_rights.details_item)

                rights = {
                    rights_name_key: _rights.rights_name,
                    item_key: _rights.item,
                    details_key: details
                }
                ledger_rights.append(rights)

            resp[rights_key] = ledger_rights

        else:
            if "JPN" in SYSTEM_LOCALE and _token.type == TokenType.IBET_STRAIGHT_BOND:
                resp = ledger_JPN.get_recent_default_corporate_bond_ledger(token_address, resp, db)
            else:
                raise InvalidParameterError("ledger template does not exist")

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

    # Get Ledger Rights Template
    _rights_list = db.query(LedgerTemplateRights). \
        filter(LedgerTemplateRights.token_address == token_address). \
        order_by(LedgerTemplateRights.id). \
        all()
    rights = []
    for _rights in _rights_list:
        rights.append({
            "rights_name": _rights.rights_name,
            "item": _rights.item,
            "details_item": _rights.details_item,
            "is_uploaded_details": _rights.is_uploaded_details,
        })

    resp = {
        "ledger_name": _template.ledger_name,
        "country_code": _template.country_code,
        "item": _template.item,
        "rights": rights
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
        _template.ledger_name = data.ledger_name
        _template.country_code = data.country_code.upper()
        _template.item = data.item
        db.add(_template)
    else:
        # Update Template: Ledger
        _template.ledger_name = data.ledger_name
        _template.country_code = data.country_code.upper()
        _template.item = data.item
        db.merge(_template)

    # NOTE: Data that is not subject to the updater will be deleted later
    _rights_list = db.query(LedgerTemplateRights). \
        filter(LedgerTemplateRights.token_address == token_address). \
        all()
    not_updated_rights_name = [_rights.rights_name for _rights in _rights_list]

    details_structure_keys = "account_address", "name", "address", "amount", "price", "balance", "acquisition_date"
    if data.country_code.upper() == "JPN":
        details_structure_keys = ledger_JPN.get_ledger_rights_details_structure_keys()
    for rights in data.rights:
        if rights.details_item:
            # exclude reserved key
            tmp_details_item = rights.details_item.copy()
            for key, _ in rights.details_item.items():
                if key in details_structure_keys:
                    tmp_details_item.pop(key)
            rights.details_item = tmp_details_item

        _rights = db.query(LedgerTemplateRights). \
            filter(LedgerTemplateRights.token_address == token_address). \
            filter(LedgerTemplateRights.rights_name == rights.rights_name). \
            first()
        if _rights is None:
            # Create Template: Ledger Rights
            _rights = LedgerTemplateRights()
            _rights.token_address = token_address
            _rights.rights_name = rights.rights_name
            _rights.item = rights.item
            _rights.details_item = rights.details_item
            _rights.is_uploaded_details = rights.is_uploaded_details
            db.add(_rights)
        else:
            # Update Template: Ledger Rights
            _rights.item = rights.item
            _rights.details_item = rights.details_item
            _rights.is_uploaded_details = rights.is_uploaded_details
            db.merge(_rights)
            if rights.rights_name in not_updated_rights_name:
                not_updated_rights_name.remove(rights.rights_name)

    for rights_name in not_updated_rights_name:
        # Delete Template:Ledger Right
        _rights = db.query(LedgerTemplateRights). \
            filter(LedgerTemplateRights.token_address == token_address). \
            filter(LedgerTemplateRights.rights_name == rights_name). \
            first()
        db.delete(_rights)

        # Delete Ledger Rights Details
        _details_list = db.query(LedgerRightsDetails). \
            filter(LedgerRightsDetails.token_address == token_address). \
            filter(LedgerRightsDetails.rights_name == rights_name). \
            all()
        for _details in _details_list:
            db.delete(_details)

    db.commit()
    return


# POST: /ledger/{token_address}/rights_details
@router.post("/{token_address}/rights_details")
async def create_rights_details(
        token_address: str,
        data: CreateLedgerRightsDetailsRequest,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Create Ledger Rights Details"""

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

    # Ledger Rights Template Exist Check
    _rights = db.query(LedgerTemplateRights). \
        filter(LedgerTemplateRights.token_address == token_address). \
        filter(LedgerTemplateRights.rights_name == data.rights_name). \
        filter(LedgerTemplateRights.is_uploaded_details == True). \
        first()
    if _rights is None:
        raise InvalidParameterError("ledger rights template does not exist")

    # Delete + Insert Ledger Right Details
    _details_list = db.query(LedgerRightsDetails). \
        filter(LedgerRightsDetails.token_address == token_address). \
        filter(LedgerRightsDetails.rights_name == data.rights_name). \
        all()
    for _details in _details_list:
        db.delete(_details)
    for details in data.details:
        _details = LedgerRightsDetails()
        _details.token_address = token_address
        _details.rights_name = data.rights_name
        _details.account_address = details.account_address
        _details.name = details.name
        _details.address = details.address
        _details.amount = details.amount
        _details.price = details.price
        _details.balance = details.balance
        _details.acquisition_date = details.acquisition_date
        db.add(_details)

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
