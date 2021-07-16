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
import sys
import os
import configparser

# Global Config
SERVER_NAME = 'ibet-Prime'
APP_ENV = os.environ.get('APP_ENV') or 'local'
NETWORK = os.environ.get("NETWORK") or "IBET"  # IBET or IBETFIN

if APP_ENV != "live":
    INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"conf/{APP_ENV}.ini")
else:
    if NETWORK == "IBET":  # ibet
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"conf/live.ini")
    else:  # ibet for Fin
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"conf/live_fin.ini")
CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)

# Logging
LOG_LEVEL = CONFIG['logging']['level']
AUTH_LOGFILE = os.environ.get('AUTH_LOGFILE') or '/dev/stdout'
ACCESS_LOGFILE = os.environ.get('ACCESS_LOGFILE') or '/dev/stdout'

# Database
if 'pytest' in sys.modules:  # for unit test
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or \
                   'postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb_test'
else:
    DATABASE_URL = os.environ.get("DATABASE_URL") or \
                   'postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb'
DATABASE_SCHEMA = os.environ.get('DATABASE_SCHEMA')
DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False
DB_AUTOCOMMIT = True

# Blockchain
WEB3_HTTP_PROVIDER = os.environ.get('WEB3_HTTP_PROVIDER') or 'http://localhost:8545'
WEB3_HTTP_PROVIDER_STANDBY = [node.strip() for node in os.environ.get("WEB3_HTTP_PROVIDER_STANDBY").split(",")] \
    if os.environ.get("WEB3_HTTP_PROVIDER_STANDBY") else []
CHAIN_ID = int(os.environ.get("CHAIN_ID")) if os.environ.get("CHAIN_ID") else 2017
TX_GAS_LIMIT = int(os.environ.get("TX_GAS_LIMIT")) if os.environ.get("TX_GAS_LIMIT") else 6000000
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
TOKEN_LIST_CONTRACT_ADDRESS = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')

# Token data cache
TOKEN_CACHE = False if os.environ.get("TOKEN_CACHE") == "0" else True
TOKEN_CACHE_TTL = int(os.environ.get("TOKEN_CACHE_TTL")) if os.environ.get("TOKEN_CACHE_TTL") else 43200

# Indexer sync interval
INDEXER_SYNC_INTERVAL = 10

# AWS Region
AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME") or "ap-northeast-1"

# Password Policy
# NOTE:
# Set PATTERN with a regular expression.
# e.g.) ^(?=.*?[a-z])(?=.*?[A-Z])[a-zA-Z]{10,}$
#         => 10 or higher length in mixed characters with lowercase alphabetic, uppercase alphabetic
#       ^(?=.*?[a-z])(?=.*?[A-Z])(?=.*?[0-9])(?=.*?[\*\+\.\\\(\)\?\[\]\^\$\-\|!#%&"',/:;<=>@_`{}~])[a-zA-Z0-9\*\+\.\\\(\)\?\[\]\^\$\-\|!#%&"',/:;<=>@_`{}~]{12,}$
#         => 12 or higher length of mixed characters with
#            lowercase alphabetic, uppercase alphabetic, numeric, and symbolic(space exclude)
EOA_PASSWORD_PATTERN = \
    os.environ.get("EOA_PASSWORD_PATTERN") or \
    "^[a-zA-Z0-9]{8,20}$"
EOA_PASSWORD_PATTERN_MSG = \
    os.environ.get("EOA_PASSWORD_PATTERN_MSG") or \
    "password must be 8 to 20 alphanumeric character"
PERSONAL_INFO_RSA_PASSPHRASE_PATTERN = \
    os.environ.get("PERSONAL_INFO_RSA_PASSPHRASE_PATTERN") or \
    "^[a-zA-Z0-9 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~]{8,}$"
PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG = \
    os.environ.get("PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG") or \
    "passphrase is need 8 or higher length of alphanumeric or symbolic characters"
PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE = \
    os.environ.get("PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE") or \
    "password"
EOA_PASSWORD_CHECK_ENABLED = False if os.environ.get("EOA_PASSWORD_CHECK_ENABLED") == "0" else True

# End to End Encryption (RSA)
# NOTE:
# about E2EE_RSA_RESOURCE_MODE
# - 0:File, Set the file path to E2EE_RSA_RESOURCE.
# - 1:AWS SecretsManager, Set the SecretsManagerARN to E2EE_RSA_RESOURCE.
if "pytest" in sys.modules:  # for unit test
    E2EE_RSA_RESOURCE_MODE = int(os.environ.get("E2EE_RSA_RESOURCE_MODE")) \
        if os.environ.get("E2EE_RSA_RESOURCE_MODE") else 0
    E2EE_RSA_RESOURCE = os.environ.get("E2EE_RSA_RESOURCE") or "tests/data/rsa_private.pem"
    E2EE_RSA_PASSPHRASE = os.environ.get("E2EE_RSA_PASSPHRASE") or "password"
