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
import logging

from fastapi import Request

from config import (
    LOG_LEVEL,
    APP_ENV,
    AUTH_LOGFILE
)

logging.basicConfig(level=LOG_LEVEL)
LOG = logging.getLogger("issuer_api")
LOG.propagate = False
AUTH_LOG = logging.getLogger("issuer_api_auth")
AUTH_LOG.propagate = False

INFO_FORMAT = "[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s"
DEBUG_FORMAT = "[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"
# NOTE:
# If 'X-Forwarded-For' is set for headers, that will be set prioritized to client ip.
# [client ip] [account address] message
AUTH_FORMAT = "[%s] [%s] %s"

if APP_ENV == "live":
    # App Log
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(INFO_FORMAT, TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

    # Auth Log
    stream_handler_auth = logging.StreamHandler(open(AUTH_LOGFILE, "a"))
    formatter_auth = logging.Formatter(INFO_FORMAT, TIMESTAMP_FORMAT)
    stream_handler_auth.setFormatter(formatter_auth)
    AUTH_LOG.addHandler(stream_handler_auth)

if APP_ENV == "dev" or APP_ENV == "local":
    # App Log
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(DEBUG_FORMAT, TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

    # Auth Log
    stream_handler_auth = logging.StreamHandler(open(AUTH_LOGFILE, "a"))
    formatter_auth = logging.Formatter(DEBUG_FORMAT, TIMESTAMP_FORMAT)
    stream_handler_auth.setFormatter(formatter_auth)
    AUTH_LOG.addHandler(stream_handler_auth)


def get_logger():
    return LOG


def auth_info(req: Request, address: str, msg: str):
    AUTH_LOG.info(__auth_format(req, address, msg))


def auth_error(req: Request, address: str, msg: str):
    AUTH_LOG.error(__auth_format(req, address, msg))


def __auth_format(req: Request, address: str, msg: str):
    return AUTH_FORMAT % (req.client.host, address, msg)
