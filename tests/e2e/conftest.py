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

import asyncio
import socket
import threading
import time
from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

import pytest
import pytest_asyncio
import uvicorn
from fastapi import HTTPException
from playwright.async_api import Browser, async_playwright

from app.database import db_async_session
from app.main import app
from app.routers.misc import bc_explorer, bc_explorer_ui


@dataclass(frozen=True)
class ExplorerSeedData:
    """
    Seed data for the blockchain explorer used in E2E tests.
    """

    latest_block_number: int
    block_with_transactions_number: int
    block_without_transactions_number: int
    block_with_transactions_hash: str
    block_without_transactions_hash: str
    tx_hash: str
    from_address: str
    to_address: str


class BlockQuery(Protocol):
    """
    Query parameters for listing blocks in the explorer.
    """

    from_block_number: int | None
    to_block_number: int | None
    sort_order: int | None
    limit: int | None
    offset: int | None
    has_transactions: bool | None


class BlockDataRow(TypedDict):
    """
    Data structure representing a block in the block list response.
    """

    number: int
    hash: str
    transactions: list[str]
    timestamp: int
    gas_limit: int
    gas_used: int
    size: int


class BlockDetailRow(TypedDict):
    """
    Data structure representing detailed block information in the block detail response.
    """

    number: int
    parent_hash: str
    sha3_uncles: str
    miner: str
    state_root: str
    transactions_root: str
    receipts_root: str
    logs_bloom: str
    difficulty: int
    gas_limit: int
    gas_used: int
    timestamp: int
    proof_of_authority_data: str
    mix_hash: str
    nonce: str
    hash: str
    size: int
    transactions: list[str]


class TxDetailRow(TypedDict):
    """
    Data structure representing detailed transaction information in the transaction detail response.
    """

    hash: str
    block_hash: str
    block_number: int
    transaction_index: int
    from_address: str
    to_address: str
    contract_name: str | None
    contract_function: str | None
    contract_parameters: dict[str, Any] | None
    gas: int
    gas_price: int
    value: int
    nonce: int


# Fixed values that keep the browser assertions deterministic.
EXPLORER_SEED_DATA = ExplorerSeedData(
    latest_block_number=7,
    block_with_transactions_number=7,
    block_without_transactions_number=6,
    block_with_transactions_hash="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    block_without_transactions_hash="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    tx_hash="0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    from_address="0x1234567890abcdef1234567890abcdef12345678",
    to_address="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
)


def _make_block_data(
    block_number: int, block_hash: str, transactions: list[str]
) -> BlockDataRow:
    """
    Create a block data row with the given parameters and deterministic timestamp and size.
    """
    return {
        "number": block_number,
        "hash": block_hash,
        "transactions": transactions,
        "timestamp": 1_700_000_000
        - (EXPLORER_SEED_DATA.latest_block_number - block_number) * 100,
        "gas_limit": 30_000_000,
        "gas_used": 21_000 if transactions else 0,
        "size": 1_024 if transactions else 512,
    }


def _make_block_detail(
    block_number: int, block_hash: str, transactions: list[str]
) -> BlockDetailRow:
    """
    Create a block detail row with the given parameters and deterministic values for other fields.
    """
    return {
        "number": block_number,
        "parent_hash": "0x1111111111111111111111111111111111111111111111111111111111111111",
        "sha3_uncles": "0x2222222222222222222222222222222222222222222222222222222222222222",
        "miner": "0x3333333333333333333333333333333333333333",
        "state_root": "0x4444444444444444444444444444444444444444444444444444444444444444",
        "transactions_root": "0x5555555555555555555555555555555555555555555555555555555555555555",
        "receipts_root": "0x6666666666666666666666666666666666666666666666666666666666666666",
        "logs_bloom": "0x" + "00" * 256,
        "difficulty": 1,
        "gas_limit": 30_000_000,
        "gas_used": 21_000 if transactions else 0,
        "timestamp": 1_700_000_000
        - (EXPLORER_SEED_DATA.latest_block_number - block_number) * 100,
        "proof_of_authority_data": "0x7777777777777777",
        "mix_hash": "0x8888888888888888888888888888888888888888888888888888888888888888",
        "nonce": "0x0000000000000000",
        "hash": block_hash,
        "size": 1_024 if transactions else 512,
        "transactions": transactions,
    }


def _make_tx_detail(tx_hash: str) -> TxDetailRow:
    """
    Create a transaction detail row with the given hash and deterministic values for other fields.
    """
    return {
        "hash": tx_hash,
        "block_hash": EXPLORER_SEED_DATA.block_with_transactions_hash,
        "block_number": EXPLORER_SEED_DATA.block_with_transactions_number,
        "transaction_index": 0,
        "from_address": EXPLORER_SEED_DATA.from_address,
        "to_address": EXPLORER_SEED_DATA.to_address,
        "contract_name": None,
        "contract_function": None,
        "contract_parameters": None,
        "gas": 21_000,
        "gas_price": 1,
        "value": 123,
        "nonce": 9,
    }


