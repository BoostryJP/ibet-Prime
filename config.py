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

import configparser
import os
import sys

SERVER_NAME = "ibet-Prime"

####################################################
# Basic settings
####################################################
# System timezone for REST API
TZ = os.environ.get("TZ") or "Asia/Tokyo"

# Default currency code
DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY") or "JPY"

# Blockchain network
NETWORK = os.environ.get("NETWORK") or "IBET"  # IBET or IBETFIN

# Environment-specific settings
APP_ENV = os.environ.get("APP_ENV") or "local"
if APP_ENV != "live":
    INI_FILE = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), f"conf/{APP_ENV}.ini"
    )
else:
    if NETWORK == "IBET":  # ibet
        INI_FILE = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "conf/live.ini"
        )
    else:  # ibet for Fin
        INI_FILE = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "conf/live_fin.ini"
        )
CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)

# Response validation mode
RESPONSE_VALIDATION_MODE = (
    True if os.environ.get("RESPONSE_VALIDATION_MODE") == "1" else False
)

# Run mode
RUN_MODE = os.environ.get("RUN_MODE")

# Profiling mode
PROFILING_MODE = True if os.environ.get("PROFILING_MODE") == "1" else False

####################################################
# Server settings
####################################################

# Database
if "pytest" in sys.modules:  # for unit test
    DATABASE_URL = (
        os.environ.get("TEST_DATABASE_URL")
        or "postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb_test"
    )
else:
    DATABASE_URL = (
        os.environ.get("DATABASE_URL")
        or "postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb"
    )
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

DATABASE_SCHEMA = os.environ.get("DATABASE_SCHEMA")
DB_ECHO = True if CONFIG["database"]["echo"] == "yes" else False

# Logging
LOG_LEVEL = CONFIG["logging"]["level"]
AUTH_LOGFILE = os.environ.get("AUTH_LOGFILE") or "/dev/stdout"
ACCESS_LOGFILE = os.environ.get("ACCESS_LOGFILE") or "/dev/stdout"


####################################################
# Blockchain monitoring settings
####################################################
# Block synchronization monitoring interval [sec]
BLOCK_SYNC_STATUS_SLEEP_INTERVAL = (
    int(os.environ.get("BLOCK_SYNC_STATUS_SLEEP_INTERVAL"))
    if os.environ.get("BLOCK_SYNC_STATUS_SLEEP_INTERVAL")
    else 3
)
# Number of monitoring data period
BLOCK_SYNC_STATUS_CALC_PERIOD = (
    int(os.environ.get("BLOCK_SYNC_STATUS_CALC_PERIOD"))
    if os.environ.get("BLOCK_SYNC_STATUS_CALC_PERIOD")
    else 3
)
# Threshold for remaining block synchronization
# - Threshold for difference between highestBlock and currentBlock
BLOCK_SYNC_REMAINING_THRESHOLD = int(
    os.environ.get("BLOCK_SYNC_REMAINING_THRESHOLD", 2)
)
# Threshold of block generation speed for judging synchronous stop [%]
if APP_ENV == "local":
    BLOCK_GENERATION_SPEED_THRESHOLD = (
        int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD"))
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")
        else 0
    )
else:
    BLOCK_GENERATION_SPEED_THRESHOLD = (
        int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD"))
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")
        else 20
    )
# Average block generation interval
EXPECTED_BLOCKS_PER_SEC = float(os.environ.get("EXPECTED_BLOCKS_PER_SEC", 0.1))

# Maximum message size for name registration for ibet PersonalInfo contract:
#   ( key bit length / 8 ) - ( 2 * hash function output length + 2 ) = 1238
#   key bit length: 10240
#   hash function output length: 20
PERSONAL_INFO_MESSAGE_SIZE_LIMIT = int((10240 / 8) - (2 * 20 + 2))


####################################################
# Web3 settings
####################################################
# Provider
WEB3_HTTP_PROVIDER = os.environ.get("WEB3_HTTP_PROVIDER") or "http://localhost:8545"
WEB3_HTTP_PROVIDER_STANDBY = (
    [node.strip() for node in os.environ.get("WEB3_HTTP_PROVIDER_STANDBY").split(",")]
    if os.environ.get("WEB3_HTTP_PROVIDER_STANDBY")
    else []
)

