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

# Database
if 'pytest' in sys.modules:  # for unit test
    DATABASE_URL = os.environ.get(
        "TEST_DATABASE_URL") or 'postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb_test'
else:
    DATABASE_URL = os.environ.get("DATABASE_URL") or 'postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb'
DATABASE_SCHEMA = os.environ.get('DATABASE_SCHEMA')
DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False
DB_AUTOCOMMIT = True

# Blockchain
WEB3_HTTP_PROVIDER = os.environ.get('WEB3_HTTP_PROVIDER') or 'http://localhost:8545'
CHAIN_ID = int(os.environ.get("CHAIN_ID")) if os.environ.get("CHAIN_ID") else 2017
TX_GAS_LIMIT = int(os.environ.get("TX_GAS_LIMIT")) if os.environ.get("TX_GAS_LIMIT") else 6000000
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Token data cache
TOKEN_CACHE = False if os.environ.get("TOKEN_CACHE") == "0" else True
TOKEN_CACHE_TTL = int(os.environ.get("TOKEN_CACHE_TTL")) if os.environ.get("TOKEN_CACHE_TTL") else 43200

# Indexer sync interval
INDEXER_SYNC_INTERVAL = 10

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
    "^[a-zA-Z0-9]{8,}$"
EOA_PASSWORD_PATTERN_MSG = \
    os.environ.get("EAO_PASSWORD_PATTERN_MSG") or \
    "password is need 8 or higher length of alphanumeric characters"
PERSONAL_INFO_RSA_PASSPHRASE_PATTERN = \
    os.environ.get("PERSONAL_INFO_RSA_PASSPHRASE_PATTERN") or \
    "^[a-zA-Z0-9 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~]{8,}$"
PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG = \
    os.environ.get("PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG") or \
    "passphrase is need 8 or higher length of alphanumeric or symbolic characters"
PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE = \
    os.environ.get("PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE") or \
    "password"

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
if E2EE_RSA_RESOURCE_MODE == 1:
    AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME")  # e.g. ap-northeast-1
else:
    AWS_REGION_NAME = ""
E2EE_REQUEST_ENABLED = False if os.environ.get("E2EE_REQUEST_ENABLED") == "0" else True

# Functions by country enable
COUNTRY_FUNCTIONS = [code.strip().upper() for code in os.environ.get("COUNTRY_FUNCTIONS").split(",")] if os.environ.get(
    "COUNTRY_FUNCTIONS") else ["JPN"]
