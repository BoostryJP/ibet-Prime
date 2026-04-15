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

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from starlette.requests import Request

import config as app_config
from app.database import DBAsyncSession
from app.model.db import IDXBlockDataBlockNumber
from app.model.schema import ListBlockDataQuery, ListTxDataQuery
from config import BC_EXPLORER_ENABLED

from . import bc_explorer

router = APIRouter(prefix="/blockchain_explorer", tags=["[misc] blockchain_explorer"])

templates = Jinja2Templates(directory="app/templates")


# Helper: get latest synced block number
async def _get_latest_block_number(db: DBAsyncSession) -> int | None:
    idx_block_data_block_number = (
        await db.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == str(app_config.CHAIN_ID))
            .limit(1)
        )
    ).first()
    return (
        idx_block_data_block_number.latest_block_number
        if idx_block_data_block_number
        else None
    )


@router.get(
    "/ui",
    summary="[ibet Blockchain Explorer] UI index",
    response_class=HTMLResponse,
)
async def ui_index(
    request: Request,
    db: DBAsyncSession,
    from_block_number: Annotated[int | None, Query()] = None,
    to_block_number: Annotated[int | None, Query()] = None,
    sort_order: Annotated[int | None, Query()] = 1,
    limit: Annotated[int | None, Query()] = 10,
    offset: Annotated[int | None, Query()] = 0,
    block_number: Annotated[int | None, Query()] = None,
    tx_hash: Annotated[str | None, Query()] = None,
    has_transactions: Annotated[bool | None, Query()] = None,
):
    if BC_EXPLORER_ENABLED is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )
    latest_block_number = await _get_latest_block_number(db)
    return templates.TemplateResponse(
        request=request,
        name="misc/bc_explorer/index.html",
        context={
            "request": request,
            "latest_block_number": latest_block_number,
            "initial_block_query": {
                "from_block_number": from_block_number,
                "to_block_number": to_block_number,
                "sort_order": sort_order,
                "limit": limit,
                "offset": offset,
                "has_transactions": has_transactions,
            },
            "initial_block_number": block_number,
            "initial_tx_hash": tx_hash,
        },
    )


@router.get(
    "/ui/blocks",
    summary="[ibet Blockchain Explorer] UI partial: blocks list",
    response_class=HTMLResponse,
)
async def ui_blocks(
    request: Request,
    db: DBAsyncSession,
    get_query: Annotated[ListBlockDataQuery, Query()],
):
    if BC_EXPLORER_ENABLED is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    # If not HTMX request, render full UI with same query
    if request.headers.get("HX-Request") != "true":
        return templates.TemplateResponse(
            request=request,
            name="misc/bc_explorer/index.html",
            context={
                "request": request,
                "latest_block_number": await _get_latest_block_number(db),
                "initial_block_query": {
                    "from_block_number": get_query.from_block_number,
                    "to_block_number": get_query.to_block_number,
                    "sort_order": get_query.sort_order,
                    "limit": get_query.limit,
                    "offset": get_query.offset,
                    "has_transactions": get_query.has_transactions,
                },
                "initial_block_number": None,
                "initial_tx_hash": None,
            },
        )

    result = await bc_explorer.service_list_block_data(db=db, get_query=get_query)
    blocks = result.get("block_data", [])
    rs = result.get("result_set", {})
    return templates.TemplateResponse(
        request=request,
        name="misc/bc_explorer/blocks.html",
        context={
            "request": request,
            "blocks": blocks,
            "count": rs.get("count", 0),
            "offset": rs.get("offset", 0),
            "limit": rs.get("limit", 0),
            "total": rs.get("total", 0),
        },
    )


@router.get(
    "/ui/block/{block_number}",
    summary="[ibet Blockchain Explorer] UI partial: block detail",
    response_class=HTMLResponse,
)
async def ui_block_detail(
    request: Request,
    db: DBAsyncSession,
    block_number: Annotated[int, Path(ge=0)],
):
    if BC_EXPLORER_ENABLED is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    if request.headers.get("HX-Request") != "true":
        return templates.TemplateResponse(
            request=request,
            name="misc/bc_explorer/index.html",
            context={
                "request": request,
                "latest_block_number": await _get_latest_block_number(db),
                "initial_block_query": {},
                "initial_block_number": block_number,
                "initial_tx_hash": None,
            },
        )

    block = await bc_explorer.service_get_block_data(db=db, block_number=block_number)
    return templates.TemplateResponse(
        request=request,
        name="misc/bc_explorer/block_detail.html",
        context={"request": request, "block": block},
    )


@router.get(
    "/ui/txs",
    summary="[ibet Blockchain Explorer] UI partial: tx list",
    response_class=HTMLResponse,
)
async def ui_txs(
    request: Request,
    db: DBAsyncSession,
    get_query: Annotated[ListTxDataQuery, Query()],
):
    if BC_EXPLORER_ENABLED is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    if request.headers.get("HX-Request") != "true":
        return templates.TemplateResponse(
            request=request,
            name="misc/bc_explorer/index.html",
            context={
                "request": request,
                "latest_block_number": await _get_latest_block_number(db),
                "initial_block_query": {},
                "initial_block_number": get_query.block_number,
                "initial_tx_hash": None,
            },
        )

    result = await bc_explorer.service_list_tx_data(db=db, get_query=get_query)
    txs = result.get("tx_data", [])
    rs = result.get("result_set", {})
    return templates.TemplateResponse(
        request=request,
        name="misc/bc_explorer/txs.html",
        context={
            "request": request,
            "txs": txs,
            "count": rs.get("count", 0),
            "offset": rs.get("offset", 0),
            "limit": rs.get("limit", 0),
            "total": rs.get("total", 0),
        },
    )


@router.get(
    "/ui/tx/{hash}",
    summary="[ibet Blockchain Explorer] UI partial: tx detail",
    response_class=HTMLResponse,
)
async def ui_tx_detail(
    request: Request,
    db: DBAsyncSession,
    hash: Annotated[str, Path()],
):
    if BC_EXPLORER_ENABLED is False:
        raise HTTPException(
            status_code=404, detail="This URL is not available in the current settings"
        )

    if request.headers.get("HX-Request") != "true":
        return templates.TemplateResponse(
            request=request,
            name="misc/bc_explorer/index.html",
            context={
                "request": request,
                "latest_block_number": await _get_latest_block_number(db),
                "initial_block_query": {},
                "initial_block_number": None,
                "initial_tx_hash": hash,
            },
        )

    tx = await bc_explorer.service_get_tx_data(db=db, hash=hash)
    return templates.TemplateResponse(
        request=request,
        name="misc/bc_explorer/tx_detail.html",
        context={"request": request, "tx": tx},
    )
