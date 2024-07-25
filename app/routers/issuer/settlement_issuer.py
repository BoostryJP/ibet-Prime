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

from datetime import UTC
from typing import Optional, Sequence

import pytz
from eth_keyfile import decode_keyfile_json
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import aliased

import config
from app.database import DBAsyncSession
from app.exceptions import InvalidParameterError, SendTransactionError
from app.model.blockchain.exchange import IbetSecurityTokenDVP
from app.model.blockchain.tx_params.ibet_security_token_dvp import (
    CancelDeliveryParams,
    CreateDeliveryParams,
)
from app.model.db import IDXDelivery, IDXPersonalInfo, Token
from app.model.schema import (
    CancelDVPDeliveryRequest,
    CreateDVPDeliveryRequest,
    CreateDVPDeliveryResponse,
    ListAllDVPDeliveriesQuery,
    ListAllDVPDeliveriesResponse,
    RetrieveDVPDeliveryResponse,
)
from app.utils.check_utils import (
    address_is_valid_address,
    check_auth,
    eoa_password_is_encrypted_value,
    validate_headers,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

router = APIRouter(prefix="/settlement", tags=["settlement"])

local_tz = pytz.timezone(config.TZ)


# GET: /settlement/dvp/{exchange_address}/deliveries
@router.get(
    "/dvp/{exchange_address}/deliveries",
    operation_id="ListAllDVPDeliveries",
    response_model=ListAllDVPDeliveriesResponse,
    responses=get_routers_responses(404, 422, InvalidParameterError),
)
async def list_all_dvp_deliveries(
    db: DBAsyncSession,
    exchange_address: str,
    request_query: ListAllDVPDeliveriesQuery = Depends(),
    issuer_address: str = Header(...),
):
    """List all DVP deliveries"""
    buyer_personal_info = aliased(IDXPersonalInfo)
    seller_personal_info = aliased(IDXPersonalInfo)

    stmt = (
        select(IDXDelivery, buyer_personal_info, seller_personal_info)
        .join(Token, Token.token_address == IDXDelivery.token_address)
        .outerjoin(
            buyer_personal_info,
            and_(
                Token.issuer_address == buyer_personal_info.issuer_address,
                IDXDelivery.buyer_address == buyer_personal_info.account_address,
            ),
        )
        .outerjoin(
            seller_personal_info,
            and_(
                Token.issuer_address == seller_personal_info.issuer_address,
                IDXDelivery.seller_address == seller_personal_info.account_address,
            ),
        )
        .where(
            and_(
                IDXDelivery.exchange_address == exchange_address,
                Token.issuer_address == issuer_address,
            )
        )
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.token_address is not None:
        stmt = stmt.where(IDXDelivery.token_address == request_query.token_address)
    if request_query.seller_address is not None:
        stmt = stmt.where(IDXDelivery.seller_address == request_query.seller_address)
    if request_query.agent_address is not None:
        stmt = stmt.where(IDXDelivery.agent_address == request_query.agent_address)
    if request_query.valid is not None:
        stmt = stmt.where(IDXDelivery.valid == request_query.valid)
    if request_query.status is not None:
        stmt = stmt.where(IDXDelivery.status == request_query.status)
    if request_query.create_blocktimestamp_from is not None:
        stmt = stmt.where(
            IDXDelivery.create_blocktimestamp
            >= local_tz.localize(request_query.create_blocktimestamp_from).astimezone(
                tz=UTC
            )
        )
    if request_query.create_blocktimestamp_to is not None:
        stmt = stmt.where(
            IDXDelivery.create_blocktimestamp
            <= local_tz.localize(request_query.create_blocktimestamp_to).astimezone(
                tz=UTC
            )
        )

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(IDXDelivery.create_blocktimestamp)
    else:  # DESC
        stmt = stmt.order_by(desc(IDXDelivery.create_blocktimestamp))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    _deliveries: Sequence[
        tuple[IDXDelivery, IDXPersonalInfo | None, IDXPersonalInfo | None]
    ] = ((await db.execute(stmt)).tuples().all())

    deliveries = []
    for _delivery, _buyer_info, _seller_info in _deliveries:
        if _delivery.create_blocktimestamp is not None:
            create_blocktimestamp = (
                local_tz.localize(_delivery.create_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            create_blocktimestamp = None
        if _delivery.cancel_blocktimestamp is not None:
            cancel_blocktimestamp = (
                local_tz.localize(_delivery.cancel_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            cancel_blocktimestamp = None
        if _delivery.confirm_blocktimestamp is not None:
            confirm_blocktimestamp = (
                local_tz.localize(_delivery.confirm_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            confirm_blocktimestamp = None
        if _delivery.finish_blocktimestamp is not None:
            finish_blocktimestamp = (
                local_tz.localize(_delivery.finish_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            finish_blocktimestamp = None
        if _delivery.abort_blocktimestamp is not None:
            abort_blocktimestamp = (
                local_tz.localize(_delivery.abort_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            abort_blocktimestamp = None

        deliveries.append(
            {
                "exchange_address": _delivery.exchange_address,
                "delivery_id": _delivery.delivery_id,
                "token_address": _delivery.token_address,
                "buyer_address": _delivery.buyer_address,
                "buyer_personal_information": (
                    _buyer_info.personal_info if _buyer_info is not None else None
                ),
                "seller_address": _delivery.seller_address,
                "seller_personal_information": (
                    _seller_info.personal_info if _seller_info is not None else None
                ),
                "amount": _delivery.amount,
                "agent_address": _delivery.agent_address,
                "data": _delivery.data,
                "create_blocktimestamp": create_blocktimestamp,
                "create_transaction_hash": _delivery.create_transaction_hash,
                "cancel_blocktimestamp": cancel_blocktimestamp,
                "cancel_transaction_hash": _delivery.cancel_transaction_hash,
                "confirm_blocktimestamp": confirm_blocktimestamp,
                "confirm_transaction_hash": _delivery.confirm_transaction_hash,
                "finish_blocktimestamp": finish_blocktimestamp,
                "finish_transaction_hash": _delivery.finish_transaction_hash,
                "abort_blocktimestamp": abort_blocktimestamp,
                "abort_transaction_hash": _delivery.abort_transaction_hash,
                "confirmed": _delivery.confirmed,
                "valid": _delivery.valid,
                "status": _delivery.status,
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": request_query.offset,
                "limit": request_query.limit,
                "total": total,
            },
            "deliveries": deliveries,
        }
    )


# POST: /settlement/dvp/{exchange_address}/deliveries
@router.post(
    "/dvp/{exchange_address}/deliveries",
    operation_id="CreateDVPDelivery",
    response_model=CreateDVPDeliveryResponse,
    responses=get_routers_responses(
        404, 422, InvalidParameterError, SendTransactionError
    ),
)
async def create_dvp_delivery(
    db: DBAsyncSession,
    req: Request,
    exchange_address: str,
    data: CreateDVPDeliveryRequest,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = await check_auth(
        request=req,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Create delivery
    dvp_contract = IbetSecurityTokenDVP(contract_address=exchange_address)
    try:
        _data = {
            "token_address": data.token_address,
            "buyer_address": data.buyer_address,
            "amount": data.amount,
            "agent_address": data.agent_address,
            "data": data.data,
        }
        (_, _, delivery_id) = await dvp_contract.create_delivery(
            data=CreateDeliveryParams(**_data),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to create delivery")

    return json_response(
        {
            "delivery_id": delivery_id,
        }
    )


# GET: /settlement/dvp/{exchange_address}/delivery/{delivery_id}
@router.get(
    "/dvp/{exchange_address}/delivery/{delivery_id}",
    operation_id="RetrieveDVPDelivery",
    response_model=RetrieveDVPDeliveryResponse,
    responses=get_routers_responses(404, 422, InvalidParameterError),
)
async def retrieve_dvp_delivery(
    db: DBAsyncSession,
    exchange_address: str = Path(..., description="Exchange Address"),
    delivery_id: int = Path(..., description="Delivery Id"),
    issuer_address: str = Header(...),
):
    """Retrieve a dvp delivery"""
    buyer_personal_info = aliased(IDXPersonalInfo)
    seller_personal_info = aliased(IDXPersonalInfo)

    _delivery: (
        tuple[IDXDelivery, IDXPersonalInfo | None, IDXPersonalInfo | None] | None
    ) = (
        (
            await db.execute(
                select(IDXDelivery, buyer_personal_info, seller_personal_info)
                .join(Token, Token.token_address == IDXDelivery.token_address)
                .outerjoin(
                    buyer_personal_info,
                    and_(
                        Token.issuer_address == buyer_personal_info.issuer_address,
                        IDXDelivery.buyer_address
                        == buyer_personal_info.account_address,
                    ),
                )
                .outerjoin(
                    seller_personal_info,
                    and_(
                        Token.issuer_address == seller_personal_info.issuer_address,
                        IDXDelivery.seller_address
                        == seller_personal_info.account_address,
                    ),
                )
                .where(
                    and_(
                        IDXDelivery.exchange_address == exchange_address,
                        IDXDelivery.delivery_id == delivery_id,
                        Token.issuer_address == issuer_address,
                    )
                )
                .limit(1)
            )
        )
        .tuples()
        .first()
    )
    if _delivery is None:
        raise HTTPException(status_code=404, detail="delivery not found")

    if _delivery[0].create_blocktimestamp is not None:
        create_blocktimestamp = (
            local_tz.localize(_delivery[0].create_blocktimestamp)
            .astimezone(tz=UTC)
            .isoformat()
        )
    else:
        create_blocktimestamp = None
    if _delivery[0].cancel_blocktimestamp is not None:
        cancel_blocktimestamp = (
            local_tz.localize(_delivery[0].cancel_blocktimestamp)
            .astimezone(tz=UTC)
            .isoformat()
        )
    else:
        cancel_blocktimestamp = None
    if _delivery[0].confirm_blocktimestamp is not None:
        confirm_blocktimestamp = (
            local_tz.localize(_delivery[0].confirm_blocktimestamp)
            .astimezone(tz=UTC)
            .isoformat()
        )
    else:
        confirm_blocktimestamp = None
    if _delivery[0].finish_blocktimestamp is not None:
        finish_blocktimestamp = (
            local_tz.localize(_delivery[0].finish_blocktimestamp)
            .astimezone(tz=UTC)
            .isoformat()
        )
    else:
        finish_blocktimestamp = None
    if _delivery[0].abort_blocktimestamp is not None:
        abort_blocktimestamp = (
            local_tz.localize(_delivery[0].abort_blocktimestamp)
            .astimezone(tz=UTC)
            .isoformat()
        )
    else:
        abort_blocktimestamp = None

    return json_response(
        {
            "exchange_address": _delivery[0].exchange_address,
            "delivery_id": _delivery[0].delivery_id,
            "token_address": _delivery[0].token_address,
            "buyer_address": _delivery[0].buyer_address,
            "buyer_personal_information": (
                _delivery[1].personal_info if _delivery[1] is not None else None
            ),
            "seller_address": _delivery[0].seller_address,
            "seller_personal_information": (
                _delivery[2].personal_info if _delivery[2] is not None else None
            ),
            "amount": _delivery[0].amount,
            "agent_address": _delivery[0].agent_address,
            "data": _delivery[0].data,
            "create_blocktimestamp": create_blocktimestamp,
            "create_transaction_hash": _delivery[0].create_transaction_hash,
            "cancel_blocktimestamp": cancel_blocktimestamp,
            "cancel_transaction_hash": _delivery[0].cancel_transaction_hash,
            "confirm_blocktimestamp": confirm_blocktimestamp,
            "confirm_transaction_hash": _delivery[0].confirm_transaction_hash,
            "finish_blocktimestamp": finish_blocktimestamp,
            "finish_transaction_hash": _delivery[0].finish_transaction_hash,
            "abort_blocktimestamp": abort_blocktimestamp,
            "abort_transaction_hash": _delivery[0].abort_transaction_hash,
            "confirmed": _delivery[0].confirmed,
            "valid": _delivery[0].valid,
            "status": _delivery[0].status,
        }
    )


# POST: /settlement/dvp/{exchange_address}/delivery/{delivery_id}
@router.post(
    "/dvp/{exchange_address}/delivery/{delivery_id}",
    operation_id="UpdateDVPDelivery",
    response_model=None,
    responses=get_routers_responses(
        404, 422, InvalidParameterError, SendTransactionError
    ),
)
async def update_dvp_delivery(
    db: DBAsyncSession,
    req: Request,
    exchange_address: str,
    delivery_id: str,
    data: CancelDVPDeliveryRequest,
    issuer_address: str = Header(None),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    match data.operation_type:
        case "Cancel":
            # Validate Headers
            validate_headers(
                issuer_address=(issuer_address, address_is_valid_address),
                eoa_password=(eoa_password, eoa_password_is_encrypted_value),
            )

            # Authentication
            _account, decrypt_password = await check_auth(
                request=req,
                db=db,
                issuer_address=issuer_address,
                eoa_password=eoa_password,
                auth_token=auth_token,
            )

            # Get private key
            keyfile_json = _account.keyfile
            private_key = decode_keyfile_json(
                raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
            )

            # Cancel delivery
            dvp_contract = IbetSecurityTokenDVP(contract_address=exchange_address)
            try:
                _data = {"delivery_id": delivery_id}
                await dvp_contract.cancel_delivery(
                    data=CancelDeliveryParams(**_data),
                    tx_from=issuer_address,
                    private_key=private_key,
                )
            except SendTransactionError:
                raise SendTransactionError("failed to cancel delivery")
            return
