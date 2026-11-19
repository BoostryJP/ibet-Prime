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
from typing import Annotated, Any

import pytz
from eth_utils.address import to_checksum_address
from fastapi import APIRouter, HTTPException, Path, Query, Request
from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.orm import defer

import config
from app.database import DBAsyncSession
from app.exceptions import (
    ERC20InsufficientAllowanceError,
    IbetWSTAccountNotWhitelistedError,
    IbetWSTInsufficientBalanceError,
)
from app.model import EthereumAddress
from app.model.db import (
    AvaIbetWSTTx,
    EthIbetWSTTx,
    IbetWSTAuthorization,
    IbetWSTTxParamsAcceptTrade,
    IbetWSTTxParamsBurn,
    IbetWSTTxParamsCancelTrade,
    IbetWSTTxParamsRejectTrade,
    IbetWSTTxParamsRequestTrade,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    IDXAvaIbetWSTTrade,
    IDXAvaIbetWSTWhitelist,
    IDXEthIbetWSTTrade,
    IDXEthIbetWSTWhitelist,
    Token,
    TokenType,
)
from app.model.db.ibet_wst import IbetWSTTxParamsTransfer
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.model.schema import (
    AcceptIbetWSTTradeRequest,
    BurnIbetWSTRequest,
    CancelIbetWSTTradeRequest,
    GetERC20AllowanceQuery,
    GetERC20AllowanceResponse,
    GetERC20BalanceQuery,
    GetERC20BalanceResponse,
    GetIbetWSTBalanceQuery,
    GetIbetWSTBalanceResponse,
    GetIbetWSTTradeQuery,
    GetIbetWSTTradeResponse,
    GetIbetWSTTransactionQuery,
    GetIbetWSTTransactionResponse,
    GetIbetWSTWhitelistQuery,
    GetIbetWSTWhitelistResponse,
    IbetWSTTransactionResponse,
    ListAllIbetWSTTokensQuery,
    ListAllIbetWSTTokensResponse,
    ListAllIbetWSTTokensSortItem,
    ListIbetWSTTradesQuery,
    ListIbetWSTTradesResponse,
    ListIbetWSTTransactionsQuery,
    ListIbetWSTTransactionsResponse,
    RejectIbetWSTTradeRequest,
    RequestIbetWSTTradeRequest,
    RetrieveIbetWSTWhitelistAccountsQuery,
    RetrieveIbetWSTWhitelistAccountsResponse,
    TransferIbetWSTRequest,
)
from app.model.schema.base import IbetWSTBlockchain
from app.model.wst import (
    AvalancheERC20,
    AvalancheIbetWST,
    EthereumERC20,
    EthereumIbetWST,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from avalanche_config import AVA_MASTER_ACCOUNT_ADDRESS
from eth_config import ETH_MASTER_ACCOUNT_ADDRESS

router = APIRouter(prefix="/ibet_wst", tags=["[misc] ibet_wst"])
local_tz = pytz.timezone(config.TZ)
utc_tz = pytz.timezone("UTC")


def _get_wst_address(
    token: Token, blockchain_platform: IbetWSTBlockchain
) -> str | None:
    return token.get_ibet_wst_address(blockchain_platform)


async def _find_wst_token_by_address(
    db: DBAsyncSession,
    ibet_wst_address: str,
    blockchain_platform: IbetWSTBlockchain,
) -> Token | None:
    target_address = to_checksum_address(ibet_wst_address)
    tokens = (await db.scalars(select(Token).options(defer(Token.abi)))).all()
    for token in tokens:
        if _get_wst_address(token, blockchain_platform) == target_address:
            return token
    return None


def _get_wst_contract(
    ibet_wst_address: str, blockchain_platform: IbetWSTBlockchain
) -> EthereumIbetWST | AvalancheIbetWST:
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvalancheIbetWST(to_checksum_address(ibet_wst_address))
    return EthereumIbetWST(to_checksum_address(ibet_wst_address))


def _get_erc20_contract(
    token_address: str, blockchain_platform: IbetWSTBlockchain
) -> EthereumERC20 | AvalancheERC20:
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvalancheERC20(token_address)
    return EthereumERC20(token_address)


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


def _get_wst_trade_model(blockchain_platform: IbetWSTBlockchain):
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return IDXAvaIbetWSTTrade
    return IDXEthIbetWSTTrade


# GET: /ibet_wst/tokens
@router.get(
    "/tokens",
    operation_id="ListAllIbetWSTTokens",
    response_model=ListAllIbetWSTTokensResponse,
    responses=get_routers_responses(422),
)
async def list_all_ibet_wst_tokens(
    db: DBAsyncSession,
    get_query: Annotated[ListAllIbetWSTTokensQuery, Query()],
):
    """List deployed IbetWST tokens with filtering and pagination.

    Only tokens whose deployment is finalized for the selected blockchain platform are returned.
    Results can be filtered by issuer, WST address, underlying ibet token, and token type, then sorted deterministically.

    These routes are included only when `IBET_WST_FEATURE_ENABLED` is enabled.
    `blockchain_platform` selects the platform-specific deployment and defaults to Ethereum.

    Errors:
    - 422: a query parameter or platform value is invalid.
    """

    blockchain_platform = IbetWSTBlockchain(get_query.blockchain_platform)

    # Load tokens and filter on application side to avoid direct dependency
    # on deprecated single-chain IbetWST columns.
    issued_tokens: list[Token] = []
    all_tokens = (
        await db.scalars(
            select(Token)
            .options(defer(Token.abi))
            .where(Token.ibet_wst_name.is_not(None))
        )
    ).all()
    for token in all_tokens:
        wst_address = _get_wst_address(token, blockchain_platform)
        if not token.is_ibet_wst_deployed(blockchain_platform):
            continue
        if wst_address is None:
            continue
        if (
            get_query.issuer_address is not None
            and token.issuer_address != get_query.issuer_address
        ):
            continue
        if (
            get_query.ibet_wst_address is not None
            and wst_address != get_query.ibet_wst_address
        ):
            continue
        if (
            get_query.ibet_token_address is not None
            and token.token_address != get_query.ibet_token_address
        ):
            continue
        if get_query.token_type is not None and token.type != get_query.token_type:
            continue
        issued_tokens.append(token)

    total = len(
        [
            token
            for token in all_tokens
            if token.is_ibet_wst_deployed(blockchain_platform)
            and _get_wst_address(token, blockchain_platform) is not None
            and (
                get_query.issuer_address is None
                or token.issuer_address == get_query.issuer_address
            )
        ]
    )
    count = len(issued_tokens)

    reverse_sort = get_query.sort_order != 0
    if get_query.sort_item == ListAllIbetWSTTokensSortItem.TOKEN_ADDRESS:
        # Keep secondary sort consistent with previous SQL behavior.
        issued_tokens.sort(
            key=lambda token: (token.created, token.token_address),
            reverse=True,
        )
        issued_tokens.sort(
            key=lambda token: token.token_address,
            reverse=reverse_sort,
        )
    else:
        # Add a deterministic tie-breaker for stable pagination.
        issued_tokens.sort(
            key=lambda token: (token.created, token.token_address),
            reverse=reverse_sort,
        )

    offset = get_query.offset or 0
    if get_query.limit is not None:
        issued_tokens = issued_tokens[offset : offset + get_query.limit]
    else:
        issued_tokens = issued_tokens[offset:]

    # Get Token Attributes
    tokens: list[dict[str, Any]] = []
    for _token in issued_tokens:
        if _token.created is None:
            continue

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
                "ibet_wst_address": _get_wst_address(_token, blockchain_platform),
                "ibet_wst_name": _token.ibet_wst_name,
                "ibet_token_address": _token.token_address,
                "ibet_token_type": _token.type,
                "ibet_token_attributes": token_attr.__dict__,
                "created": _issue_datetime,
            }
        )

    # Response
    resp = {
        "result_set": {
            "count": count,
            "offset": get_query.offset,
            "limit": get_query.limit,
            "total": total,
        },
        "tokens": tokens,
    }
    return json_response(resp)