elif "alembic" in sys.modules or "manage.py" in sys.argv[0]:  # for migration
    E2EE_RSA_RESOURCE_MODE = int(os.environ.get("E2EE_RSA_RESOURCE_MODE")) \
        if os.environ.get("E2EE_RSA_RESOURCE_MODE") else 0
    E2EE_RSA_RESOURCE = os.environ.get("E2EE_RSA_RESOURCE") or "tests/data/rsa_private.pem"
    E2EE_RSA_PASSPHRASE = os.environ.get("E2EE_RSA_PASSPHRASE") or "password"
else:
    E2EE_RSA_RESOURCE_MODE = int(os.environ.get("E2EE_RSA_RESOURCE_MODE"))
    E2EE_RSA_RESOURCE = os.environ.get("E2EE_RSA_RESOURCE")
    E2EE_RSA_PASSPHRASE = os.environ.get("E2EE_RSA_PASSPHRASE")
E2EE_REQUEST_ENABLED = False if os.environ.get("E2EE_REQUEST_ENABLED") == "0" else True

# Bulk Transfer
BULK_TRANSFER_INTERVAL = int(os.environ.get("BULK_TRANSFER_INTERVAL")) \
    if os.environ.get("BULK_TRANSFER_INTERVAL") else 10
BULK_TRANSFER_WORKER_COUNT = int(os.environ.get("BULK_TRANSFER_WORKER_COUNT")) \
    if os.environ.get("BULK_TRANSFER_WORKER_COUNT") else 5
BULK_TRANSFER_WORKER_LOT_SIZE = int(os.environ.get("BULK_TRANSFER_WORKER_LOT_SIZE")) \
    if os.environ.get("BULK_TRANSFER_WORKER_LOT_SIZE") else 5

# System locale
SYSTEM_LOCALE = [code.strip().upper() for code in os.environ.get("SYSTEM_LOCALE").split(",")] \
    if os.environ.get("SYSTEM_LOCALE") else ["JPN"]

# System timezone for REST API
TZ = os.environ.get("TZ") or "Asia/Tokyo"

# Scheduled Events
SCHEDULED_EVENTS_INTERVAL = int(os.environ.get("SCHEDULED_EVENTS_INTERVAL")) \
    if os.environ.get("SCHEDULED_EVENTS_INTERVAL") else 60

# Update Token
UPDATE_TOKEN_INTERVAL = int(os.environ.get("UPDATE_TOKEN_INTERVAL")) \
    if os.environ.get("UPDATE_TOKEN_INTERVAL") else 10

# Block Sync Monitor
# monitoring interval(second)
BLOCK_SYNC_STATUS_SLEEP_INTERVAL = int(os.environ.get("BLOCK_SYNC_STATUS_SLEEP_INTERVAL")) \
    if os.environ.get("BLOCK_SYNC_STATUS_SLEEP_INTERVAL") else 3
# number of monitoring data period
BLOCK_SYNC_STATUS_CALC_PERIOD = int(os.environ.get("BLOCK_SYNC_STATUS_CALC_PERIOD")) \
    if os.environ.get("BLOCK_SYNC_STATUS_CALC_PERIOD") else 3
# Threshold of block generation speed for judging synchronous stop(%)
if APP_ENV == "local":
    BLOCK_GENERATION_SPEED_THRESHOLD = int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")) \
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD") else 0
else:
    BLOCK_GENERATION_SPEED_THRESHOLD = int(os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD")) \
        if os.environ.get("BLOCK_GENERATION_SPEED_THRESHOLD") else 20
# auto transfer approval interval(second)
AUTO_TRANSFER_APPROVAL_INTERVAL = int(os.environ.get("AUTO_TRANSFER_APPROVAL_INTERVAL")) \
    if os.environ.get("AUTO_TRANSFER_APPROVAL_INTERVAL") else 10

# Random Bytes Generator
AWS_KMS_GENERATE_RANDOM_ENABLED = True if os.environ.get("AWS_KMS_GENERATE_RANDOM_ENABLED") == "1" else False

# Create UTXO
CREATE_UTXO_INTERVAL = int(os.environ.get("CREATE_UTXO_INTERVAL")) \
    if os.environ.get("CREATE_UTXO_INTERVAL") else 10
CREATE_UTXO_BLOCK_LOT_MAX_SIZE = int(os.environ.get("CREATE_UTXO_BLOCK_LOT_MAX_SIZE")) \
    if os.environ.get("CREATE_UTXO_BLOCK_LOT_MAX_SIZE") else 10000
