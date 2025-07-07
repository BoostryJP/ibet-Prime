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
from typing import Annotated, Sequence

import pytz
from eth_utils import to_checksum_address
from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy import and_, asc, desc, func, select

import config
from app.database import DBAsyncSession
from app.model import EthereumAddress
from app.model.db import (
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
    IDXEthIbetWSTTrade,
    Token,
    TokenType,
)
from app.model.eth import IbetWST
from app.model.ibet import IbetShareContract, IbetStraightBondContract
from app.model.schema import (
    AcceptIbetWSTTradeRequest,
    BurnIbetWSTRequest,
    CancelIbetWSTTradeRequest,
    GetIbetWSTBalanceResponse,
    GetIbetWSTTradeResponse,
    GetIbetWSTTransactionResponse,
    GetIbetWSTWhitelistResponse,
    IbetWSTTransactionResponse,
    ListAllIbetWSTTokensQuery,
    ListAllIbetWSTTokensResponse,
    ListAllIbetWSTTokensSortItem,
    ListIbetWSTTradesQuery,
    ListIbetWSTTradesResponse,
    RejectIbetWSTTradeRequest,
    RequestIbetWSTTradeRequest,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from eth_config import ETH_MASTER_ACCOUNT_ADDRESS

router = APIRouter(prefix="/ibet_wst", tags=["[misc] ibet_wst"])
local_tz = pytz.timezone(config.TZ)
utc_tz = pytz.timezone("UTC")


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
    """
    List all IbetWST tokens

    - This endpoint retrieves all IbetWST tokens based on the provided query parameters.
    - Only tokens whose deployment has already been finalized will be returned.
    """

    # Base Query
    stmt = select(Token).where(Token.ibet_wst_deployed.is_(True))

    if get_query.issuer_address is not None:
        stmt = stmt.where(Token.issuer_address == get_query.issuer_address)

    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Search Filter
    if get_query.ibet_wst_address is not None:
        stmt = stmt.where(Token.ibet_wst_address == get_query.ibet_wst_address)
    if get_query.ibet_token_address is not None:
        stmt = stmt.where(Token.token_address == get_query.ibet_token_address)
    if get_query.token_type is not None:
        stmt = stmt.where(Token.type == get_query.token_type)

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(Token).order_by(None)
    )

    # Sort
    sort_attr = getattr(Token, get_query.sort_item, None)
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if get_query.sort_item != ListAllIbetWSTTokensSortItem.CREATED:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(Token.created))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

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
                "ibet_wst_address": _token.ibet_wst_address,
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
    responses=get_routers_responses(422),
)
async def get_ibet_wst_balance(
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
):
    """
    Get IbetWST balance for a specific account address

    - This endpoint retrieves the IbetWST balance for the specified account address.
    """

    wst_contract = IbetWST(to_checksum_address(ibet_wst_address))
    balance = await wst_contract.balance_of(to_checksum_address(account_address))

    return json_response({"balance": balance})


# POST: /ibet_wst/balances/{account_address}/{ibet_wst_address}/burn
@router.post(
    "/balances/{account_address}/{ibet_wst_address}/burn",
    operation_id="BurnIbetWSTBalance",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(422),
)
async def burn_ibet_wst_balance(
    db: DBAsyncSession,
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: BurnIbetWSTRequest,
):
    """
    Burn IbetWST balance
    - This endpoint allows a user to send burnWithAuthorization transaction to the IbetWST contract.
    """
    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = EthIbetWSTTx()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.BURN
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsBurn(
        from_address=to_checksum_address(account_address),
        value=req_params.value,
    )
    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# GET: /ibet_wst/transactions/{tx_id}
@router.get(
    "/transactions/{tx_id}",
    operation_id="GetIbetWSTTransaction",
    response_model=GetIbetWSTTransactionResponse,
    responses=get_routers_responses(404),
)
async def get_ibet_wst_transaction(
    db: DBAsyncSession,
    tx_id: Annotated[str, Path(description="IbetWST transaction ID")],
):
    """
    Get IbetWST transaction details

    - This endpoint retrieves the details of a specific IbetWST transaction by its ID.
    """
    # Get Transaction
    wst_tx: EthIbetWSTTx | None = (
        await db.scalars(
            select(EthIbetWSTTx).where(EthIbetWSTTx.tx_id == tx_id).limit(1)
        )
    ).first()
    if wst_tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

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
        "event_log": wst_tx.event_log,
    }
    return json_response(resp)


# GET: /ibet_wst/whitelists/{ibet_wst_address}/{account_address}
@router.get(
    "/whitelists/{ibet_wst_address}/{account_address}",
    operation_id="GetIbetWSTWhitelist",
    response_model=GetIbetWSTWhitelistResponse,
    responses=get_routers_responses(422),
)
async def get_ibet_wst_whitelist(
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    account_address: Annotated[EthereumAddress, Path(description="Account address")],
):
    """
    Get IbetWST whitelist status for a specific account address

    - This endpoint retrieves the whitelist status of an account address for the specified IbetWST contract.
    """
    wst_contract = IbetWST(to_checksum_address(ibet_wst_address))
    is_whitelisted = await wst_contract.account_white_list(
        to_checksum_address(account_address)
    )

    return json_response({"whitelisted": is_whitelisted})


