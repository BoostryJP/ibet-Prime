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

Measure Ethereum WST gas on a local Amsterdam fork using existing contract tests.

"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from pathlib import Path

import yaml
from hexbytes import HexBytes
from web3 import Web3
from web3.types import RPCEndpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
# Leave room for state-heavy deployments when measuring Amsterdam gas costs.
BLOCK_GAS_LIMIT = 60_000_000


@contextmanager
def start_anvil(
    anvil: str, port: int, hardfork: str, *extra: str
) -> Generator[tuple[Web3, str]]:
    # Reject occupied ports before starting or funding a node.
    with socket.socket() as port_check:
        port_check.bind(("127.0.0.1", port))
        actual_port = port_check.getsockname()[1]
    rpc_url = f"http://127.0.0.1:{actual_port}"
    with tempfile.TemporaryFile(mode="w+") as node_log:
        node = subprocess.Popen(
            [
                anvil,
                "--host",
                "127.0.0.1",
                "--port",
                str(actual_port),
                "--chain-id",
                "11111",
                "--hardfork",
                hardfork,
                "--slots-in-an-epoch",
                "1",
                "--gas-price",
                "0",
                "--block-base-fee-per-gas",
                "0",
                "--gas-limit",
                str(BLOCK_GAS_LIMIT),
                "--silent",
                *extra,
            ],
            stdout=node_log,
            stderr=node_log,
        )
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 2}))
            deadline = time.monotonic() + 15
            while True:
                if node.poll() is not None:
                    node_log.seek(0)
                    raise RuntimeError(
                        f"Anvil exited during startup: {node_log.read()}"
                    )
                if web3.is_connected():
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("Timed out waiting for Anvil to start")
                time.sleep(0.1)
            yield web3, rpc_url
        finally:
            node.terminate()
            try:
                node.wait(timeout=10)
            except subprocess.TimeoutExpired:
                node.kill()
                node.wait()


def check_amsterdam_pricing(web3: Web3) -> None:
    """Verify EIP-8037 charges with a small deployment and storage write."""
    snapshot = web3.provider.make_request(RPCEndpoint("evm_snapshot"), [])
    if "result" not in snapshot:
        raise RuntimeError(f"Cannot snapshot pricing probe: {snapshot}")
    try:
        sender = web3.eth.accounts[0]
        # The 12-byte init code returns the following 6-byte runtime:
        # PUSH1 1; PUSH1 0; SSTORE; STOP. Its first call writes 1 to a new slot 0.
        creation = HexBytes("0x6006600c60003960066000f3600160005500")
        deployed = web3.eth.wait_for_transaction_receipt(
            web3.eth.send_transaction(
                {"from": sender, "data": creation, "gas": 1_000_000}
            )
        )
        address = deployed.get("contractAddress")
        if deployed.get("status") != 1 or address is None:
            raise RuntimeError("Amsterdam pricing probe deployment failed")
        stored = web3.eth.wait_for_transaction_receipt(
            web3.eth.send_transaction({"from": sender, "to": address, "gas": 1_000_000})
        )
        creation_gas = deployed["gasUsed"]
        storage_gas = stored["gasUsed"]
        # EIP-8037: new account = 120 * 1530; new storage slot = 64 * 1530.
        # These are minimum charges; gasUsed also includes execution costs.
        if (
            stored.get("status") != 1
            or int.from_bytes(web3.eth.get_storage_at(address, 0)) != 1
            or creation_gas < 183_600
            or storage_gas < 97_920
        ):
            raise RuntimeError(
                "Amsterdam state-gas pricing is not active: "
                f"creation gas={creation_gas}, new-slot gas={storage_gas}. "
                "Refusing to report underestimated WST gas usage."
            )
        print(
            f"Amsterdam pricing verified: creation gas={creation_gas}, "
            f"new-slot gas={storage_gas}",
            flush=True,
        )
    finally:
        # Restore balances, nonces and contract state before the WST tests run.
        reverted = web3.provider.make_request(
            RPCEndpoint("evm_revert"), [snapshot["result"]]
        )
        if reverted.get("result") is not True:
            raise RuntimeError(f"Cannot revert pricing probe: {reverted}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure Ethereum WST gas on an isolated Amsterdam fork."
    )
    parser.add_argument(
        "--port", type=int, default=18546, help="Temporary fork node port"
    )
    parser.add_argument(
        "pytest_args", nargs=argparse.REMAINDER, help="Extra pytest options after --"
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    anvil = shutil.which("anvil")
    if anvil is None:
        parser.error(
            "anvil is required; install Foundry and add its bin directory to PATH"
        )
    pytest_args = args.pytest_args
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]

    with ExitStack() as stack:
        # Anvil v1.8.5 needs fork startup to initialize Amsterdam gas pricing.
        # Use a local source; its hardfork does not affect the measurement rules.
        _, source_rpc = stack.enter_context(start_anvil(anvil, 0, "osaka"))
        web3, rpc_url = stack.enter_context(
            start_anvil(
                anvil,
                args.port,
                "amsterdam",
                "--fork-url",
                source_rpc,
            )
        )
        check_amsterdam_pricing(web3)
        accounts = yaml.safe_load(
            (REPO_ROOT / "tests/data/account_config.yml").read_text()
        )
        for account in accounts.values():
            response = web3.provider.make_request(
                RPCEndpoint("anvil_setBalance"), [account["address"], hex(10**23)]
            )
            if "error" in response:
                raise RuntimeError(f"Failed to fund test account: {response['error']}")
        env = dict(
            os.environ,
            WEB3_HTTP_PROVIDER=rpc_url,
            ETH_WEB3_HTTP_PROVIDER=rpc_url,
            ETH_CHAIN_ID="11111",
        )
        print(
            "Local Ethereum fork: hardfork=amsterdam, "
            f"chain_id={web3.eth.chain_id}, "
            f"block_gas_limit={web3.eth.get_block('latest').get('gasLimit')}",
            flush=True,
        )
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "tests.helpers.wst_gas_measurement",
                "tests/app/model/wst/test_IbetWST.py",
                "-v",
                "-s",
                *pytest_args,
            ],
            cwd=REPO_ROOT,
            env=env,
        ).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, RuntimeError) as error:
        print(f"WST gas measurement failed: {error}", file=sys.stderr)
        sys.exit(1)
