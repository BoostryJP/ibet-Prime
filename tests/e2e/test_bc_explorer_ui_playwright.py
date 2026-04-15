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

import pytest
from playwright.async_api import Browser, expect

from tests.e2e.conftest import ExplorerSeedData

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _truncate(value: str, prefix_length: int, suffix_length: int) -> str:
    """Helper function to truncate a string with an ellipsis in the middle."""
    return f"{value[:prefix_length]}…{value[-suffix_length:]}"


async def test_bc_explorer_index_page_renders_shell(
    browser_server: str,
    browser: Browser,
    seeded_explorer_data: ExplorerSeedData,
) -> None:
    """
    Verify the blockchain explorer index page renders the main shell
    and expected dynamic content based on the seeded explorer data.

        The test covers the following scenarios:
        1. The main shell renders with the expected header and search input.
        2. The latest synced block number from the seeded data is displayed in the banner.
    """

    context = await browser.new_context()
    page = await context.new_page()

    response = await page.goto(
        f"{browser_server}/blockchain_explorer/ui",
        wait_until="domcontentloaded",
    )

    assert response is not None
    assert response.status == 200

    # Verify the initial shell renders with the expected explorer header.
    await expect(
        page.get_by_role("heading", name="ibet Blockchain Explorer")
    ).to_be_visible()

    # Verify the search input is present and exposes the expected placeholder.
    await expect(page.locator("#header-txhash")).to_have_attribute(
        "placeholder", "Tx hash (0x...)"
    )

    # Verify the page reflects the latest synced block number in the banner.
    await expect(
        page.get_by_text(
            f"Latest synced block: #{seeded_explorer_data.latest_block_number}"
        )
    ).to_be_visible()

    await context.close()


async def test_bc_explorer_fragments_render_block_and_tx_details(
    browser_server: str,
    browser: Browser,
    seeded_explorer_data: ExplorerSeedData,
) -> None:
    """
    Verify the blockchain explorer fragments render expected block
    and transaction details based on the seeded explorer data.

        The test covers the following scenarios:
        1. The blocks fragment correctly filters and paginates blocks with transactions.
        2. The block detail fragment shows the full block hash and truncated transaction hashes.
        3. The transaction detail fragment renders truncated hashes and optional contract metadata.
    """

    blocks_context = await browser.new_context(
        extra_http_headers={"HX-Request": "true"}
    )
    blocks_page = await blocks_context.new_page()

    blocks_response = await blocks_page.goto(
        (
            f"{browser_server}/blockchain_explorer/ui/blocks"
            f"?from_block_number={seeded_explorer_data.block_without_transactions_number}"
            f"&to_block_number={seeded_explorer_data.block_with_transactions_number}"
            "&sort_order=1&limit=10&offset=0&has_transactions=true"
        ),
        wait_until="domcontentloaded",
    )

    assert blocks_response is not None
    assert blocks_response.status == 200

    # Verify the filtered block list only keeps the block with transactions.
    await expect(
        blocks_page.locator(
            f'tr[data-block-number="{seeded_explorer_data.block_with_transactions_number}"]'
        )
    ).to_have_count(1)

    # Verify the no-transaction block is excluded by the has_transactions filter.
    await expect(
        blocks_page.locator(
            f'tr[data-block-number="{seeded_explorer_data.block_without_transactions_number}"]'
        )
    ).to_have_count(0)

    # Verify the fragment exposes the list count and pagination metadata.
    await expect(
        blocks_page.get_by_text("Count: 1 / Total: 8 | limit: 10 offset: 0")
    ).to_be_visible()

    block_detail_context = await browser.new_context(
        extra_http_headers={"HX-Request": "true"}
    )
    block_detail_page = await block_detail_context.new_page()

    block_detail_response = await block_detail_page.goto(
        f"{browser_server}/blockchain_explorer/ui/block/{seeded_explorer_data.block_with_transactions_number}",
        wait_until="domcontentloaded",
    )

    assert block_detail_response is not None
    assert block_detail_response.status == 200

    # Verify the selected block detail shows the full block hash.
    await expect(
        block_detail_page.get_by_text(seeded_explorer_data.block_with_transactions_hash)
    ).to_be_visible()

    # Verify the transaction hash is truncated in the block detail view.
    await expect(
        block_detail_page.get_by_text(_truncate(seeded_explorer_data.tx_hash, 10, 8))
    ).to_be_visible()

    tx_detail_context = await browser.new_context(
        extra_http_headers={"HX-Request": "true"}
    )
    tx_detail_page = await tx_detail_context.new_page()

    tx_detail_response = await tx_detail_page.goto(
        f"{browser_server}/blockchain_explorer/ui/tx/{seeded_explorer_data.tx_hash}",
        wait_until="domcontentloaded",
    )

    assert tx_detail_response is not None
    assert tx_detail_response.status == 200

    # Verify the transaction detail page shows the truncated transaction hash in the header.
    await expect(
        tx_detail_page.get_by_text(_truncate(seeded_explorer_data.tx_hash, 14, 10))
    ).to_be_visible()

    # Verify optional contract metadata is rendered even when the transaction is not decoded.
    await expect(tx_detail_page.get_by_text("Contract")).to_be_visible()
    await expect(tx_detail_page.get_by_text("None / None")).to_be_visible()

    await tx_detail_context.close()
    await block_detail_context.close()
    await blocks_context.close()
