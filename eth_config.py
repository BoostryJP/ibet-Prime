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

from config import APP_ENV

####################################################
# Basic settings
####################################################

# Master account address for Ethereum transactions
ETH_MASTER_ACCOUNT_ADDRESS = os.environ.get("ETH_MASTER_ACCOUNT_ADDRESS")

# Hex encoded private key of the master account
ETH_MASTER_PRIVATE_KEY = os.environ.get("ETH_MASTER_PRIVATE_KEY")

# Ethereum configuration settings for a blockchain application
ETH_CHAIN_ID = os.environ.get("ETH_CHAIN_ID") or 2025

####################################################
# Ethereum node settings
####################################################

# Provider for Ethereum Web3 HTTP requests
ETH_WEB3_HTTP_PROVIDER = (
    os.environ.get("ETH_WEB3_HTTP_PROVIDER") or "http://localhost:8546"
)
ETH_WEB3_HTTP_PROVIDER_STANDBY = (
    [
        node.strip()
        for node in os.environ.get("ETH_WEB3_HTTP_PROVIDER_STANDBY").split(",")
    ]
    if os.environ.get("ETH_WEB3_HTTP_PROVIDER_STANDBY")
    else []
)
ETH_WEB3_REQUEST_RETRY_COUNT = 3
ETH_WEB3_REQUEST_WAIT_TIME = 3


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
if APP_ENV == "local":
    BLOCK_GENERATION_SPEED_THRESHOLD = 0.0
else:
    BLOCK_GENERATION_SPEED_THRESHOLD = 0.2