# Chain ID
CHAIN_ID = int(os.environ.get("CHAIN_ID")) if os.environ.get("CHAIN_ID") else 2017

# Gas limit
TX_GAS_LIMIT = (
    int(os.environ.get("TX_GAS_LIMIT")) if os.environ.get("TX_GAS_LIMIT") else 6000000
)

WEB3_REQUEST_RETRY_COUNT = (
    int(os.environ.get("WEB3_REQUEST_RETRY_COUNT"))
    if os.environ.get("WEB3_REQUEST_RETRY_COUNT")
    else 3
)
WEB3_REQUEST_WAIT_TIME = (
    int(os.environ.get("WEB3_REQUEST_WAIT_TIME"))
    if os.environ.get("WEB3_REQUEST_WAIT_TIME")
    else BLOCK_SYNC_STATUS_SLEEP_INTERVAL
)  # Same batch interval


####################################################
# Token settings
####################################################
# Default addresses
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get("TOKEN_LIST_CONTRACT_ADDRESS")
E2E_MESSAGING_CONTRACT_ADDRESS = os.environ.get("E2E_MESSAGING_CONTRACT_ADDRESS")

# Token data cache
TOKEN_CACHE = False if os.environ.get("TOKEN_CACHE") == "0" else True
TOKEN_CACHE_TTL = (
    int(os.environ.get("TOKEN_CACHE_TTL"))
    if os.environ.get("TOKEN_CACHE_TTL")
    else 43200
)
TOKEN_CACHE_TTL_JITTER = (
    int(os.environ.get("TOKEN_CACHE_TTL_JITTER"))
    if os.environ.get("TOKEN_CACHE_TTL_JITTER")
    else 21600
)

####################################################
# Batch settings
####################################################

# =============================
# Indexer
# =============================
INDEXER_SYNC_INTERVAL = 10
INDEXER_BLOCK_LOT_MAX_SIZE = (
    int(os.environ.get("INDEXER_BLOCK_LOT_MAX_SIZE"))
    if os.environ.get("INDEXER_BLOCK_LOT_MAX_SIZE")
    else 1000000
)

# =============================
# Processor
# =============================

# Bulk Tx
BULK_TX_LOT_SIZE = (
    int(os.environ.get("BULK_TX_LOT_SIZE"))
    if os.environ.get("BULK_TX_LOT_SIZE")
    else 100
)

# Bulk Transfer
BULK_TRANSFER_INTERVAL = (
    int(os.environ.get("BULK_TRANSFER_INTERVAL"))
    if os.environ.get("BULK_TRANSFER_INTERVAL")
    else 10
)
BULK_TRANSFER_WORKER_COUNT = (
    int(os.environ.get("BULK_TRANSFER_WORKER_COUNT"))
    if os.environ.get("BULK_TRANSFER_WORKER_COUNT")
    else 5
)
BULK_TRANSFER_WORKER_LOT_SIZE = (
    int(os.environ.get("BULK_TRANSFER_WORKER_LOT_SIZE"))
    if os.environ.get("BULK_TRANSFER_WORKER_LOT_SIZE")
    else 5
)

# Batch Register Personal Info
BATCH_REGISTER_PERSONAL_INFO_INTERVAL = (
    int(os.environ.get("BATCH_REGISTER_PERSONAL_INFO_INTERVAL"))
    if os.environ.get("BATCH_REGISTER_PERSONAL_INFO_INTERVAL")
    else 60
)
BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT = (
    int(os.environ.get("BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT"))
    if os.environ.get("BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT")
    else 1
)
BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE = (
    int(os.environ.get("BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE"))
    if os.environ.get("BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE")
    else 2
)

# Scheduled Events
SCHEDULED_EVENTS_INTERVAL = (
    int(os.environ.get("SCHEDULED_EVENTS_INTERVAL"))
    if os.environ.get("SCHEDULED_EVENTS_INTERVAL")
    else 60
)
SCHEDULED_EVENTS_WORKER_COUNT = (
    int(os.environ.get("SCHEDULED_EVENTS_WORKER_COUNT"))
    if os.environ.get("SCHEDULED_EVENTS_WORKER_COUNT")
    else 5
)