@pytest.fixture(scope="session", autouse=True)
def enable_bc_explorer_ui() -> Iterator[None]:
    """
    Fixture to enable the blockchain explorer UI and mock its backend services for E2E tests.

    This fixture performs the following actions:
    1. Overrides the blockchain explorer services with deterministic in-memory implementations that return fixed data based on `EXPLORER_SEED_DATA`.
    2. Ensures the explorer UI router is included in the FastAPI app.
    3. Yields control to the test, allowing it to run with the mocked services.
    4. Restores the original services and router after the test completes.
    """

    # Swap the explorer services with deterministic in-memory responses for E2E.
    original_bc_enabled = bc_explorer_ui.BC_EXPLORER_ENABLED
    original_get_latest_block_number = getattr(
        bc_explorer_ui, "_get_latest_block_number"
    )
    original_list_block_data = bc_explorer.service_list_block_data
    original_get_block_data = bc_explorer.service_get_block_data
    original_get_tx_data = bc_explorer.service_get_tx_data

    async def _mock_get_latest_block_number(_: Any) -> int:
        """Return the latest block number from the seed data."""
        return EXPLORER_SEED_DATA.latest_block_number

    async def _mock_list_block_data(db: Any, get_query: BlockQuery) -> dict[str, Any]:
        """Return a list of blocks based on the seed data, applying filters and pagination from the query."""
        blocks: list[BlockDataRow] = [
            _make_block_data(
                EXPLORER_SEED_DATA.block_without_transactions_number,
                EXPLORER_SEED_DATA.block_without_transactions_hash,
                [],
            ),
            _make_block_data(
                EXPLORER_SEED_DATA.block_with_transactions_number,
                EXPLORER_SEED_DATA.block_with_transactions_hash,
                [EXPLORER_SEED_DATA.tx_hash],
            ),
        ]

        if get_query.from_block_number is not None:
            blocks = [
                block
                for block in blocks
                if block["number"] >= get_query.from_block_number
            ]
        if get_query.to_block_number is not None:
            blocks = [
                block
                for block in blocks
                if block["number"] <= get_query.to_block_number
            ]
        if get_query.has_transactions:
            blocks = [block for block in blocks if len(block["transactions"]) > 0]

        sort_order = get_query.sort_order or 1
        blocks = sorted(
            blocks,
            key=lambda block: block["number"],
            reverse=sort_order != 0,
        )

        offset = get_query.offset or 0
        limit = get_query.limit or len(blocks)
        sliced_blocks = blocks[offset : offset + limit]

        return {
            "result_set": {
                "count": len(blocks),
                "offset": offset,
                "limit": limit,
                "total": EXPLORER_SEED_DATA.latest_block_number + 1,
            },
            "block_data": sliced_blocks,
        }

    async def _mock_get_block_data(db: Any, block_number: int) -> BlockDetailRow:
        """Return block details based on the block number, using the seed data."""
        if block_number == EXPLORER_SEED_DATA.block_with_transactions_number:
            return _make_block_detail(
                EXPLORER_SEED_DATA.block_with_transactions_number,
                EXPLORER_SEED_DATA.block_with_transactions_hash,
                [EXPLORER_SEED_DATA.tx_hash],
            )
        if block_number == EXPLORER_SEED_DATA.block_without_transactions_number:
            return _make_block_detail(
                EXPLORER_SEED_DATA.block_without_transactions_number,
                EXPLORER_SEED_DATA.block_without_transactions_hash,
                [],
            )
        raise HTTPException(status_code=404, detail="block data not found")

    async def _mock_get_tx_data(db: Any, hash: str) -> TxDetailRow:
        """Return transaction details based on the transaction hash, using the seed data."""
        if hash == EXPLORER_SEED_DATA.tx_hash:
            return _make_tx_detail(hash)
        raise HTTPException(status_code=404, detail="block data not found")

    bc_explorer_ui.BC_EXPLORER_ENABLED = True

    # The UI module uses a private helper, so we replace it directly for the test run.
    bc_explorer_ui._get_latest_block_number = _mock_get_latest_block_number  # pyright: ignore[reportPrivateUsage]
    bc_explorer.service_list_block_data = _mock_list_block_data
    bc_explorer.service_get_block_data = _mock_get_block_data
    bc_explorer.service_get_tx_data = _mock_get_tx_data
    app.dependency_overrides[db_async_session] = lambda: object()

    # Ensure the explorer UI router is included in the app if not already present.
    if not any(
        getattr(route, "path", None) == "/blockchain_explorer/ui"
        for route in app.router.routes
    ):
        app.include_router(bc_explorer_ui.router)

    # Yield control to the test
    yield

    # Restore the original services and router after the test completes.
    bc_explorer_ui.BC_EXPLORER_ENABLED = original_bc_enabled
    bc_explorer_ui._get_latest_block_number = original_get_latest_block_number  # pyright: ignore[reportPrivateUsage]
    bc_explorer.service_list_block_data = original_list_block_data
    bc_explorer.service_get_block_data = original_get_block_data
    bc_explorer.service_get_tx_data = original_get_tx_data
    app.dependency_overrides.pop(db_async_session, None)


@pytest.fixture(scope="function", autouse=True)
def ibet_block_number() -> Iterator[None]:
    yield


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def browser_server(enable_bc_explorer_ui: None) -> Iterator[str]:
    """
    Fixture to start the FastAPI app on a real port for Playwright E2E tests.

    This fixture performs the following actions:
    1. Finds a free port and starts the FastAPI app using Uvicorn in a separate thread.
    2. Waits for the server to be ready before yielding the server URL to the test.
    3. After the test completes, signals the server to shut down and waits for the thread to finish.
    """
    port = _find_free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        lifespan="off",
    )
    server = uvicorn.Server(config)

    def _run() -> None:
        asyncio.run(server.serve())

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if server.started:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Playwright test server did not start")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="function")
def seeded_explorer_data() -> ExplorerSeedData:
    """Fixture to provide the seeded explorer data for tests."""
    return EXPLORER_SEED_DATA


@pytest_asyncio.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    """Fixture to launch a Playwright browser instance for E2E tests."""
    async with async_playwright() as playwright:
        launched_browser = await playwright.chromium.launch()
        try:
            yield launched_browser
        finally:
            await launched_browser.close()
