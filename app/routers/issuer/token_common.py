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

import secrets
import uuid
from typing import Annotated, Optional

import pytz
from eth_keyfile import decode_keyfile_json
from fastapi import APIRouter, Header, HTTPException, Path, Query
from sqlalchemy import and_, asc, desc, func, select
from starlette.requests import Request

from app.database import DBAsyncSession
from app.exceptions import InvalidParameterError
from app.model.db import (
    EthIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    ScheduledEvents,
    Token,
    TokenStatus,
    TokenType,
)
from app.model.db.ibet_wst import IbetWSTAuthorization
from app.model.eth import IbetWST, IbetWSTDigestHelper
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.model.schema import (
    AddIbetWSTWhitelistRequest,
    DeleteIbetWSTWhitelistRequest,
    IbetWSTTransactionResponse,
    ListAllIssuedTokensQuery,
    ListAllIssuedTokensResponse,
    ListAllScheduledEventsQuery,
    ListAllScheduledEventsResponse,
    ListAllScheduledEventsSortItem,
)
from app.utils.check_utils import (
    address_is_valid_address,
    check_auth,
    eoa_password_is_encrypted_value,
    validate_headers,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.eth_contract_utils import EthWeb3
from app.utils.fastapi_utils import json_response
from config import IBET_WST_FEATURE_ENABLED, TZ
from eth_config import ETH_MASTER_ACCOUNT_ADDRESS

router = APIRouter(
    prefix="",
    tags=["token_common"],
)

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# GET: /tokens
@router.get(
    "/tokens",
    operation_id="ListAllIssuedTokens",
    response_model=ListAllIssuedTokensResponse,
    responses=get_routers_responses(422),
)
async def list_all_issued_tokens(
    db: DBAsyncSession,
    request_query: Annotated[ListAllIssuedTokensQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all tokens issued from ibet-Prime"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base Query
    if issuer_address is None:
        stmt = select(Token)
    else:
        stmt = select(Token).where(Token.issuer_address == issuer_address)

    if request_query.token_address_list is not None:
        stmt = stmt.where(Token.token_address.in_(request_query.token_address_list))

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Search Filter
    if request_query.token_type is not None:
        stmt = stmt.where(Token.type == request_query.token_type)

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Sort
    sort_attr = getattr(Token, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if request_query.sort_item != "created":
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(Token.created))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    # Execute Query
    issued_tokens = (await db.scalars(stmt)).all()

    # Get Token Attributes
    tokens = []
    for _token in issued_tokens:
        token_attr = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND:
            token_attr = await IbetStraightBondContract(_token.token_address).get()
        elif _token.type == TokenType.IBET_SHARE:
            token_attr = await IbetShareContract(_token.token_address).get()

        _issue_datetime = (
            pytz.timezone("UTC")
            .localize(_token.created)
            .astimezone(local_tz)
            .isoformat()
        )

        tokens.append(
            {
                "issuer_address": _token.issuer_address,
                "token_address": _token.token_address,
                "token_type": _token.type,
                "created": _issue_datetime,
                "token_status": _token.token_status,
                "contract_version": _token.version,
                "token_attributes": token_attr.__dict__,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "tokens": tokens,
    }
    return json_response(resp)


# GET: /tokens/scheduled_events
@router.get(
    "/tokens/scheduled_events",
    operation_id="ListAllScheduledEvents",
    response_model=ListAllScheduledEventsResponse,
)
async def list_all_scheduled_events(
    db: DBAsyncSession,
    request_query: Annotated[ListAllScheduledEventsQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all scheduled token update events"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base Query
    if issuer_address is None:
        stmt = select(ScheduledEvents)
    else:
        stmt = select(ScheduledEvents).where(
            ScheduledEvents.issuer_address == issuer_address
        )

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(ScheduledEvents).order_by(None)
    )

    # Search Filter
    if request_query.token_type is not None:
        stmt = stmt.where(ScheduledEvents.token_type == request_query.token_type)
    if request_query.token_address is not None:
        stmt = stmt.where(ScheduledEvents.token_address == request_query.token_address)
    if request_query.status is not None:
        stmt = stmt.where(ScheduledEvents.status == request_query.status)

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(ScheduledEvents).order_by(None)
    )

    # Sort
    sort_attr = getattr(ScheduledEvents, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if request_query.sort_item != ListAllScheduledEventsSortItem.CREATED:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(ScheduledEvents.created))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    # Execute Query
    rows = (await db.scalars(stmt)).all()

    # Get Token Attributes
    schedule_events = []
    for _event in rows:
        token_attr = None
        if _event.token_type == TokenType.IBET_STRAIGHT_BOND:
            token_attr = await IbetStraightBondContract(_event.token_address).get()
        elif _event.token_type == TokenType.IBET_SHARE:
            token_attr = await IbetShareContract(_event.token_address).get()

        _scheduled_datetime = (
            pytz.timezone("UTC")
            .localize(_event.scheduled_datetime)
            .astimezone(local_tz)
            .isoformat()
        )
        _created = (
            pytz.timezone("UTC")
            .localize(_event.created)
            .astimezone(local_tz)
            .isoformat()
        )

        schedule_events.append(
            {
                "scheduled_event_id": _event.event_id,
                "token_address": _event.token_address,
                "token_type": _event.token_type,
                "scheduled_datetime": _scheduled_datetime,
                "event_type": _event.event_type,
                "status": _event.status,
                "data": _event.data,
                "created": _created,
                "is_soft_deleted": _event.is_soft_deleted,
                "token_attributes": token_attr.__dict__,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "scheduled_events": schedule_events,
    }
    return json_response(resp)


# POST: /tokens/{token_address}/ibet_wst/whitelists/add
@router.post(
    "/tokens/{token_address}/ibet_wst/whitelists/add",
    operation_id="AddIbetWSTWhitelist",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(400, 404, 422),
)
async def add_ibet_wst_whitelist(
    db: DBAsyncSession,
    request: Request,
    data: AddIbetWSTWhitelistRequest,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """
    Add an account to the IbetWST whitelist

    - This endpoint allows an issuer to add an account to the whitelist of an IbetWST contract.
    """

    # Check if IBET_WST feature is enabled
    if IBET_WST_FEATURE_ENABLED is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    # - Check if the eoa_password or auth_token is valid
    _account, decrypt_password = await check_auth(
        request=request,
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

    # Get Token
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != TokenStatus.FAILED,
                    Token.ibet_wst_address.is_not(None),
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    # Generate IbetWST contract instance
    contract = IbetWST(token.ibet_wst_address)

    # Generate nonce
    nonce = secrets.token_bytes(32)

    # Get domain separator
    domain_separator = await contract.domain_separator()

    # Generate digest
    digest = IbetWSTDigestHelper.generate_add_account_whitelist_digest(
        domain_separator=domain_separator,
        account_address=data.account_address,  # Account to be added to whitelist
        nonce=nonce,
    )

    # Sign the digest from the authorizer's private key
    signature = EthWeb3.eth.account.unsafe_sign_hash(digest, private_key)

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = EthIbetWSTTx()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.ADD_WHITELIST
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = token.ibet_wst_address
    wst_tx.tx_params = {"account_address": data.account_address}
    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
    wst_tx.authorizer = issuer_address
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=nonce.hex(),
        v=signature.v,
        r=signature.r.to_bytes(32).hex(),
        s=signature.s.to_bytes(32).hex(),
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /tokens/{token_address}/ibet_wst/whitelists/delete
@router.post(
    "/tokens/{token_address}/ibet_wst/whitelists/delete",
    operation_id="DeleteIbetWSTWhitelist",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(400, 404, 422),
)
async def delete_ibet_wst_whitelist(
    db: DBAsyncSession,
    request: Request,
    data: DeleteIbetWSTWhitelistRequest,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """
    Delete an account from the IbetWST whitelist

    - This endpoint allows an issuer to delete an account from the whitelist of an IbetWST contract.
    """
    # Check if IBET_WST feature is enabled
    if IBET_WST_FEATURE_ENABLED is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    # - Check if the eoa_password or auth_token is valid
    _account, decrypt_password = await check_auth(
        request=request,
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

    # Get Token
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != TokenStatus.FAILED,
                    Token.ibet_wst_address.is_not(None),
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("This token is temporarily unavailable")

    # Generate IbetWST contract instance
    contract = IbetWST(token.ibet_wst_address)

    # Generate nonce
    nonce = secrets.token_bytes(32)

    # Get domain separator
    domain_separator = await contract.domain_separator()

    # Generate digest
    digest = IbetWSTDigestHelper.generate_delete_account_whitelist_digest(
        domain_separator=domain_separator,
        account_address=data.account_address,  # Account to be deleted to whitelist
        nonce=nonce,
    )

    # Sign the digest from the authorizer's private key
    signature = EthWeb3.eth.account.unsafe_sign_hash(digest, private_key)

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = EthIbetWSTTx()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.DELETE_WHITELIST
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = token.ibet_wst_address
    wst_tx.tx_params = {"account_address": data.account_address}
    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
    wst_tx.authorizer = issuer_address
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=nonce.hex(),
        v=signature.v,
        r=signature.r.to_bytes(32).hex(),
        s=signature.s.to_bytes(32).hex(),
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})