# POST: /ibet_wst/trades/{ibet_wst_address}/request
@router.post(
    "/trades/{ibet_wst_address}/request",
    operation_id="RequestIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(422),
)
async def request_ibet_wst_trade(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: RequestIbetWSTTradeRequest,
):
    """
    Request an IbetWST trade

    - This endpoint allows a user to send requestTradeWithAuthorization transaction to the IbetWST contract.
    """
    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = EthIbetWSTTx()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.REQUEST_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsRequestTrade(
        seller_st_account_address=req_params.seller_st_account_address,
        buyer_st_account_address=req_params.buyer_st_account_address,
        sc_token_address=req_params.sc_token_address,
        seller_sc_account_address=req_params.seller_sc_account_address,
        buyer_sc_account_address=req_params.buyer_sc_account_address,
        st_value=req_params.st_value,
        sc_value=req_params.sc_value,
        memo=req_params.memo,
    )
    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /ibet_wst/trades/{ibet_wst_address}/cancel
@router.post(
    "/trades/{ibet_wst_address}/cancel",
    operation_id="CancelIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(422),
)
async def cancel_ibet_wst_trade(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: CancelIbetWSTTradeRequest,
):
    """
    Cancel an IbetWST trade

    - This endpoint allows a user to send cancelTradeWithAuthorization transaction to the IbetWST contract.
    """
    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = EthIbetWSTTx()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.CANCEL_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsCancelTrade(index=req_params.index)
    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /ibet_wst/trades/{ibet_wst_address}/accept
@router.post(
    "/trades/{ibet_wst_address}/accept",
    operation_id="AcceptIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(422),
)
async def accept_ibet_wst_trade(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: AcceptIbetWSTTradeRequest,
):
    """
    Accept an IbetWST trade

    - This endpoint allows a user to send acceptTradeWithAuthorization transaction to the IbetWST contract.
    """
    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = EthIbetWSTTx()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.ACCEPT_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsAcceptTrade(index=req_params.index)
    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
    db.add(wst_tx)
    await db.commit()

    return json_response({"tx_id": tx_id})


# POST: /ibet_wst/trades/{ibet_wst_address}/reject
@router.post(
    "/trades/{ibet_wst_address}/reject",
    operation_id="RejectIbetWSTTrade",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(422),
)
async def reject_ibet_wst_trade(
    db: DBAsyncSession,
    ibet_wst_address: Annotated[
        EthereumAddress, Path(description="IbetWST contract address")
    ],
    req_params: RejectIbetWSTTradeRequest,
):
    """
    Reject an IbetWST trade

    - This endpoint allows a user to send rejectTradeWithAuthorization transaction to the IbetWST contract.
    """
    # Insert transaction record
    tx_id = str(uuid.uuid4())
    wst_tx = EthIbetWSTTx()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.REJECT_TRADE
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsRejectTrade(index=req_params.index)
    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
    wst_tx.authorizer = req_params.authorizer
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=req_params.authorization.nonce,
        v=req_params.authorization.v,
        r=req_params.authorization.r,
        s=req_params.authorization.s,
    )
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
    """
    List IbetWST trades

    - This endpoint retrieves a list of trades from the IbetWST contract based on the provided query parameters.
    """
    # Base Query
    stmt = select(IDXEthIbetWSTTrade).where(
        IDXEthIbetWSTTrade.ibet_wst_address == ibet_wst_address
    )
    total = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(IDXEthIbetWSTTrade)
        .order_by(None)
    )

    # Search Filter
    if query.seller_st_account_address is not None:
        stmt = stmt.where(
            IDXEthIbetWSTTrade.seller_st_account_address
            == query.seller_st_account_address
        )
    if query.buyer_st_account_address is not None:
        stmt = stmt.where(
            IDXEthIbetWSTTrade.buyer_st_account_address
            == query.buyer_st_account_address
        )
    if query.sc_token_address is not None:
        stmt = stmt.where(IDXEthIbetWSTTrade.sc_token_address == query.sc_token_address)
    if query.seller_sc_account_address is not None:
        stmt = stmt.where(
            IDXEthIbetWSTTrade.seller_sc_account_address
            == query.seller_sc_account_address
        )
    if query.buyer_sc_account_address is not None:
        stmt = stmt.where(
            IDXEthIbetWSTTrade.buyer_sc_account_address
            == query.buyer_sc_account_address
        )
    if query.state is not None:
        stmt = stmt.where(IDXEthIbetWSTTrade.state == query.state)
    count = await db.scalar(
        stmt.with_only_columns(func.count())
        .select_from(IDXEthIbetWSTTrade)
        .order_by(None)
    )

    # Sort
    stmt = stmt.order_by(asc(IDXEthIbetWSTTrade.index))

    # Pagination
    if query.limit is not None:
        stmt = stmt.limit(query.limit)
    if query.offset is not None:
        stmt = stmt.offset(query.offset)

    # Execute Query
    _trades: Sequence[IDXEthIbetWSTTrade] = (await db.scalars(stmt)).all()

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
            "sc_value": trade.sc_value,
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
):
    """
    Get details of a specific IbetWST trade

    - This endpoint retrieves the details of a specific trade by its index from the IbetWST contract.
    """
    # Get Trade
    trade: IDXEthIbetWSTTrade | None = (
        await db.scalars(
            select(IDXEthIbetWSTTrade).where(
                and_(
                    IDXEthIbetWSTTrade.ibet_wst_address == ibet_wst_address,
                    IDXEthIbetWSTTrade.index == index,
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
        "sc_value": trade.sc_value,
        "state": trade.state,
        "memo": trade.memo,
    }
    return json_response(resp)
