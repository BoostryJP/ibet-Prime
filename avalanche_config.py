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

import os
from typing import Any, cast

import boto3  # type: ignore[import-untyped]

from config import APP_ENV, AWS_REGION_NAME

####################################################
# Basic settings
####################################################

# Master account address for Avalanche transactions
AVA_MASTER_ACCOUNT_ADDRESS = os.environ.get("AVA_MASTER_ACCOUNT_ADDRESS")

# Resource type for the master account's private key
# - "os_environ": Environment variable
# - "aws_secrets_manager": AWS Secrets Manager
AVA_MASTER_PRIVATE_KEY_RESOURCE = os.environ.get(
    "AVA_MASTER_PRIVATE_KEY_RESOURCE", "os_environ"
)


# Hex encoded private key of the master account
def _load_ava_master_private_key() -> str | None:
    secret_id = os.environ.get("AVA_MASTER_PRIVATE_KEY")
    if AVA_MASTER_PRIVATE_KEY_RESOURCE != "aws_secrets_manager":
        return secret_id
    if secret_id is None:
        return None

    client: Any = boto3.client(  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        "secretsmanager", region_name=AWS_REGION_NAME
    )
    secret_value: Any = client.get_secret_value(  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        SecretId=secret_id
    )
    return cast(str | None, secret_value.get("SecretString"))  # pyright: ignore[reportUnknownMemberType]


AVA_MASTER_PRIVATE_KEY: str | None = _load_ava_master_private_key()

# Avalanche configuration settings for a blockchain application

_ava_chain_id = os.environ.get("AVA_CHAIN_ID")
AVA_CHAIN_ID = int(_ava_chain_id) if _ava_chain_id is not None else 22222


####################################################
# Avalanche node settings
####################################################

# Avalanche C-Chain settings
AVA_WEB3_HTTP_PROVIDER = (
    os.environ.get("AVA_WEB3_HTTP_PROVIDER") or "http://localhost:8547"
)
_ava_web3_http_provider_standby = os.environ.get("AVA_WEB3_HTTP_PROVIDER_STANDBY")
AVA_WEB3_HTTP_PROVIDER_STANDBY = (
    [node.strip() for node in _ava_web3_http_provider_standby.split(",")]
    if _ava_web3_http_provider_standby
    else []
)
AVA_WEB3_REQUEST_RETRY_COUNT = 3
AVA_WEB3_REQUEST_WAIT_TIME = 3


####################################################
# Block synchronization monitoring settings
####################################################

# Number of monitoring data period
BLOCK_SYNC_STATUS_CALC_PERIOD = 3

# Threshold for remaining block synchronization
# - Threshold for difference between highestBlock and currentBlock
BLOCK_SYNC_REMAINING_THRESHOLD = 2

# Expected number of blocks generated per minute
EXPECTED_BLOCK_GENERATION_PER_MIN = 5.0

# Threshold for block generation speed to determine synchronization halt [rate]
BLOCK_GENERATION_SPEED_THRESHOLD = 0.0 if APP_ENV == "local" else 0.2
