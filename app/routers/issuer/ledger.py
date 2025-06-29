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
from typing import List, Optional, Sequence

import pytz
from fastapi import APIRouter, Header, Query
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import log
from app.database import DBAsyncSession
from app.exceptions import Integer64bitLimitExceededError, InvalidParameterError
from app.model.db import (
    Account,
    IDXPersonalInfo,
    Ledger,
    LedgerDataType,
    LedgerDetailsData,
    LedgerDetailsTemplate,
    LedgerTemplate,
    Token,
    TokenStatus,
    TokenType,
)
from app.model.ibet import (
    ContractPersonalInfoType,
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract,
)
from app.model.schema import (
    CreateUpdateLedgerDetailsDataRequest,
    CreateUpdateLedgerTemplateRequest,
    LedgerDetailsDataResponse,
    LedgerTemplateResponse,
    ListAllLedgerDetailsDataResponse,
    ListAllLedgerHistoryResponse,
    RetrieveLedgerDetailsDataResponse,
    RetrieveLedgerHistoryResponse,
)
from app.utils.check_utils import address_is_valid_address, validate_headers
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.ibet_ledger_utils import request_ledger_creation
from config import TZ

router = APIRouter(
    prefix="/ledger",
    tags=["token_common"],
)
LOG = log.get_logger()
local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /ledger/{token_address}/history
@router.get(
    "/{token_address}/history",
    operation_id="ListAllLedgerHistory",
    response_model=ListAllLedgerHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_all_ledger_history(
    db: DBAsyncSession,
    token_address: str,
    issuer_address: Optional[str] = Header(None),
    offset: int = Query(None),
    limit: int = Query(None),
):
    """List all ledger history"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    else:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.issuer_address == issuer_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    stmt = (
        select(Ledger)
        .where(Ledger.token_address == token_address)
        .order_by(desc(Ledger.id))
    )

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Ledger).order_by(None)
    )

    # NOTE: Because it don`t filter, `total` and `count` will be the same.
    count = total

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _ledger_list: Sequence[Ledger] = (await db.scalars(stmt)).all()

    ledgers = []
    for _ledger in _ledger_list:
        created_formatted = (
            utc_tz.localize(_ledger.ledger_created).astimezone(local_tz).isoformat()
        )
        ledgers.append(
            {
                "id": _ledger.id,
                "token_address": _ledger.token_address,
                "token_type": _ledger.token_type,
                "created": created_formatted,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "ledgers": ledgers,
    }

    return json_response(resp)


# GET: /ledger/{token_address}/history/{ledger_id}
@router.get(
    "/{token_address}/history/{ledger_id}",
    operation_id="RetrieveLedgerHistory",
    response_model=RetrieveLedgerHistoryResponse,
    responses=get_routers_responses(
        422, 404, InvalidParameterError, Integer64bitLimitExceededError
    ),
)
async def retrieve_ledger_history(
    db: DBAsyncSession,
    token_address: str,
    ledger_id: int,
    issuer_address: Optional[str] = Header(None),
    latest_flg: int = Query(..., ge=0, le=1),
):
    """Retrieve ledger history"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    else:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.issuer_address == issuer_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Ledger Exist Check
    _ledger: Ledger | None = (
        await db.scalars(
            select(Ledger)
            .where(and_(Ledger.id == ledger_id, Ledger.token_address == token_address))
            .limit(1)
        )
    ).first()
    if _ledger is None:
        raise HTTPException(status_code=404, detail="ledger does not exist")

    resp: dict = _ledger.ledger

    # For backward compatibility, set the default value if `currency` is not set.
    if resp.get("currency") is None:
        resp["currency"] = ""

    if latest_flg == 1:  # Get the latest personal info
        # Get ibet fin token_detail_type
        _ibet_fin_details_list: Sequence[LedgerDetailsTemplate] = (
            await db.scalars(
                select(LedgerDetailsTemplate)
                .where(
                    and_(
                        LedgerDetailsTemplate.token_address == token_address,
                        LedgerDetailsTemplate.data_type == LedgerDataType.IBET_FIN,
                    )
                )
                .order_by(LedgerDetailsTemplate.id)
            )
        ).all()
        _ibet_fin_token_detail_type_list = [
            _details.token_detail_type for _details in _ibet_fin_details_list
        ]
        # Update PersonalInfo
        some_personal_info_not_registered = False
        for details in resp["details"]:
            if details["token_detail_type"] in _ibet_fin_token_detail_type_list:
                for data in details["data"]:
                    if data["account_address"] == "":
                        # For data whose data source is DB, the account_address is set to "".
                        # Here, control logic is implemented assuming that
                        # an inconsistency has occurred in the data_type of LedgerDetailsTemplate,
                        # resulting in a value other than "DB".
                        # In this case, personal information will not be updated.
                        continue
                    else:
                        personal_info, _pi_not_registered = await __get_personal_info(
                            token_address=token_address,
                            token_type=_token.type,
                            account_address=data["account_address"],
                            db=db,
                        )
                        data["name"] = personal_info.get("name", None)
                        data["address"] = personal_info.get("address", None)
                        if _pi_not_registered:
                            some_personal_info_not_registered = True
            details["some_personal_info_not_registered"] = (
                some_personal_info_not_registered
            )
    else:
        # NOTE: Implementation for backward compatibility
        #   In specifications prior to v24.6, the item "some_personal_info_not_registered" does not exist,
        #   so data for which the item does not exist is overwritten with False.
        for details in resp["details"]:
            if details.get("some_personal_info_not_registered") is None:
                details["some_personal_info_not_registered"] = False

    return json_response(resp)


# GET: /ledger/{token_address}/template
@router.get(
    "/{token_address}/template",
    operation_id="RetrieveLedgerTemplate",
    response_model=LedgerTemplateResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def retrieve_ledger_template(
    db: DBAsyncSession,
    token_address: str,
    issuer_address: Optional[str] = Header(None),
):
    """Retrieve ledger template"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    else:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.issuer_address == issuer_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Ledger Template Exist Check
    _template: LedgerTemplate | None = (
        await db.scalars(
            select(LedgerTemplate)
            .where(LedgerTemplate.token_address == token_address)
            .limit(1)
        )
    ).first()
    if _template is None:
        raise HTTPException(status_code=404, detail="ledger template does not exist")

    # Get Ledger Details Template
    _details_list: Sequence[LedgerDetailsTemplate] = (
        await db.scalars(
            select(LedgerDetailsTemplate)
            .where(LedgerDetailsTemplate.token_address == token_address)
            .order_by(LedgerDetailsTemplate.id)
        )
    ).all()
    details = []
    for _details in _details_list:
        details.append(
            {
                "token_detail_type": _details.token_detail_type,
                "headers": _details.headers,
                "data": {
                    "type": _details.data_type,
                    "source": _details.data_source,
                },
                "footers": _details.footers,
            }
        )

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
    operation_id="CreateUpdateLedgerTemplate",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def create_update_ledger_template(
    db: DBAsyncSession,
    token_address: str,
    data: CreateUpdateLedgerTemplateRequest,
    issuer_address: str = Header(...),
):
    """Create or Update Ledger Template"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == token_address,
                    Token.issuer_address == issuer_address,
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Ledger Template
    _template: LedgerTemplate | None = (
        await db.scalars(
            select(LedgerTemplate)
            .where(LedgerTemplate.token_address == token_address)
            .limit(1)
        )
    ).first()

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
        await db.merge(_template)

    # NOTE: Data that is not subject to the updater will be deleted later
    _details_list: Sequence[LedgerDetailsTemplate] = (
        await db.scalars(
            select(LedgerDetailsTemplate).where(
                LedgerDetailsTemplate.token_address == token_address
            )
        )
    ).all()
    delete_details_token_detail_type = [
        _details.token_detail_type for _details in _details_list
    ]

    for details in data.details:
        _details: LedgerDetailsTemplate | None = (
            await db.scalars(
                select(LedgerDetailsTemplate)
                .where(
                    and_(
                        LedgerDetailsTemplate.token_address == token_address,
                        LedgerDetailsTemplate.token_detail_type
                        == details.token_detail_type,
                    )
                )
                .limit(1)
            )
        ).first()
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
            await db.merge(_details)
            if details.token_detail_type in delete_details_token_detail_type:
                delete_details_token_detail_type.remove(details.token_detail_type)

    # Delete Ledger Details Template
    for token_detail_type in delete_details_token_detail_type:
        await db.execute(
            delete(LedgerDetailsTemplate).where(
                LedgerDetailsTemplate.token_address == token_address,
                LedgerDetailsTemplate.token_detail_type == token_detail_type,
            )
        )

    # Request Ledger Creation
    await request_ledger_creation(db, token_address)

    await db.commit()
    return


# DELETE: /ledger/{token_address}/template
@router.delete(
    "/{token_address}/template",
    operation_id="DeleteLedgerTemplate",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def delete_ledger_template(
    db: DBAsyncSession,
    token_address: str,
    issuer_address: str = Header(...),
):
    """Delete ledger template"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == token_address,
                    Token.issuer_address == issuer_address,
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Delete Ledger Template
    _template = (
        await db.scalars(
            select(LedgerTemplate)
            .where(LedgerTemplate.token_address == token_address)
            .limit(1)
        )
    ).first()
    if _template is None:
        raise HTTPException(status_code=404, detail="ledger template does not exist")
    await db.delete(_template)

    # Delete Ledger Details Template
    await db.execute(
        delete(LedgerDetailsTemplate).where(
            LedgerDetailsTemplate.token_address == token_address
        )
    )

    await db.commit()
    return


# GET: /ledger/{token_address}/details_data
@router.get(
    "/{token_address}/details_data",
    operation_id="ListAllLedgerDetailsData",
    response_model=ListAllLedgerDetailsDataResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_all_ledger_details_data(
    db: DBAsyncSession,
    token_address: str,
    issuer_address: Optional[str] = Header(None),
    offset: int = Query(None),
    limit: int = Query(None),
):
    """List all ledger details data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    else:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.issuer_address == issuer_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Ledger Details Data(summary data_id)
    stmt = (
        select(
            LedgerDetailsData.data_id,
            func.count(LedgerDetailsData.data_id),
            func.max(LedgerDetailsData.data_created),
        )
        .where(LedgerDetailsData.token_address == token_address)
        .group_by(LedgerDetailsData.data_id)
        .order_by(LedgerDetailsData.data_id)
    )

    # NOTE: This API does not filter the data, so count equals total.
    total = await db.scalar(
        select(func.count()).select_from(stmt.with_only_columns(1).order_by(None))
    )
    count = total

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _details_data_list: Sequence[tuple[str, int, datetime]] = (
        (await db.execute(stmt)).tuples().all()
    )

    details_data = []
    for _data_id, _count, _created in _details_data_list:
        created_formatted = utc_tz.localize(_created).astimezone(local_tz).isoformat()
        details_data.append(
            {
                "data_id": _data_id,
                "count": _count,
                "created": created_formatted,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "details_data": details_data,
    }

    return json_response(resp)


# POST: /ledger/{token_address}/details_data
@router.post(
    "/{token_address}/details_data",
    operation_id="CreateLedgerDetailsData",
    response_model=LedgerDetailsDataResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def create_ledger_details_data(
    db: DBAsyncSession,
    token_address: str,
    data_list: List[CreateUpdateLedgerDetailsDataRequest],
    issuer_address: str = Header(...),
):
    """Create ledger details data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == token_address,
                    Token.issuer_address == issuer_address,
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
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

    await db.commit()
    return json_response({"data_id": data_id})


# GET: /ledger/{token_address}/details_data/{data_id}
@router.get(
    "/{token_address}/details_data/{data_id}",
    operation_id="RetrieveLedgerDetailsData",
    response_model=List[RetrieveLedgerDetailsDataResponse],
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def retrieve_ledger_details_data(
    db: DBAsyncSession,
    token_address: str,
    data_id: str,
    issuer_address: Optional[str] = Header(None),
):
    """Retrieve ledger details data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Token Exist Check
    if issuer_address is None:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    else:
        _token: Token | None = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == token_address,
                        Token.issuer_address == issuer_address,
                        Token.token_status != TokenStatus.FAILED,
                    )
                )
                .limit(1)
            )
        ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Ledger Details Data
    _details_data_list: Sequence[LedgerDetailsData] = (
        await db.scalars(
            select(LedgerDetailsData).where(
                and_(
                    LedgerDetailsData.token_address == token_address,
                    LedgerDetailsData.data_id == data_id,
                )
            )
        )
    ).all()

    resp = []
    for _details_data in _details_data_list:
        resp.append(
            {
                "name": _details_data.name,
                "address": _details_data.address,
                "amount": _details_data.amount,
                "price": _details_data.price,
                "balance": _details_data.balance,
                "acquisition_date": _details_data.acquisition_date,
            }
        )

    return json_response(resp)


# POST: /ledger/{token_address}/details_data/{data_id}
@router.post(
    "/{token_address}/details_data/{data_id}",
    operation_id="UpdateLedgerDetailsData",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def update_ledger_details_data(
    db: DBAsyncSession,
    token_address: str,
    data_id: str,
    data_list: List[CreateUpdateLedgerDetailsDataRequest],
    issuer_address: str = Header(...),
):
    """Update ledger details data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == token_address,
                    Token.issuer_address == issuer_address,
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Delete + Insert Ledger Details Data
    await db.execute(
        delete(LedgerDetailsData).where(
            and_(
                LedgerDetailsData.token_address == token_address,
                LedgerDetailsData.data_id == data_id,
            )
        )
    )
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

    # Request Ledger Creation
    await request_ledger_creation(db, token_address)

    await db.commit()
    return


# DELETE: /ledger/{token_address}/details_data/{data_id}
@router.delete(
    "/{token_address}/details_data/{data_id}",
    operation_id="DeleteLedgerDetailsData",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def delete_ledger_details_data(
    db: DBAsyncSession,
    token_address: str,
    data_id: str,
    issuer_address: str = Header(...),
):
    """Delete ledger details data"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Issuer Management Token Check
    _token = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == token_address,
                    Token.issuer_address == issuer_address,
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token does not exist")
    if _token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Delete Ledger Details Data
    await db.execute(
        delete(LedgerDetailsData).where(
            and_(
                LedgerDetailsData.token_address == token_address,
                LedgerDetailsData.data_id == data_id,
            )
        )
    )

    await db.commit()
    return


async def __get_personal_info(
    token_address: str, token_type: str, account_address: str, db: AsyncSession
) -> tuple[dict, bool]:
    # NOTE:
    # For tokens with require_personal_info_registered = False, search only indexed data.
    # If indexed data does not exist, return the default value.

    token: Token | None = (
        await db.scalars(
            select(Token).where(Token.token_address == token_address).limit(1)
        )
    ).first()
    if token is None:
        personal_info_not_registered = True
        return ContractPersonalInfoType().model_dump(), personal_info_not_registered

    # Issuer cannot have any personal info
    if account_address == token.issuer_address:
        personal_info_not_registered = False
        return (
            ContractPersonalInfoType(
                key_manager=None,
                name=None,
                address=None,
                postal_code=None,
                email=None,
                birth=None,
            ).model_dump(),
            personal_info_not_registered,
        )

    # Search indexed data
    _idx_personal_info: IDXPersonalInfo | None = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == account_address,
                    IDXPersonalInfo.issuer_address == token.issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if (
        _idx_personal_info is not None
        and any(_idx_personal_info.personal_info.values()) is not False
    ):
        # Get personal info from DB
        personal_info_not_registered = False
        return _idx_personal_info.personal_info, personal_info_not_registered

    # Get token attributes
    token_contract = None
    if token_type == TokenType.IBET_SHARE.value:
        token_contract = await IbetShareContract(token_address).get()
    elif token_type == TokenType.IBET_STRAIGHT_BOND.value:
        token_contract = await IbetStraightBondContract(token_address).get()

    if token_contract.require_personal_info_registered is True:
        # Get issuer account
        issuer_account = (
            await db.scalars(
                select(Account)
                .where(Account.issuer_address == token.issuer_address)
                .limit(1)
            )
        ).first()

        # Retrieve personal info from contract storage
        personal_info_contract = PersonalInfoContract(
            logger=LOG,
            issuer=issuer_account,
            contract_address=token_contract.personal_info_contract_address,
        )
        personal_info = await personal_info_contract.get_info(
            account_address=account_address, default_value=None
        )
        if any(personal_info.values()) is False:
            personal_info_not_registered = True
        else:
            personal_info_not_registered = False
    else:
        # Do not retrieve contract data and return the default value
        personal_info = ContractPersonalInfoType().model_dump()
        personal_info_not_registered = True

    return personal_info, personal_info_not_registered
