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
from typing import Annotated, Any, Optional, cast

import pytz
from eth_keyfile.keyfile import decode_keyfile_json
from eth_utils.address import to_checksum_address
from fastapi import APIRouter, Header, HTTPException, Path, Query
from sqlalchemy import and_, asc, desc, func, select
from starlette.requests import Request

from app.database import DBAsyncSession
from app.exceptions import InvalidParameterError
from app.model import EthereumAddress
from app.model.db import (
    AvaIbetWSTTx,
    EthIbetWSTTx,
    IbetWSTBlockchain,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    IDXAvaIbetWSTWhitelist,
    IDXEthIbetWSTWhitelist,
    IDXPersonalInfo,
    ScheduledEvents,
    Token,
    TokenStatus,
    TokenType,
)
from app.model.db.ibet_wst import (
    IbetWSTAuthorization,
    IbetWSTTxParamsAddAccountWhiteList,
    IbetWSTTxParamsDeleteAccountWhiteList,
    IbetWSTTxParamsForceBurn,
)
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.model.schema import (
    AddIbetWSTWhitelistRequest,
    DeleteIbetWSTWhitelistRequest,
    ForceBurnIbetWSTRequest,
    GetIbetWSTWhitelistWithPersonalInfoResponse,
    IbetWSTTransactionResponse,
    IbetWSTWhitelistQuery,
    ListAllIssuedTokensQuery,
    ListAllIssuedTokensResponse,
    ListAllScheduledEventsQuery,
    ListAllScheduledEventsResponse,
    ListAllScheduledEventsSortItem,
    RetrieveIbetWSTWhitelistAccountsWithPersonalInfoResponse,
)
from app.model.wst import AvalancheIbetWST, EthereumIbetWST, IbetWSTDigestHelper
from app.utils.ava_contract_utils import AvaWeb3
from app.utils.check_utils import (
    address_is_valid_address,
    check_auth,
    eoa_password_is_encrypted_value,
    validate_headers,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.eth_contract_utils import EthWeb3
from app.utils.fastapi_utils import json_response
from avalanche_config import AVA_MASTER_ACCOUNT_ADDRESS
from config import IBET_WST_AVA_FEATURE_ENABLED, IBET_WST_ETH_FEATURE_ENABLED, TZ
from eth_config import ETH_MASTER_ACCOUNT_ADDRESS

router = APIRouter(
    prefix="",
    tags=["token_common"],
)

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


def _get_wst_address(
    token: Token, blockchain_platform: IbetWSTBlockchain
) -> str | None:
    return token.get_ibet_wst_address(blockchain_platform)


def _get_wst_contract(
    ibet_wst_address: str, blockchain_platform: IbetWSTBlockchain
) -> EthereumIbetWST | AvalancheIbetWST:
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvalancheIbetWST(ibet_wst_address)
    return EthereumIbetWST(ibet_wst_address)


def _get_signer_web3(blockchain_platform: IbetWSTBlockchain):
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvaWeb3
    return EthWeb3


def _get_master_account(blockchain_platform: IbetWSTBlockchain) -> str:
    account = (
        AVA_MASTER_ACCOUNT_ADDRESS
        if blockchain_platform == IbetWSTBlockchain.AVALANCHE
        else ETH_MASTER_ACCOUNT_ADDRESS
    )
    if account is None:
        raise HTTPException(
            status_code=503,
            detail="Master account is not configured for the selected blockchain platform",
        )
    return account


def _get_wst_tx_model(blockchain_platform: IbetWSTBlockchain):
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvaIbetWSTTx
    return EthIbetWSTTx


def _get_wst_whitelist_model(blockchain_platform: IbetWSTBlockchain):
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return IDXAvaIbetWSTWhitelist
    return IDXEthIbetWSTWhitelist


def _is_wst_blockchain_feature_enabled(blockchain_platform: IbetWSTBlockchain) -> bool:
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return IBET_WST_AVA_FEATURE_ENABLED
    return IBET_WST_ETH_FEATURE_ENABLED


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
    sort_item = request_query.sort_item or "created"
    sort_attr = getattr(Token, str(sort_item), Token.created)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if str(sort_item) != "created":
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
    tokens: list[dict[str, Any]] = []
    for _token in issued_tokens:
        token_attr: dict[str, Any] | None = None
        if _token.type == TokenType.IBET_STRAIGHT_BOND:
            token_contract = await IbetStraightBondContract(_token.token_address).get()
            token_attr = dict(token_contract.__dict__)
        elif _token.type == TokenType.IBET_SHARE:
            token_contract = await IbetShareContract(_token.token_address).get()
            token_attr = dict(token_contract.__dict__)

        if _token.created is not None:
            _issue_datetime = (
                pytz.timezone("UTC")
                .localize(_token.created)
                .astimezone(local_tz)
                .isoformat()
            )
        else:
            _issue_datetime = None

        tokens.append(
            {
                "issuer_address": _token.issuer_address,
                "token_address": _token.token_address,
                "token_type": _token.type,
                "created": _issue_datetime,
                "token_status": _token.token_status,
                "contract_version": _token.version,
                "token_attributes": token_attr,
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
    sort_item = request_query.sort_item or ListAllScheduledEventsSortItem.CREATED
    sort_attr = getattr(ScheduledEvents, str(sort_item), ScheduledEvents.created)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if sort_item != ListAllScheduledEventsSortItem.CREATED:
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
    schedule_events: list[dict[str, Any]] = []
    for _event in rows:
        token_attr: dict[str, Any] | None = None
        if _event.token_type == TokenType.IBET_STRAIGHT_BOND:
            token_contract = await IbetStraightBondContract(_event.token_address).get()
            token_attr = dict(token_contract.__dict__)
        elif _event.token_type == TokenType.IBET_SHARE:
            token_contract = await IbetShareContract(_event.token_address).get()
            token_attr = dict(token_contract.__dict__)

        _scheduled_datetime = (
            pytz.timezone("UTC")
            .localize(_event.scheduled_datetime)
            .astimezone(local_tz)
            .isoformat()
        )
        if _event.created is not None:
            _created = (
                pytz.timezone("UTC")
                .localize(_event.created)
                .astimezone(local_tz)
                .isoformat()
            )
        else:
            _created = None

        schedule_events.append(
            {
                "scheduled_event_id": _event.event_id,
                "token_address": _event.token_address,
                "token_type": _event.token_type,
                "scheduled_datetime": _scheduled_datetime,
                "event_type": _event.event_type,
                "status": _event.status,
                "data": cast(dict[str, Any], cast(Any, _event).data),
                "created": _created,
                "is_soft_deleted": _event.is_soft_deleted,
                "token_attributes": token_attr,
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


# GET: /tokens/{token_address}/ibet_wst/whitelists
@router.get(
    "/tokens/{token_address}/ibet_wst/whitelists",
    operation_id="RetrieveIbetWSTWhitelistAccountsWithPersonalInfo",
    response_model=RetrieveIbetWSTWhitelistAccountsWithPersonalInfoResponse,
    responses=get_routers_responses(404, 422),
)
async def retrieve_ibet_wst_whitelist_accounts_with_personal_info(
    db: DBAsyncSession,
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
    issuer_address: Annotated[str, Header(description="Issuer address")],
    request_query: Annotated[IbetWSTWhitelistQuery, Query()],
):
    """
    Retrieve the whitelist accounts of an IbetWST contract with personal information

    - This endpoint retrieves the whitelist accounts of an IbetWST contract along with their personal information.
    """

    blockchain_platform = IbetWSTBlockchain(request_query.blockchain_platform)

    # Check if IBET_WST feature is enabled for selected blockchain platform
    if _is_wst_blockchain_feature_enabled(blockchain_platform) is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == to_checksum_address(issuer_address),
                    Token.token_address == to_checksum_address(token_address),
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    ibet_wst_address = _get_wst_address(
        token, IbetWSTBlockchain(request_query.blockchain_platform)
    )
    if ibet_wst_address is None:
        raise HTTPException(status_code=404, detail="Token not found")

    # Get whitelists
    whitelist_model = _get_wst_whitelist_model(blockchain_platform)
    whitelist_list = cast(
        list[tuple[Any, IDXPersonalInfo | None]],
        (
            await db.execute(
                select(whitelist_model, IDXPersonalInfo)
                .where(whitelist_model.ibet_wst_address == ibet_wst_address)
                .outerjoin(
                    IDXPersonalInfo,
                    and_(
                        IDXPersonalInfo.issuer_address
                        == to_checksum_address(issuer_address),
                        whitelist_model.st_account_address
                        == IDXPersonalInfo.account_address,
                    ),
                )
                .order_by(whitelist_model.created.desc())
            )
        )
        .tuples()
        .all(),
    )

    # Response
    account_list: list[dict[str, Any]] = []
    for item in whitelist_list:
        if item[1] is not None:
            personal_info = item[1].json()
            account_list.append(
                {
                    "st_account_address": item[0].st_account_address,
                    "st_account_personal_info": personal_info.get("personal_info"),
                    "sc_account_address_in": item[0].sc_account_address_in,
                    "sc_account_address_out": item[0].sc_account_address_out,
                }
            )
        else:
            account_list.append(
                {
                    "st_account_address": item[0].st_account_address,
                    "st_account_personal_info": None,
                    "sc_account_address_in": item[0].sc_account_address_in,
                    "sc_account_address_out": item[0].sc_account_address_out,
                }
            )

    return json_response({"whitelist_accounts": account_list})


# GET: /tokens/{token_address}/ibet_wst/whitelists/{account_address}
@router.get(
    "/tokens/{token_address}/ibet_wst/whitelists/{account_address}",
    operation_id="GetIbetWSTWhitelistWithPersonalInfo",
    response_model=GetIbetWSTWhitelistWithPersonalInfoResponse,
    responses=get_routers_responses(),
)
async def get_ibet_wst_whitelist_with_personal_info(
    db: DBAsyncSession,
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
    issuer_address: Annotated[str, Header(description="Issuer address")],
    request_query: Annotated[IbetWSTWhitelistQuery, Query()],
):
    """
    Get IbetWST whitelist status for a specific account with personal information

    - This endpoint retrieves the whitelist status of an account address for the specified IbetWST contract.
    """

    blockchain_platform = IbetWSTBlockchain(request_query.blockchain_platform)

    # Check if IBET_WST feature is enabled for selected blockchain platform
    if _is_wst_blockchain_feature_enabled(blockchain_platform) is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Token
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == to_checksum_address(issuer_address),
                    Token.token_address == to_checksum_address(token_address),
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    ibet_wst_address = _get_wst_address(
        token, IbetWSTBlockchain(request_query.blockchain_platform)
    )
    if ibet_wst_address is None:
        raise HTTPException(status_code=404, detail="Token not found")

    # Get whitelist status
    wst_contract = _get_wst_contract(ibet_wst_address, blockchain_platform)
    whitelist = await wst_contract.account_white_list(
        to_checksum_address(account_address)
    )

    # Get personal information
    personal_info: IDXPersonalInfo | None = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.issuer_address
                    == to_checksum_address(issuer_address),
                    IDXPersonalInfo.account_address
                    == to_checksum_address(account_address),
                )
            )
            .limit(1)
        )
    ).first()

    return json_response(
        {
            "st_account_address": whitelist.st_account,
            "st_account_personal_info": personal_info.personal_info
            if personal_info
            else None,
            "sc_account_address_in": whitelist.sc_account_in,
            "sc_account_address_out": whitelist.sc_account_out,
            "listed": whitelist.listed,
        }
    )


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
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
    issuer_address: Annotated[str, Header(description="Issuer address")],
    eoa_password: Annotated[Optional[str], Header(description="EOA passphrase")] = None,
    auth_token: Annotated[
        Optional[str], Header(description="JWT authentication token")
    ] = None,
):
    """
    Add an account to the IbetWST whitelist

    - This endpoint allows an issuer to add an account to the whitelist of an IbetWST contract.
    """

    blockchain_platform = IbetWSTBlockchain(data.blockchain_platform)

    # Check if IBET_WST feature is enabled for selected blockchain platform
    if _is_wst_blockchain_feature_enabled(blockchain_platform) is False:
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
        issuer_address=to_checksum_address(issuer_address),
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = cast(dict[str, Any] | None, cast(Any, _account).keyfile)
    if keyfile_json is None:
        raise HTTPException(status_code=400, detail="Keyfile not found")
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Get Token
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == to_checksum_address(issuer_address),
                    Token.token_address == to_checksum_address(token_address),
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    ibet_wst_address = _get_wst_address(
        token, IbetWSTBlockchain(data.blockchain_platform)
    )
    if ibet_wst_address is None:
        raise HTTPException(status_code=404, detail="Token not found")

    # Generate IbetWST contract instance
    contract = _get_wst_contract(ibet_wst_address, blockchain_platform)

    # Generate nonce
    nonce = secrets.token_bytes(32)

    # Get domain separator
    domain_separator = await contract.domain_separator()

    # Generate digest
    digest = IbetWSTDigestHelper.generate_add_account_whitelist_digest(
        domain_separator=domain_separator,
        st_account=data.st_account_address,  # ST Account to be added to whitelist
        sc_account_in=data.sc_account_address_in,  # SC Account for deposits
        sc_account_out=data.sc_account_address_out,  # SC Account for withdrawals
        nonce=nonce,
    )

    # Sign the digest from the authorizer's private key
    signature = _get_signer_web3(blockchain_platform).eth.account.unsafe_sign_hash(
        digest, private_key
    )

    # Insert transaction record
    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.ADD_WHITELIST
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsAddAccountWhiteList(
        st_account=data.st_account_address,  # ST Account to be added to whitelist
        sc_account_in=data.sc_account_address_in,  # SC Account for deposits
        sc_account_out=data.sc_account_address_out,  # SC Account for withdrawals
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = to_checksum_address(issuer_address)
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
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
    issuer_address: Annotated[str, Header(description="Issuer address")],
    eoa_password: Annotated[Optional[str], Header(description="EOA passphrase")] = None,
    auth_token: Annotated[
        Optional[str], Header(description="JWT authentication token")
    ] = None,
):
    """
    Delete an account from the IbetWST whitelist

    - This endpoint allows an issuer to delete an account from the whitelist of an IbetWST contract.
    """
    blockchain_platform = IbetWSTBlockchain(data.blockchain_platform)

    # Check if IBET_WST feature is enabled for selected blockchain platform
    if _is_wst_blockchain_feature_enabled(blockchain_platform) is False:
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
        issuer_address=to_checksum_address(issuer_address),
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = cast(dict[str, Any] | None, cast(Any, _account).keyfile)
    if keyfile_json is None:
        raise HTTPException(status_code=400, detail="Keyfile not found")
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Get Token
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == to_checksum_address(issuer_address),
                    Token.token_address == to_checksum_address(token_address),
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    ibet_wst_address = _get_wst_address(
        token, IbetWSTBlockchain(data.blockchain_platform)
    )
    if ibet_wst_address is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("This token is temporarily unavailable")

    # Generate IbetWST contract instance
    contract = _get_wst_contract(ibet_wst_address, blockchain_platform)

    # Generate nonce
    nonce = secrets.token_bytes(32)

    # Get domain separator
    domain_separator = await contract.domain_separator()

    # Generate digest
    digest = IbetWSTDigestHelper.generate_delete_account_whitelist_digest(
        domain_separator=domain_separator,
        st_account=data.st_account_address,  # Account to be deleted to whitelist
        nonce=nonce,
    )

    # Sign the digest from the authorizer's private key
    signature = _get_signer_web3(blockchain_platform).eth.account.unsafe_sign_hash(
        digest, private_key
    )

    # Insert transaction record
    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.DELETE_WHITELIST
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsDeleteAccountWhiteList(
        st_account=data.st_account_address,  # Account to be deleted to whitelist
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = to_checksum_address(issuer_address)
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=nonce.hex(),
        v=signature.v,
        r=signature.r.to_bytes(32).hex(),
        s=signature.s.to_bytes(32).hex(),
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /tokens/{token_address}/ibet_wst/positions/force_burn
@router.post(
    "/tokens/{token_address}/ibet_wst/positions/force_burn",
    operation_id="ForceBurnIbetWSTPosition",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(400, 404, 422),
)
async def force_burn_ibet_wst_position(
    db: DBAsyncSession,
    request: Request,
    data: ForceBurnIbetWSTRequest,
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
    issuer_address: Annotated[str, Header(description="Issuer address")],
    eoa_password: Annotated[Optional[str], Header(description="EOA passphrase")] = None,
    auth_token: Annotated[
        Optional[str], Header(description="JWT authentication token")
    ] = None,
):
    """
    Force burn an IbetWST position for a specific account

    - This endpoint allows an issuer to force burn an IbetWST position for a specific account.
    """

    blockchain_platform = IbetWSTBlockchain(data.blockchain_platform)

    # Check if IBET_WST feature is enabled for selected blockchain platform
    if _is_wst_blockchain_feature_enabled(blockchain_platform) is False:
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
    issuer_account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=to_checksum_address(issuer_address),
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = cast(dict[str, Any] | None, cast(Any, issuer_account).keyfile)
    if keyfile_json is None:
        raise HTTPException(status_code=400, detail="Keyfile not found")
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Get Token
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.issuer_address == to_checksum_address(issuer_address),
                    Token.token_address == to_checksum_address(token_address),
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    ibet_wst_address = _get_wst_address(
        token, IbetWSTBlockchain(data.blockchain_platform)
    )
    if ibet_wst_address is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("This token is temporarily unavailable")

    # Generate IbetWST contract instance
    contract = _get_wst_contract(ibet_wst_address, blockchain_platform)

    # Generate nonce
    nonce = secrets.token_bytes(32)

    # Get domain separator
    domain_separator = await contract.domain_separator()

    # Generate digest
    digest = IbetWSTDigestHelper.generate_force_burn_from_digest(
        domain_separator=domain_separator,
        account_address=data.account_address,  # Account to force burn
        value=data.value,  # Amount to force burn
        nonce=nonce,
    )

    # Sign the digest from the authorizer's private key
    signature = _get_signer_web3(blockchain_platform).eth.account.unsafe_sign_hash(
        digest, private_key
    )

    # Insert transaction record
    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.FORCE_BURN
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsForceBurn(
        account=data.account_address,  # Account to force burn
        value=data.value,  # Amount to force burn
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = to_checksum_address(issuer_address)
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=nonce.hex(),
        v=signature.v,
        r=signature.r.to_bytes(32).hex(),
        s=signature.s.to_bytes(32).hex(),
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})