# GET: /ibet_wst/balances/{account_address}/{ibet_wst_address}
@router.get(
    "/balances/{account_address}/{ibet_wst_address}",
    operation_id="GetIbetWSTBalance",
    response_model=GetIbetWSTBalanceResponse,
    responses=get_routers_responses(404, 422),
)
async def get_ibet_wst_balance(
    db: DBAsyncSession,
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    query: Annotated[GetIbetWSTBalanceQuery, Query()],
):
    """Get an account's IbetWST balance from the selected contract.

    The WST address must be registered for the selected platform.
    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, query parameter, or platform value is invalid.
    """
    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(
        db,
        ibet_wst_address,
        blockchain_platform,
    )
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    # Get balance amount
    wst_contract = _get_wst_contract(ibet_wst_address, blockchain_platform)
    balance = await wst_contract.balance_of(to_checksum_address(account_address))
    return json_response({"balance": balance})


# POST: /ibet_wst/balances/{account_address}/{ibet_wst_address}/burn
@router.post(
    "/balances/{account_address}/{ibet_wst_address}/burn",
    operation_id="BurnIbetWSTBalance",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(IbetWSTInsufficientBalanceError, 404, 422, 503),
)
async def burn_ibet_wst_balance(
    request: Request,
    db: DBAsyncSession,
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: BurnIbetWSTRequest,
):
    """Queue an authorized IbetWST burn transaction.

    The account must have enough IbetWST balance for the requested burn.
    Track the queued transaction with the returned `tx_id` through the transaction endpoints.

    The WST address, selected-platform master account, authorizer, and authorization signature fields must be configured or supplied.
    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 400 `IbetWSTInsufficientBalanceError` (code 13): the account balance is below the requested burn value.
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, request field, or platform value is invalid.
    - 503: the selected platform's master account is not configured.
    """
    blockchain_platform = IbetWSTBlockchain(req_params.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(db, ibet_wst_address, blockchain_platform)
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    # Pre-transaction check: Ensure ST token balance is sufficient
    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    wst_contract = _get_wst_contract(ibet_wst_address, blockchain_platform)
    wst_balance = await wst_contract.balance_of(to_checksum_address(account_address))
    if wst_balance < req_params.value:
        raise IbetWSTInsufficientBalanceError

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.BURN
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsBurn(
        from_address=to_checksum_address(account_address),
        value=req_params.value,
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    wst_tx.client_ip = get_client_ip(request)
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# GET: /ibet_wst/transactions
@router.get(
    "/transactions",
    operation_id="ListIbetWSTTransactions",
    response_model=ListIbetWSTTransactionsResponse,
    responses=get_routers_responses(422),
)
async def list_ibet_wst_transactions(
    db: DBAsyncSession,
    get_query: Annotated[ListIbetWSTTransactionsQuery, Query()],
):
    """List queued and processed IbetWST transactions with filtering and pagination.

    Results are filtered by WST address and optional transaction fields, and ordered by creation time descending.
    Creation timestamps are returned as ISO 8601 values with timezone offsets.
    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 422: a query parameter, date, or platform value is invalid.
    """

    blockchain_platform = IbetWSTBlockchain(get_query.blockchain_platform)

    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    # Base Query
    stmt = select(wst_tx_model).where(
        wst_tx_model.ibet_wst_address == get_query.ibet_wst_address
    )
    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(wst_tx_model).order_by(None)
    )

    # Search Filter
    if get_query.tx_id is not None:
        stmt = stmt.where(wst_tx_model.tx_id == get_query.tx_id)
    if get_query.tx_type is not None:
        stmt = stmt.where(wst_tx_model.tx_type == get_query.tx_type)
    if get_query.status is not None:
        stmt = stmt.where(wst_tx_model.status == int(get_query.status))
    if get_query.tx_hash is not None:
        stmt = stmt.where(wst_tx_model.tx_hash == get_query.tx_hash)
    if get_query.authorizer is not None:
        stmt = stmt.where(wst_tx_model.authorizer == get_query.authorizer)
    if get_query.finalized is not None:
        stmt = stmt.where(wst_tx_model.finalized == get_query.finalized)
    if get_query.created_from:
        _created_from = datetime.strptime(
            get_query.created_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            wst_tx_model.created
            >= local_tz.localize(_created_from).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.created_to:
        _created_to = datetime.strptime(
            get_query.created_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            wst_tx_model.created
            <= local_tz.localize(_created_to).astimezone(utc_tz).replace(tzinfo=None)
        )

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(wst_tx_model).order_by(None)
    )

    # Sort
    stmt = stmt.order_by(desc(wst_tx_model.created))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    # Execute Query
    wst_txs = (await db.scalars(stmt)).all()

    # Response
    tx_list: list[dict[str, Any]] = []
    for wst_tx in wst_txs:
        if wst_tx.created is None:
            continue

        # Set event_log
        event_log = _build_event_log_for_response(wst_tx)

        # Set created datetime
        _created_datetime = (
            pytz.timezone("UTC")
            .localize(wst_tx.created)
            .astimezone(local_tz)
            .isoformat()
        )

        # Append transaction details
        tx_list.append(
            {
                "tx_id": wst_tx.tx_id,
                "tx_type": wst_tx.tx_type,
                "version": wst_tx.version,
                "status": wst_tx.status,
                "ibet_wst_address": wst_tx.ibet_wst_address,
                "tx_sender": wst_tx.tx_sender,
                "authorizer": wst_tx.authorizer,
                "tx_hash": wst_tx.tx_hash,
                "block_number": wst_tx.block_number,
                "finalized": wst_tx.finalized,
                "event_log": event_log,
                "created": _created_datetime,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": get_query.offset,
            "limit": get_query.limit,
            "total": total,
        },
        "transactions": tx_list,
    }
    return json_response(resp)


# GET: /ibet_wst/transactions/{tx_id}
@router.get(
    "/transactions/{tx_id}",
    operation_id="GetIbetWSTTransaction",
    response_model=GetIbetWSTTransactionResponse,
    responses=get_routers_responses(404, 422),
)
async def get_ibet_wst_transaction(
    db: DBAsyncSession,
    tx_id: Annotated[str, Path(description="IbetWST transaction ID")],
    query: Annotated[GetIbetWSTTransactionQuery, Query()],
):
    """Retrieve one IbetWST transaction from the selected platform.

    The response includes its processing status, blockchain identifiers, authorization event log, and timestamps.
    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 404: no transaction exists for `tx_id` on the selected platform.
    - 422: a path, query parameter, or platform value is invalid.
    """
    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    # Get Transaction
    wst_tx = (
        await db.scalars(
            select(wst_tx_model).where(wst_tx_model.tx_id == tx_id).limit(1)
        )
    ).first()
    if wst_tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Set event_log
    event_log = _build_event_log_for_response(wst_tx)

    # Set created datetime
    assert wst_tx.created is not None
    _created_datetime = (
        pytz.timezone("UTC").localize(wst_tx.created).astimezone(local_tz).isoformat()
    )

    # Response
    resp = {
        "tx_id": wst_tx.tx_id,
        "tx_type": wst_tx.tx_type,
        "version": wst_tx.version,
        "status": wst_tx.status,
        "ibet_wst_address": wst_tx.ibet_wst_address,
        "tx_sender": wst_tx.tx_sender,
        "authorizer": wst_tx.authorizer,
        "tx_hash": wst_tx.tx_hash,
        "block_number": wst_tx.block_number,
        "finalized": wst_tx.finalized,
        "event_log": event_log,
        "created": _created_datetime,
    }

    return json_response(resp)


# GET: /ibet_wst/whitelists/{ibet_wst_address}
@router.get(
    "/whitelists/{ibet_wst_address}",
    operation_id="RetrieveIbetWSTWhitelistAccounts",
    response_model=RetrieveIbetWSTWhitelistAccountsResponse,
    responses=get_routers_responses(422),
)
async def retrieve_ibet_wst_whitelist_accounts(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    query: Annotated[RetrieveIbetWSTWhitelistAccountsQuery, Query()],
):
    """List whitelist entries for an IbetWST contract.

    Results are ordered by creation time descending.
    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 422: an address, query parameter, or platform value is invalid.
    """
    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    whitelist_model = _get_wst_whitelist_model(blockchain_platform)
    # Get whitelists
    whitelist_list = (
        await db.scalars(
            select(whitelist_model)
            .where(
                whitelist_model.ibet_wst_address
                == to_checksum_address(ibet_wst_address)
            )
            .order_by(whitelist_model.created.desc())
        )
    ).all()

    # Response
    account_list: list[dict[str, str]] = []
    for whitelist in whitelist_list:
        account_list.append(
            {
                "st_account_address": whitelist.st_account_address,
                "sc_account_address_in": whitelist.sc_account_address_in,
                "sc_account_address_out": whitelist.sc_account_address_out,
            }
        )

    return json_response({"whitelist_accounts": account_list})


# GET: /ibet_wst/whitelists/{ibet_wst_address}/{account_address}
@router.get(
    "/whitelists/{ibet_wst_address}/{account_address}",
    operation_id="GetIbetWSTWhitelist",
    response_model=GetIbetWSTWhitelistResponse,
    responses=get_routers_responses(404, 422),
)
async def get_ibet_wst_whitelist(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
    query: Annotated[GetIbetWSTWhitelistQuery, Query()],
):
    """Get an account's current whitelist entry from an IbetWST contract.

    The WST address must be registered for the selected platform.
    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, query parameter, or platform value is invalid.
    """
    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(db, ibet_wst_address, blockchain_platform)
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    # Get whitelist status
    wst_contract = _get_wst_contract(ibet_wst_address, blockchain_platform)
    whitelist = await wst_contract.account_white_list(
        to_checksum_address(account_address)
    )

    return json_response(
        {
            "st_account_address": whitelist.st_account,
            "sc_account_address_in": whitelist.sc_account_in,
            "sc_account_address_out": whitelist.sc_account_out,
            "listed": whitelist.listed,
        }
    )


# POST: /ibet_wst/transfers/{ibet_wst_address}
@router.post(
    "/transfers/{ibet_wst_address}",
    operation_id="TransferIbetWST",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(
        IbetWSTInsufficientBalanceError,
        IbetWSTAccountNotWhitelistedError,
        404,
        422,
        503,
    ),
)
async def transfer_ibet_wst(
    request: Request,
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: TransferIbetWSTRequest,
):
    """Queue an authorized transfer of IbetWST tokens.

    The sender must have sufficient balance, and both sender and recipient must be whitelisted.
    Track the queued transaction with the returned `tx_id` through the transaction endpoints.
    The selected platform's master account must be configured, and `blockchain_platform` defaults to Ethereum.

    Errors:
    - 400 `IbetWSTInsufficientBalanceError` (code 13): the sender balance is below the transfer value.
    - 400 `IbetWSTAccountNotWhitelistedError` (code 15): the sender or recipient is not whitelisted.
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, request field, or platform value is invalid.
    - 503: the selected platform's master account is not configured.
    """
    blockchain_platform = IbetWSTBlockchain(req_params.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(db, ibet_wst_address, blockchain_platform)
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    wst_tx_model = _get_wst_tx_model(blockchain_platform)

    # Generate contract instance
    wst_contract = _get_wst_contract(ibet_wst_address, blockchain_platform)

    # Pre-transaction check: Ensure ST token balance is sufficient
    wst_balance = await wst_contract.balance_of(
        to_checksum_address(req_params.from_address)
    )
    if wst_balance < req_params.value:
        raise IbetWSTInsufficientBalanceError

    # Pre-transaction check: Ensure from_address and to_address are whitelisted
    wl_from = await wst_contract.account_white_list(req_params.from_address)
    wl_to = await wst_contract.account_white_list(req_params.to_address)
    if not wl_from.listed or not wl_to.listed:
        raise IbetWSTAccountNotWhitelistedError

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.TRANSFER
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsTransfer(
        from_address=req_params.from_address,
        to_address=req_params.to_address,
        value=req_params.value,
        valid_after=req_params.valid_after,
        valid_before=req_params.valid_before,
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    wst_tx.client_ip = get_client_ip(request)
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /ibet_wst/trades/{ibet_wst_address}/request
@router.post(
    "/trades/{ibet_wst_address}/request",
    operation_id="RequestIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(IbetWSTAccountNotWhitelistedError, 404, 422, 503),
)
async def request_ibet_wst_trade(
    request: Request,
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: RequestIbetWSTTradeRequest,
):
    """Queue an authorized IbetWST trade request.

    Both seller and buyer must be whitelisted.
    Track the queued transaction with the returned `tx_id` through the transaction endpoints.
    The selected platform's master account must be configured, and `blockchain_platform` defaults to Ethereum.

    Errors:
    - 400 `IbetWSTAccountNotWhitelistedError` (code 15): the seller or buyer is not whitelisted.
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, request field, or platform value is invalid.
    - 503: the selected platform's master account is not configured.
    """
    blockchain_platform = IbetWSTBlockchain(req_params.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(db, ibet_wst_address, blockchain_platform)
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    wst_tx_model = _get_wst_tx_model(blockchain_platform)

    # Generate contract instance
    wst_contract = _get_wst_contract(ibet_wst_address, blockchain_platform)

    # Pre-transaction check: Ensure from_address and to_address are whitelisted
    wl_from = await wst_contract.account_white_list(
        req_params.seller_st_account_address
    )
    wl_to = await wst_contract.account_white_list(req_params.buyer_st_account_address)
    if not wl_from.listed or not wl_to.listed:
        raise IbetWSTAccountNotWhitelistedError

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.REQUEST_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsRequestTrade(
        seller_st_account=req_params.seller_st_account_address,
        buyer_st_account=req_params.buyer_st_account_address,
        sc_token_address=req_params.sc_token_address,
        st_value=req_params.st_value,
        sc_value=req_params.sc_value,
        memo=req_params.memo,
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    wst_tx.client_ip = get_client_ip(request)
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /ibet_wst/trades/{ibet_wst_address}/cancel
@router.post(
    "/trades/{ibet_wst_address}/cancel",
    operation_id="CancelIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(404, 422, 503),
)
async def cancel_ibet_wst_trade(
    request: Request,
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: CancelIbetWSTTradeRequest,
):
    """Queue an authorized IbetWST trade cancellation.

    Track the queued transaction with the returned `tx_id` through the transaction endpoints.
    The selected platform's master account must be configured, and `blockchain_platform` defaults to Ethereum.

    Errors:
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, request field, or platform value is invalid.
    - 503: the selected platform's master account is not configured.
    """

    blockchain_platform = IbetWSTBlockchain(req_params.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(db, ibet_wst_address, blockchain_platform)
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    wst_tx_model = _get_wst_tx_model(blockchain_platform)

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.CANCEL_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsCancelTrade(index=req_params.index)
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    wst_tx.client_ip = get_client_ip(request)
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /ibet_wst/trades/{ibet_wst_address}/accept
@router.post(
    "/trades/{ibet_wst_address}/accept",
    operation_id="AcceptIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(
        IbetWSTInsufficientBalanceError,
        ERC20InsufficientAllowanceError,
        404,
        422,
        503,
    ),
)
async def accept_ibet_wst_trade(
    request: Request,
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: AcceptIbetWSTTradeRequest,
):
    """Queue an authorized acceptance of an IbetWST trade.

    The seller must have sufficient WST balance, and the buyer must have sufficient settlement-token allowance.
    Track the queued transaction with the returned `tx_id` through the transaction endpoints.
    The selected platform's master account must be configured, and `blockchain_platform` defaults to Ethereum.

    Errors:
    - 400 `IbetWSTInsufficientBalanceError` (code 13): the seller's WST balance is below the trade value.
    - 400 `ERC20InsufficientAllowanceError` (code 14): the buyer's settlement-token allowance is below the required value.
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, request field, or platform value is invalid.
    - 503: the selected platform's master account is not configured.
    """
    blockchain_platform = IbetWSTBlockchain(req_params.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(db, ibet_wst_address, blockchain_platform)
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    wst_tx_model = _get_wst_tx_model(blockchain_platform)

    # Retrieve trade details
    wst_contract = _get_wst_contract(ibet_wst_address, blockchain_platform)
    trade = await wst_contract.get_trade(req_params.index)

    # Pre-transaction check: Ensure ST token balance is sufficient
    wst_balance = await wst_contract.balance_of(
        to_checksum_address(trade.seller_st_account)
    )
    if wst_balance < trade.st_value:
        raise IbetWSTInsufficientBalanceError

    # Pre-transaction check: Ensure SC token allowance is sufficient
    sc_contract = _get_erc20_contract(trade.sc_token_address, blockchain_platform)
    allowance = await sc_contract.allowance(
        account=to_checksum_address(trade.buyer_sc_account),
        spender=to_checksum_address(ibet_wst_address),
    )
    if allowance < trade.sc_value:
        raise ERC20InsufficientAllowanceError

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.ACCEPT_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsAcceptTrade(index=req_params.index)
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    wst_tx.client_ip = get_client_ip(request)
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /ibet_wst/trades/{ibet_wst_address}/reject
@router.post(
    "/trades/{ibet_wst_address}/reject",
    operation_id="RejectIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(404, 422, 503),
)
async def reject_ibet_wst_trade(
    request: Request,
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: RejectIbetWSTTradeRequest,
):
    """Queue an authorized rejection of an IbetWST trade.

    Track the queued transaction with the returned `tx_id` through the transaction endpoints.
    The selected platform's master account must be configured, and `blockchain_platform` defaults to Ethereum.

    Errors:
    - 404: no registered token uses `ibet_wst_address` on the selected platform.
    - 422: an address, request field, or platform value is invalid.
    - 503: the selected platform's master account is not configured.
    """
    blockchain_platform = IbetWSTBlockchain(req_params.blockchain_platform)

    # Check if ibet-WST exists
    _token = await _find_wst_token_by_address(db, ibet_wst_address, blockchain_platform)
    if _token is None:
        raise HTTPException(status_code=404, detail="IbetWST token not found")

    wst_tx_model = _get_wst_tx_model(blockchain_platform)

    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.REJECT_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsRejectTrade(index=req_params.index)
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    wst_tx.client_ip = get_client_ip(request)
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# GET: /ibet_wst/trades/{ibet_wst_address}
@router.get(
    "/trades/{ibet_wst_address}",
    operation_id="ListIbetWSTTrades",
    response_model=ListIbetWSTTradesResponse,
    responses=get_routers_responses(422),
)
async def list_ibet_wst_trades(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    query: Annotated[
        ListIbetWSTTradesQuery, Query(description="Query parameters for listing trades")
    ],
):
    """List IbetWST trades with filtering and pagination.

    Results are ordered by trade index ascending.
    Filters include participants, settlement token, and trade state.
    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 422: an address, query parameter, or platform value is invalid.
    """
    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    wst_trade_model = _get_wst_trade_model(blockchain_platform)

    # Base Query
    stmt = select(wst_trade_model).where(
        wst_trade_model.ibet_wst_address == to_checksum_address(ibet_wst_address)
    )
    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(wst_trade_model).order_by(None)
    )

    # Search Filter
    if query.seller_st_account_address is not None:
        stmt = stmt.where(
            wst_trade_model.seller_st_account_address == query.seller_st_account_address
        )
    if query.buyer_st_account_address is not None:
        stmt = stmt.where(
            wst_trade_model.buyer_st_account_address == query.buyer_st_account_address
        )
    if query.sc_token_address is not None:
        stmt = stmt.where(wst_trade_model.sc_token_address == query.sc_token_address)
    if query.seller_sc_account_address is not None:
        stmt = stmt.where(
            wst_trade_model.seller_sc_account_address == query.seller_sc_account_address
        )
    if query.buyer_sc_account_address is not None:
        stmt = stmt.where(
            wst_trade_model.buyer_sc_account_address == query.buyer_sc_account_address
        )
    if query.state is not None:
        stmt = stmt.where(wst_trade_model.state == query.state)
    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(wst_trade_model).order_by(None)
    )

    # Sort
    stmt = stmt.order_by(asc(wst_trade_model.index))

    # Pagination
    if query.limit is not None:
        stmt = stmt.limit(query.limit)
    if query.offset is not None:
        stmt = stmt.offset(query.offset)

    # Execute Query
    _trades = (await db.scalars(stmt)).all()

    # Response
    trade_list = [
        {
            "index": trade.index,
            "seller_st_account_address": trade.seller_st_account_address,
            "buyer_st_account_address": trade.buyer_st_account_address,
            "sc_token_address": trade.sc_token_address,
            "seller_sc_account_address": trade.seller_sc_account_address,
            "buyer_sc_account_address": trade.buyer_sc_account_address,
            "st_value": trade.st_value,
            "sc_value": int(trade.sc_value),
            "state": trade.state,
            "memo": trade.memo,
        }
        for trade in _trades
    ]
    resp = {
        "result_set": {
            "count": count,
            "offset": query.offset,
            "limit": query.limit,
            "total": total,
        },
        "trades": trade_list,
    }
    return json_response(resp)


# GET: /ibet_wst/trades/{ibet_wst_address}/{index}
@router.get(
    "/trades/{ibet_wst_address}/{index}",
    operation_id="GetIbetWSTTrade",
    response_model=GetIbetWSTTradeResponse,
    responses=get_routers_responses(404, 422),
)
async def get_ibet_wst_trade(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    index: Annotated[int, Path(description="Trade index")],
    query: Annotated[GetIbetWSTTradeQuery, Query()],
):
    """Retrieve one IbetWST trade by contract address and index.

    `blockchain_platform` defaults to Ethereum.

    Errors:
    - 404: no trade exists for the contract address and index.
    - 422: an address, path parameter, query parameter, or platform value is invalid.
    """
    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    wst_trade_model = _get_wst_trade_model(blockchain_platform)
    # Get Trade
    trade = (
        await db.scalars(
            select(wst_trade_model).where(
                and_(
                    wst_trade_model.ibet_wst_address
                    == to_checksum_address(ibet_wst_address),
                    wst_trade_model.index == index,
                )
            )
        )
    ).first()
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    # Response
    resp = {
        "index": trade.index,
        "seller_st_account_address": trade.seller_st_account_address,
        "buyer_st_account_address": trade.buyer_st_account_address,
        "sc_token_address": trade.sc_token_address,
        "seller_sc_account_address": trade.seller_sc_account_address,
        "buyer_sc_account_address": trade.buyer_sc_account_address,
        "st_value": trade.st_value,
        "sc_value": int(trade.sc_value),
        "state": trade.state,
        "memo": trade.memo,
    }
    return json_response(resp)


# GET: /ibet_wst/erc20/balance
@router.get(
    "/erc20/balance",
    operation_id="GetERC20Balance",
    response_model=GetERC20BalanceResponse,
    responses=get_routers_responses(422),
)
async def get_erc20_balance(
    query: Annotated[
        GetERC20BalanceQuery, Query(description="Query parameters for ERC20 balance")
    ],
):
    """Get an ERC-20 balance from the selected blockchain.

    If the supplied token address does not expose a compatible ERC-20 `balanceOf`, the result is normally zero.
    `blockchain_platform` selects Ethereum or Avalanche and defaults to Ethereum.

    Errors:
    - 422: an address, query parameter, or platform value is invalid.
    """

    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    # Get balance amount
    # - If token_address is not an ERC20 token, it will return 0 balance.
    erc20 = _get_erc20_contract(query.token_address, blockchain_platform)
    balance = await erc20.balance_of(query.account_address)

    # Return response
    return json_response({"balance": balance})


# GET: /ibet_wst/erc20/allowance
@router.get(
    "/erc20/allowance",
    operation_id="GetERC20Allowance",
    response_model=GetERC20AllowanceResponse,
    responses=get_routers_responses(422),
)
async def get_erc20_allowance(
    query: Annotated[
        GetERC20AllowanceQuery,
        Query(description="Query parameters for ERC20 allowance"),
    ],
):
    """Get an ERC-20 allowance from the selected blockchain.

    If the supplied token address does not expose a compatible ERC-20 `allowance`, the result is normally zero.
    `blockchain_platform` selects Ethereum or Avalanche and defaults to Ethereum.

    Errors:
    - 422: an address, query parameter, or platform value is invalid.
    """

    blockchain_platform = IbetWSTBlockchain(query.blockchain_platform)

    # Get allowance amount
    # - If token_address is not an ERC20 token, it will return 0 allowance
    erc20 = _get_erc20_contract(query.token_address, blockchain_platform)
    allowance = await erc20.allowance(query.account_address, query.spender_address)

    # Return response
    return json_response({"allowance": allowance})


###################################################################
# Utility Functions
###################################################################
def get_client_ip(request: Request) -> str | None:
    """
    Get client IP address from the request, considering possible proxy headers
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # If there are multiple, the first one is the client IP
        client_ip = x_forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client is not None else None
    return client_ip


def _to_event_log_int(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str | float):
        return int(value)
    return default


def _build_event_log_for_response(
    wst_tx: EthIbetWSTTx | AvaIbetWSTTx,
) -> dict[str, Any] | None:
    """
    Format the event_log from the DB for API response
    """

    event_log = wst_tx.event_log
    if event_log is None:
        return None

    event_log = dict(event_log)

    if wst_tx.tx_type in [
        IbetWSTTxType.REQUEST_TRADE,
        IbetWSTTxType.CANCEL_TRADE,
        IbetWSTTxType.ACCEPT_TRADE,
        IbetWSTTxType.REJECT_TRADE,
    ]:
        sc_value = _to_event_log_int(event_log.get("sc_value", 0), default=0)
        sc_decimals = _to_event_log_int(event_log.get("sc_decimals", 6), default=6)

        event_log["sc_value"] = sc_value
        event_log["sc_decimals"] = sc_decimals

        # Return as a fixed-point decimal string with sc_decimals digits
        if sc_decimals > 0:
            scale = 10**sc_decimals
            int_part = sc_value // scale
            frac_part = sc_value % scale
            event_log["display_sc_value"] = f"{int_part}.{frac_part:0{sc_decimals}d}"
        else:
            event_log["display_sc_value"] = str(sc_value)

    return event_log
