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
from datetime import UTC, datetime
from typing import Sequence

import pytz
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import log
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
)
from app.model.db import (
    UTXO,
    IDXPersonalInfo,
    Ledger,
    LedgerCreationRequest,
    LedgerCreationRequestData,
    LedgerCreationStatus,
    LedgerDataType,
    LedgerDetailsData,
    LedgerDetailsTemplate,
    LedgerTemplate,
    Notification,
    NotificationType,
    Token,
    TokenType,
)
from config import TZ

LOG = log.get_logger()
local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


async def request_ledger_creation(db: AsyncSession, token_address: str):
    """Request ledger creation"""

    # Get token information
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(and_(Token.token_address == token_address, Token.token_status == 1))
            .limit(1)
        )
    ).first()
    if _token is None or _token.type not in TokenType:
        return

    # Get ledger template
    _template: LedgerTemplate | None = (
        await db.scalars(
            select(LedgerTemplate)
            .where(LedgerTemplate.token_address == token_address)
            .limit(1)
        )
    ).first()
    if _template is None:
        return

    # Get ledger details template
    _details_template_list: Sequence[LedgerDetailsTemplate] = (
        await db.scalars(
            select(LedgerDetailsTemplate)
            .where(LedgerDetailsTemplate.token_address == token_address)
            .order_by(LedgerDetailsTemplate.id)
        )
    ).all()

    # Request ledger creation
    req_id = str(uuid.uuid4())
    ledger_req = LedgerCreationRequest()
    ledger_req.request_id = req_id
    ledger_req.token_type = _token.type
    ledger_req.token_address = token_address
    ledger_req.status = LedgerCreationStatus.PROCESSING
    db.add(ledger_req)

    # Create ledger input dataset
    for _details_template in _details_template_list:
        await __create_ledger_input_dataset(
            db=db,
            request_id=req_id,
            token_address=token_address,
            token_type=_token.type,
            data_type=_details_template.data_type,
            data_source=_details_template.data_source,
        )


async def sync_request_with_registered_personal_info(
    db: AsyncSession, request_id: str, issuer_address: str
):
    """ "Sync ledger creation request data with registered personal information"""

    # Search for data with unset personal information fields.
    # NOTE: Excluding issuer address
    unset_data_list = (
        await db.scalars(
            select(LedgerCreationRequestData).where(
                and_(
                    LedgerCreationRequestData.request_id == request_id,
                    LedgerCreationRequestData.data_type == LedgerDataType.IBET_FIN,
                    LedgerCreationRequestData.account_address != issuer_address,
                    LedgerCreationRequestData.name == None,
                )
            )
        )
    ).all()

    # Update personal information fields
    initial_unset_count = len(unset_data_list)
    final_set_count = 0
    for unset_data in unset_data_list:
        personal_info = await __get_personal_info(
            db=db,
            account_address=unset_data.account_address,
            issuer_address=issuer_address,
        )
        if personal_info is None:
            continue
        else:
            unset_data.name = personal_info.get("name")
            unset_data.address = personal_info.get("address")
            await db.merge(unset_data)
            final_set_count += 1

    return initial_unset_count, final_set_count


async def finalize_ledger(
    db: AsyncSession,
    request_id: str,
    token_address: str,
    currency_code: str | None = None,
    some_personal_info_not_registered: bool = False,
):
    """Finalize ledger creation"""

    # Get token information
    _token: Token | None = (
        await db.scalars(
            select(Token).where(Token.token_address == token_address).limit(1)
        )
    ).first()
    if _token is None or _token.type not in TokenType:
        return

    # Get ledger template
    _template: LedgerTemplate | None = (
        await db.scalars(
            select(LedgerTemplate)
            .where(LedgerTemplate.token_address == token_address)
            .limit(1)
        )
    ).first()
    if _template is None:
        return

    # Get ledger details
    _details_template_list: Sequence[LedgerDetailsTemplate] = (
        await db.scalars(
            select(LedgerDetailsTemplate)
            .where(LedgerDetailsTemplate.token_address == token_address)
            .order_by(LedgerDetailsTemplate.id)
        )
    ).all()

    ledger_details = []
    for _details_template in _details_template_list:
        _details_data_list: Sequence[LedgerCreationRequestData] = (
            await db.scalars(
                select(LedgerCreationRequestData).where(
                    and_(
                        LedgerCreationRequestData.request_id == request_id,
                        LedgerCreationRequestData.data_type
                        == _details_template.data_type,
                    )
                )
            )
        ).all()
        data_list = [
            {
                "account_address": _details_data.account_address,
                "name": _details_data.name,
                "address": _details_data.address,
                "amount": _details_data.amount,
                "price": _details_data.price,
                "balance": _details_data.balance,
                "acquisition_date": _details_data.acquisition_date,
            }
            for _details_data in _details_data_list
        ]
        details = {
            "token_detail_type": _details_template.token_detail_type,
            "headers": _details_template.headers,
            "data": data_list,
            "footers": _details_template.footers,
            "some_personal_info_not_registered": False
            if _details_template.data_type == LedgerDataType.DB
            else some_personal_info_not_registered,  # Always False for LedgerDataType.DB
        }
        ledger_details.append(details)

    created_ymd = (
        utc_tz.localize(datetime.now(UTC).replace(tzinfo=None))
        .astimezone(local_tz)
        .strftime("%Y/%m/%d")
    )
    # NOTE: Merge with template with ledger GET API
    ledger = {
        "created": created_ymd,
        "token_name": _template.token_name,
        "currency": currency_code,
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
    await db.flush()

    # Delete ledger request data
    await db.execute(
        delete(LedgerCreationRequestData).where(
            LedgerCreationRequestData.request_id == request_id
        )
    )

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
        "ledger_id": _ledger.id,
    }
    db.add(_notification)


