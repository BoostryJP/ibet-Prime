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

Pytest plugin enabled only by tests/measure_wst_gas.py.

Measure successful transactions independently of application gas limits. Gas limits
are raised only on the isolated measurement node; application code is unchanged.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from _pytest.terminal import TerminalReporter
from eth_utils.abi import function_abi_to_4byte_selector
from hexbytes import HexBytes
from web3.exceptions import ContractLogicError, Web3RPCError
from web3.types import Nonce, TxParams

from app.utils.eth_contract_utils import EthAsyncContractUtils, EthWeb3


@dataclass
class GasMeasurement:
    operation: str
    estimate: int
    configured_limit: int
    gas_used: int

    @property
    def exceeds_limit(self) -> bool:
        return max(self.estimate, self.gas_used) > self.configured_limit


measurements: list[GasMeasurement] = []


@pytest.fixture(scope="session", autouse=True)
def measure_wst_transactions() -> Iterator[None]:
    measurements.clear()
    artifacts = Path(__file__).resolve().parents[2] / "contracts/wst"
    selectors: dict[bytes, str] = {}
    constructors: list[tuple[bytes, str]] = []
    for path in sorted(artifacts.glob("*.json")):
        artifact = json.loads(path.read_text())
        if artifact.get("bytecode"):
            constructors.append((HexBytes(artifact["bytecode"]), path.stem))
        for entry in artifact.get("abi", []):
            if entry.get("type") == "function":
                selectors[function_abi_to_4byte_selector(entry)] = entry["name"]

    original_send = EthAsyncContractUtils.send_transaction

    async def send_with_measurement(
        transaction: TxParams, private_key: bytes
    ) -> tuple[str, Nonce]:
        data = HexBytes(transaction.get("data", b""))
        if not transaction.get("to"):
            operation = next(
                (
                    f"deploy({name})"
                    for code, name in constructors
                    if data.startswith(code)
                ),
                "deploy",
            )
        else:
            operation = selectors.get(data[:4], data[:4].to_0x_hex())
        configured_limit = transaction.get("gas")
        if configured_limit is None:
            raise RuntimeError(f"Missing configured gas limit for {operation}")

        block_limit = (await EthWeb3.eth.get_block("latest")).get("gasLimit")
        if block_limit is None:
            raise RuntimeError("Measurement block has no gas limit")
        estimated_tx = cast(TxParams, dict(transaction))
        estimated_tx["gas"] = block_limit
        try:
            estimate = await EthWeb3.eth.estimate_gas(estimated_tx)
        except (ContractLogicError, Web3RPCError) as error:
            # Error cases deliberately submit invalid authorizations, etc. Keep
            # their original execution and assertions instead of hiding reverts.
            print(f"\n{operation}: estimate unavailable ({type(error).__name__})")
            return await original_send(transaction, private_key)

        measured_tx = cast(TxParams, dict(transaction))
        measured_tx["gas"] = max(configured_limit, (estimate * 130 + 99) // 100)
        if measured_tx["gas"] > block_limit:
            raise RuntimeError(
                f"Measurement gas budget exceeds block limit: {operation}"
            )
        tx_hash, nonce = await original_send(measured_tx, private_key)
        receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        if receipt.get("status") != 1:
            raise RuntimeError(
                f"Estimated transaction failed during measurement: {operation}"
            )
        row = GasMeasurement(operation, estimate, configured_limit, receipt["gasUsed"])
        measurements.append(row)
        verdict = "EXCEEDS CONFIGURED LIMIT" if row.exceeds_limit else "within limit"
        print(
            f"\n{operation}: estimate={estimate}, gasUsed={row.gas_used}, "
            f"configured_limit={configured_limit}, measurement_limit={measured_tx['gas']} "
            f"[{verdict}]"
        )
        return tx_hash, nonce

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            EthAsyncContractUtils,
            "send_transaction",
            staticmethod(send_with_measurement),
        )
        yield


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # A passing contract test with raised measurement limits does not establish
    # that the configured application limits are sufficient.
    if exitstatus == pytest.ExitCode.OK and any(
        row.exceeds_limit for row in measurements
    ):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter: TerminalReporter) -> None:
    terminalreporter.write_sep(
        "=", "WST gas measurements (local execution limits raised)"
    )
    grouped: dict[tuple[str, int], list[GasMeasurement]] = {}
    for row in measurements:
        grouped.setdefault((row.operation, row.configured_limit), []).append(row)
    terminalreporter.write_line(
        "Operation | Max estimate | Max gasUsed | Configured limit | Result"
    )
    for (operation, configured), rows in sorted(grouped.items()):
        estimate = max(row.estimate for row in rows)
        used = max(row.gas_used for row in rows)
        verdict = "EXCEEDS" if any(row.exceeds_limit for row in rows) else "OK"
        terminalreporter.write_line(
            f"{operation} | {estimate:,} | {used:,} | {configured:,} | {verdict}"
        )
    if any(row.exceeds_limit for row in measurements):
        terminalreporter.write_line(
            "An estimate or gasUsed exceeds its configured limit. Measurement exits with status 1 "
            "even if the contract tests pass."
        )
