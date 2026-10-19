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

Measure Ethereum WST gas using the existing contract tests and a temporary Anvil.
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml
from web3 import Web3
from web3.types import RPCEndpoint

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure Ethereum WST gas using contract tests and a temporary Anvil."
    )
    parser.add_argument("--port", type=int, default=18546, help="Temporary Anvil port")
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

    # Fail before starting Anvil if this port already belongs to another service.
    with socket.socket() as port_check:
        port_check.bind(("127.0.0.1", args.port))

    rpc_url = f"http://127.0.0.1:{args.port}"
    env = dict(
        os.environ,
        WEB3_HTTP_PROVIDER=rpc_url,
        ETH_WEB3_HTTP_PROVIDER=rpc_url,
        ETH_CHAIN_ID="11111",
    )
    pytest_args = args.pytest_args
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]

    # Match tests/run_anvil_eth.sh. Both test providers use this isolated node.
    with tempfile.TemporaryFile(mode="w+") as node_log:
        node = subprocess.Popen(
            [
                anvil,
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "--chain-id",
                "11111",
                "--hardfork",
                "amsterdam",
                "--slots-in-an-epoch",
                "1",
                "--gas-price",
                "0",
                "--block-base-fee-per-gas",
                "0",
                "--gas-limit",
                "16777216",
                "--silent",
            ],
            stdout=node_log,
            stderr=node_log,
        )
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 1}))
            deadline = time.monotonic() + 10
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

            accounts = yaml.safe_load(
                (REPO_ROOT / "tests/data/account_config.yml").read_text()
            )
            for account in accounts.values():
                response = web3.provider.make_request(
                    RPCEndpoint("anvil_setBalance"),
                    [account["address"], hex(10**23)],
                )
                if "error" in response:
                    raise RuntimeError(
                        f"Failed to fund test account: {response['error']}"
                    )

            print(
                "Local Ethereum network: hardfork=amsterdam, "
                f"chain_id={web3.eth.chain_id}, "
                f"block_gas_limit={web3.eth.get_block('latest').get('gasLimit')}",
                flush=True,
            )
            return subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/app/model/wst/test_IbetWST.py",
                    "-v",
                    "-s",
                    *pytest_args,
                ],
                cwd=REPO_ROOT,
                env=env,
            ).returncode
        finally:
            node.terminate()
            try:
                node.wait(timeout=10)
            except subprocess.TimeoutExpired:
                node.kill()
                node.wait()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, RuntimeError) as error:
        print(f"WST gas measurement failed: {error}", file=sys.stderr)
        sys.exit(1)
