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
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.blockchain import (
    ContractPersonalInfoType,
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract,
)
from app.model.db import (
    UTXO,
    Account,
    IDXPersonalInfo,
    Ledger,
    LedgerDetailsData,
    LedgerDetailsDataType,
    LedgerDetailsTemplate,
    LedgerTemplate,
    Notification,
    NotificationType,
    Token,
    TokenType,
)
from config import TZ

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


async def create_ledger(token_address: str, db: AsyncSession):
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(and_(Token.token_address == token_address, Token.token_status == 1))
            .limit(1)
        )
    ).first()
    if (
        _token.type != TokenType.IBET_SHARE.value
        and _token.type != TokenType.IBET_STRAIGHT_BOND.value
    ):
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

    # Get currency code only for BOND tokens
    currency = ""  # default
    if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
        bond_contract = await IbetStraightBondContract(token_address).get()
        currency = bond_contract.face_value_currency

    # Get ledger details
    _details_list: Sequence[LedgerDetailsTemplate] = (
        await db.scalars(
            select(LedgerDetailsTemplate)
            .where(LedgerDetailsTemplate.token_address == token_address)
            .order_by(LedgerDetailsTemplate.id)
        )
    ).all()
    ledger_details = []

    for _details in _details_list:
        # Get ledger details data
        data_list, some_personal_info_not_registered = await __get_details_data_list(
            token_address, _token.type, _details.data_type, _details.data_source, db
        )
        details = {
            "token_detail_type": _details.token_detail_type,
            "headers": _details.headers,
            "data": data_list,
            "footers": _details.footers,
            "some_personal_info_not_registered": some_personal_info_not_registered,
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
        "currency": currency,
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


async def __get_details_data_list(
    token_address: str,
    token_type: str,
    data_type: str,
    data_source: str,
    db: AsyncSession,
) -> tuple[list[dict], bool]:
    data_list = []
    some_personal_info_not_registered = False
    if data_type == LedgerDetailsDataType.DB.value:
        data_list = []
        # Get Ledger Details Data from DB
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
            data_list.append(
                {
                    "account_address": None,
                    "name": _details_data.name,
                    "address": _details_data.address,
                    "amount": _details_data.amount,
                    "price": _details_data.price,
                    "balance": _details_data.balance,
                    "acquisition_date": _details_data.acquisition_date,
                }
            )
    elif data_type == LedgerDetailsDataType.IBET_FIN.value:
        # NOTE:
        # If there is an account with no personal information registered,
        # some_personal_info_not_registered will be True.
        data_list, some_personal_info_not_registered = (
            await __get_details_data_list_from_ibetfin(token_address, token_type, db)
        )

    return data_list, some_personal_info_not_registered


async def __get_details_data_list_from_ibetfin(
    token_address: str, token_type: str, db: AsyncSession
) -> tuple[list[dict], bool]:
    if token_type == TokenType.IBET_SHARE.value:
        token_contract = await IbetShareContract(token_address).get()
        price = token_contract.principal_value
    elif token_type == TokenType.IBET_STRAIGHT_BOND.value:
        token_contract = await IbetStraightBondContract(token_address).get()
        price = token_contract.face_value

    issuer_account = (
        await db.scalars(
            select(Account)
            .where(Account.issuer_address == token_contract.issuer_address)
            .limit(1)
        )
    ).first()
    personal_info_contract = PersonalInfoContract(
        issuer=issuer_account,
        contract_address=token_contract.personal_info_contract_address,
    )

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

    data_list = []
    some_personal_info_not_registered = False
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
            personal_info, _pi_not_registered = await __get_personal_info(
                account_address,
                token_contract,
                personal_info_contract,
                db,
            )
            details_data["name"] = personal_info.get("name", None)
            details_data["address"] = personal_info.get("address", None)

            data_list.append(details_data)
            if _pi_not_registered:
                some_personal_info_not_registered = True

    return data_list, some_personal_info_not_registered


async def __get_personal_info(
    account_address: str,
    token_contract: IbetShareContract | IbetStraightBondContract,
    personal_info_contract: PersonalInfoContract,
    db: AsyncSession,
) -> tuple[dict, bool]:
    # NOTE:
    # For tokens with require_personal_info_registered = False, search only indexed data.
    # If indexed data does not exist, return the default value.

    # Search indexed data
    _idx_personal_info: IDXPersonalInfo | None = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == account_address,
                    IDXPersonalInfo.issuer_address == token_contract.issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _idx_personal_info is not None:
        # Get personal info from DB
        personal_info_not_registered = False
        return _idx_personal_info.personal_info, personal_info_not_registered

    # Retrieve personal info
    if token_contract.require_personal_info_registered is True:
        # Retrieve from contract storage
        personal_info = await personal_info_contract.get_info(
            account_address, default_value=None
        )
        personal_info_not_registered = False
    else:
        # Do not retrieve contract data and return the default value
        personal_info = ContractPersonalInfoType().model_dump()
        personal_info_not_registered = True

    return personal_info, personal_info_not_registered