# Update Token
UPDATE_TOKEN_INTERVAL = (
    int(os.environ.get("UPDATE_TOKEN_INTERVAL"))
    if os.environ.get("UPDATE_TOKEN_INTERVAL")
    else 10
)

# Create UTXO
CREATE_UTXO_INTERVAL = (
    int(os.environ.get("CREATE_UTXO_INTERVAL"))
    if os.environ.get("CREATE_UTXO_INTERVAL")
    else 600
)
CREATE_UTXO_BLOCK_LOT_MAX_SIZE = (
    int(os.environ.get("CREATE_UTXO_BLOCK_LOT_MAX_SIZE"))
    if os.environ.get("CREATE_UTXO_BLOCK_LOT_MAX_SIZE")
    else 10000
)

# Rotate E2E Messaging RSA Key
ROTATE_E2E_MESSAGING_RSA_KEY_INTERVAL = (
    int(os.environ.get("ROTATE_E2E_MESSAGING_RSA_KEY_INTERVAL"))
    if os.environ.get("ROTATE_E2E_MESSAGING_RSA_KEY_INTERVAL")
    else 10
)

####################################################
# Password settings
####################################################
# NOTE:
# Set PATTERN with a regular expression.
# e.g.) ^(?=.*?[a-z])(?=.*?[A-Z])[a-zA-Z]{10,}$
#         => 10 or higher length in mixed characters with lowercase alphabetic, uppercase alphabetic
#       ^(?=.*?[a-z])(?=.*?[A-Z])(?=.*?[0-9])(?=.*?[\*\+\.\\\(\)\?\[\]\^\$\-\|!#%&"',/:;<=>@_`{}~])[a-zA-Z0-9\*\+\.\\\(\)\?\[\]\^\$\-\|!#%&"',/:;<=>@_`{}~]{12,}$
#         => 12 or higher length of mixed characters with
#            lowercase alphabetic, uppercase alphabetic, numeric, and symbolic(space exclude)
EOA_PASSWORD_PATTERN = (
    os.environ.get("EOA_PASSWORD_PATTERN")
    or r"^[a-zA-Z0-9 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~]{8,200}$"
)
EOA_PASSWORD_PATTERN_MSG = (
    os.environ.get("EOA_PASSWORD_PATTERN_MSG")
    or "password must be 8 to 200 alphanumeric or symbolic character"
)
PERSONAL_INFO_RSA_PASSPHRASE_PATTERN = (
    os.environ.get("PERSONAL_INFO_RSA_PASSPHRASE_PATTERN")
    or r"^[a-zA-Z0-9 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~]{8,200}$"
)
PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG = (
    os.environ.get("PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG")
    or "passphrase must be 8 to 200 alphanumeric or symbolic characters"
)
PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE = (
    os.environ.get("PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE") or "password"
)
E2E_MESSAGING_RSA_PASSPHRASE_PATTERN = (
    os.environ.get("E2E_MESSAGING_RSA_PASSPHRASE_PATTERN")
    or r"^[a-zA-Z0-9 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~]{8,200}$"
)
E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG = (
    os.environ.get("E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG")
    or "passphrase must be 8 to 200 alphanumeric or symbolic characters"
)
E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE = (
    os.environ.get("E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE") or "password"
)
EOA_PASSWORD_CHECK_ENABLED = (
    False if os.environ.get("EOA_PASSWORD_CHECK_ENABLED") == "0" else True
)

# End-to-End Encryption (RSA)
# NOTE:
# about E2EE_RSA_RESOURCE_MODE
# - 0:File, Set the file path to E2EE_RSA_RESOURCE.
# - 1:AWS SecretsManager, Set the SecretsManagerARN to E2EE_RSA_RESOURCE.
if "pytest" in sys.modules:  # for unit test
    E2EE_RSA_RESOURCE_MODE = (
        int(os.environ.get("E2EE_RSA_RESOURCE_MODE"))
        if os.environ.get("E2EE_RSA_RESOURCE_MODE")
        else 0
    )
    E2EE_RSA_RESOURCE = (
        os.environ.get("E2EE_RSA_RESOURCE") or "tests/data/rsa_private.pem"
    )
    E2EE_RSA_PASSPHRASE = os.environ.get("E2EE_RSA_PASSPHRASE") or "password"
