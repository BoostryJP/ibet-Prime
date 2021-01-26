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
SERVER_NAME = 'ibet-Issuer'
APP_ENV = os.environ.get('APP_ENV') or 'local'
NETWORK = os.environ.get("NETWORK") or "IBET"  # IBET or IBETFIN

if APP_ENV != "live":
    INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/{APP_ENV}.ini")
else:
    if NETWORK == "IBET":  # ibet
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/live.ini")
    else:  # ibet for Fin
        INI_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../conf/live_fin.ini")
CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)

# Database
if 'pytest' in sys.modules:  # for unit test
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or 'postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb_test'
else:
    DATABASE_URL = os.environ.get("DATABASE_URL") or 'postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb'
DB_ECHO = True if CONFIG['database']['echo'] == 'yes' else False
DB_AUTOCOMMIT = True

# Key File Password
KEY_FILE_PASSWORD = os.environ.get("KEY_FILE_PASSWORD") or "password"
