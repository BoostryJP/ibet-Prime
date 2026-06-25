"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast
from unittest import mock

from hexbytes import HexBytes
from web3.eth.async_eth import AsyncEth
from web3.eth.eth import Eth
from web3.types import RPCEndpoint


@contextmanager
def install_anvil_transaction_sync_patch(_: Any = None) -> Generator[None, None, None]:
    """Route transaction sending through Anvil's synchronous RPC during tests."""

    transaction_receipt_cache: dict[HexBytes, Any] = {}
    original_sync_get_transaction_receipt = Eth.get_transaction_receipt
    original_async_get_transaction_receipt = AsyncEth.get_transaction_receipt

    def _cache_receipt(receipt: Any) -> HexBytes:
        transaction_hash = HexBytes(receipt["transactionHash"])
        transaction_receipt_cache[transaction_hash] = receipt
        return transaction_hash

    def _get_cached_receipt(transaction_hash: Any) -> Any:
        cached_receipt = transaction_receipt_cache.get(HexBytes(transaction_hash))
        if cached_receipt is not None:
            return cached_receipt
        return None

    def _send_transaction_via_sync_api(self: Eth, transaction: Any) -> HexBytes:
        transaction_params = self.send_transaction_munger(transaction)[0]
        receipt = self.w3.manager.request_blocking(
            cast(RPCEndpoint, "eth_sendTransactionSync"), [transaction_params]
        )
        return _cache_receipt(receipt)

    def _send_raw_transaction_via_sync_api(self: Eth, transaction: Any) -> HexBytes:
        receipt = self.w3.manager.request_blocking(
            cast(RPCEndpoint, "eth_sendRawTransactionSync"), [transaction]
        )
        return _cache_receipt(receipt)

    async def _async_send_transaction_via_sync_api(
        self: AsyncEth, transaction: Any
    ) -> HexBytes:
        transaction_params = self.send_transaction_munger(transaction)[0]
        receipt = await self.w3.manager.coro_request(
            cast(RPCEndpoint, "eth_sendTransactionSync"), [transaction_params]
        )
        return _cache_receipt(receipt)

    async def _async_send_raw_transaction_via_sync_api(
        self: AsyncEth, transaction: Any
    ) -> HexBytes:
        receipt = await self.w3.manager.coro_request(
            cast(RPCEndpoint, "eth_sendRawTransactionSync"), [transaction]
        )
        return _cache_receipt(receipt)

    def _get_transaction_receipt_with_cache(self: Eth, transaction_hash: Any) -> Any:
        cached_receipt = _get_cached_receipt(transaction_hash)
        if cached_receipt is not None:
            return cached_receipt
        return original_sync_get_transaction_receipt(self, transaction_hash)

    async def _async_get_transaction_receipt_with_cache(
        self: AsyncEth, transaction_hash: Any
    ) -> Any:
        cached_receipt = _get_cached_receipt(transaction_hash)
        if cached_receipt is not None:
            return cached_receipt
        return await original_async_get_transaction_receipt(self, transaction_hash)

    with (
        mock.patch.object(
            Eth,
            "send_transaction",
            _send_transaction_via_sync_api,
        ),
        mock.patch.object(
            Eth,
            "send_raw_transaction",
            _send_raw_transaction_via_sync_api,
        ),
        mock.patch.object(
            Eth,
            "get_transaction_receipt",
            _get_transaction_receipt_with_cache,
        ),
        mock.patch.object(
            AsyncEth,
            "send_transaction",
            _async_send_transaction_via_sync_api,
        ),
        mock.patch.object(
            AsyncEth,
            "send_raw_transaction",
            _async_send_raw_transaction_via_sync_api,
        ),
        mock.patch.object(
            AsyncEth,
            "get_transaction_receipt",
            _async_get_transaction_receipt_with_cache,
        ),
    ):
        yield