elif (
    "alembic" in sys.modules or "manage.py" in sys.argv[0] or APP_ENV == "local"
):  # for migration or local
    E2EE_RSA_RESOURCE_MODE = (
        int(os.environ.get("E2EE_RSA_RESOURCE_MODE"))
        if os.environ.get("E2EE_RSA_RESOURCE_MODE")
        else 0
    )
    E2EE_RSA_RESOURCE = (
        os.environ.get("E2EE_RSA_RESOURCE") or "tests/data/rsa_private.pem"
    )
    E2EE_RSA_PASSPHRASE = os.environ.get("E2EE_RSA_PASSPHRASE") or "password"
else:
    E2EE_RSA_RESOURCE_MODE = int(os.environ.get("E2EE_RSA_RESOURCE_MODE"))
    E2EE_RSA_RESOURCE = os.environ.get("E2EE_RSA_RESOURCE")
    E2EE_RSA_PASSPHRASE = os.environ.get("E2EE_RSA_PASSPHRASE")
E2EE_REQUEST_ENABLED = False if os.environ.get("E2EE_REQUEST_ENABLED") == "0" else True


####################################################
# Settings for the "BlockchainExplorer"
####################################################
BC_EXPLORER_ENABLED = True if os.environ.get("BC_EXPLORER_ENABLED") == "1" else False


####################################################
# Settings for the "SealedTx" feature
####################################################
DEDICATED_OFFCHAIN_TX_MODE = (
    True if os.environ.get("DEDICATED_OFFCHAIN_TX_MODE") == "1" else False
)

####################################################
# Settings for the "FreezeLog" feature
####################################################
FREEZE_LOG_FEATURE_ENABLED = (
    True if os.environ.get("FREEZE_LOG_FEATURE_ENABLED") == "1" else False
)
FREEZE_LOG_CONTRACT_ADDRESS = os.environ.get("FREEZE_LOG_CONTRACT_ADDRESS")


####################################################
# Settings for the "DvP" feature
####################################################
# For paying agent
DVP_AGENT_FEATURE_ENABLED = (
    True if os.environ.get("DVP_AGENT_FEATURE_ENABLED") == "1" else False
)

# Data encryption mode
# - "aes-256-cbc"
DVP_DATA_ENCRYPTION_MODE = os.environ.get("DVP_DATA_ENCRYPTION_MODE") or None
DVP_DATA_ENCRYPTION_KEY = os.environ.get("DVP_DATA_ENCRYPTION_KEY") or None

####################################################
# Settings for the "IbetWST" feature
####################################################
IBET_WST_FEATURE_ENABLED = (
    True if os.environ.get("IBET_WST_FEATURE_ENABLED") == "1" else False
)

# IbetWST Bridge
IBET_WST_BRIDGE_INTERVAL = (
    int(os.environ.get("IBET_WST_BRIDGE_INTERVAL"))
    if os.environ.get("IBET_WST_BRIDGE_INTERVAL")
    else 10
)
IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE = (
    int(os.environ.get("IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE"))
    if os.environ.get("IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE")
    else 10000
)

######################################################
# O11y Settings
######################################################
PYROSCOPE_SERVER_URL = os.environ.get("PYROSCOPE_SERVER_URL")

####################################################
# Other settings
####################################################
# AWS Region
AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME") or "ap-northeast-1"

# Random Bytes Generator
AWS_KMS_GENERATE_RANDOM_ENABLED = (
    True if os.environ.get("AWS_KMS_GENERATE_RANDOM_ENABLED") == "1" else False
)

# File Upload
# NOTE: (Reference information) WSGI server and app used by ibet-Prime has no request body size limit.
MAX_UPLOAD_FILE_SIZE = (
    int(os.environ.get("MAX_UPLOAD_FILE_SIZE"))
    if os.environ.get("MAX_UPLOAD_FILE_SIZE")
    else 100_000_000
)