async def __create_ledger_input_dataset(
    db: AsyncSession,
    request_id: str,
    token_address: str,
    token_type: str,
    data_type: str,
    data_source: str,
):
    if data_type == LedgerDataType.DB:
        await __create_dataset_from_db(db, request_id, token_address, data_source)
    elif data_type == LedgerDataType.IBET_FIN:
        await __create_dataset_from_ibetfin(db, request_id, token_address, token_type)


async def __create_dataset_from_db(
    db: AsyncSession,
    request_id: str,
    token_address: str,
    data_source: str,
):
    """Create ledger input data from DB(uploaded off-chain data)"""

    _details_data_list: Sequence[LedgerDetailsData] = (
        await db.scalars(
            select(LedgerDetailsData)
            .where(
                and_(
                    LedgerDetailsData.token_address == token_address,
                    LedgerDetailsData.data_id == data_source,
                )
            )
            .order_by(LedgerDetailsData.id)
        )
    ).all()
    for _details_data in _details_data_list:
        ledger_req_data = LedgerCreationRequestData()
        ledger_req_data.request_id = request_id
        ledger_req_data.data_type = LedgerDataType.DB
        ledger_req_data.account_address = ""
        ledger_req_data.acquisition_date = _details_data.acquisition_date
        ledger_req_data.name = _details_data.name
        ledger_req_data.address = _details_data.address
        ledger_req_data.amount = _details_data.amount
        ledger_req_data.price = _details_data.price
        ledger_req_data.balance = _details_data.balance
        db.add(ledger_req_data)


async def __create_dataset_from_ibetfin(
    db: AsyncSession,
    request_id: str,
    token_address: str,
    token_type: str,
):
    """Create ledger input data from ibet for Fin"""

    if token_type == TokenType.IBET_SHARE:
        token_contract = await IbetShareContract(token_address).get()
        price = token_contract.principal_value
    elif token_type == TokenType.IBET_STRAIGHT_BOND:
        token_contract = await IbetStraightBondContract(token_address).get()
        price = token_contract.face_value
    else:
        return

    # Get token holders from UTXO
    _utxo_list: Sequence[UTXO] = (
        await db.scalars(
            select(UTXO)
            .where(
                and_(
                    UTXO.token_address == token_contract.token_address, UTXO.amount > 0
                )
            )
            .order_by(UTXO.account_address, UTXO.block_timestamp)
        )
    ).all()

    # NOTE: UTXO grouping
    #       account_address
    #       - block_timestamp(YYYY/MM/DD)
    #         - sum(amount)
    utxo_grouped = {}
    for _utxo in _utxo_list:
        date_ymd = (
            utc_tz.localize(_utxo.block_timestamp)
            .astimezone(local_tz)
            .strftime("%Y/%m/%d")
        )
        if _utxo.account_address not in utxo_grouped:
            utxo_grouped[_utxo.account_address] = {date_ymd: _utxo.amount}
        else:
            if date_ymd not in utxo_grouped[_utxo.account_address]:
                utxo_grouped[_utxo.account_address][date_ymd] = _utxo.amount
            else:
                utxo_grouped[_utxo.account_address][date_ymd] += _utxo.amount

    for account_address, date_ymd_amount in utxo_grouped.items():
        for date_ymd, amount in date_ymd_amount.items():
            ledger_req_data = LedgerCreationRequestData()
            ledger_req_data.request_id = request_id
            ledger_req_data.data_type = LedgerDataType.IBET_FIN
            ledger_req_data.account_address = account_address
            ledger_req_data.acquisition_date = date_ymd
            ledger_req_data.name = None
            ledger_req_data.address = None
            ledger_req_data.amount = amount
            ledger_req_data.price = price
            ledger_req_data.balance = price * amount
            db.add(ledger_req_data)


async def __get_personal_info(
    db: AsyncSession,
    account_address: str,
    issuer_address: str,
) -> dict | None:
    # Search indexed personal information
    _idx_personal_info: IDXPersonalInfo | None = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == account_address,
                    IDXPersonalInfo.issuer_address == issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if (
        _idx_personal_info is not None
        and any(_idx_personal_info.personal_info.values()) is not False
    ):
        return _idx_personal_info.personal_info
    else:
        return None
