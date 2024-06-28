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

import logging
import sys
import urllib
from datetime import UTC, datetime

from fastapi import Request, Response

from config import ACCESS_LOGFILE, APP_ENV, AUTH_LOGFILE, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL)
LOG = logging.getLogger("issuer_api")
LOG.propagate = False
AUTH_LOG = logging.getLogger("issuer_api_auth")
AUTH_LOG.propagate = False
ACCESS_LOG = logging.getLogger("issuer_api_access")
ACCESS_LOG.propagate = False

logging.getLogger("web3.manager.RequestManager").propagate = False
logging.getLogger("web3.manager.RequestManager").addHandler(logging.NullHandler())

INFO_FORMAT = "[%(asctime)s] {}[%(process)d] [%(levelname)s] %(message)s"
DEBUG_FORMAT = "[%(asctime)s] {}[%(process)d] [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"
# NOTE:
# If 'X-Forwarded-For' is set for headers, that will be set prioritized to client ip.
# [client ip] [account address] message
AUTH_FORMAT = "[%s] [%s] %s"
ACCESS_FORMAT = '"%s %s HTTP/%s" %d (%.6fsec)'

if APP_ENV == "live":
    # App Log
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(INFO_FORMAT.format(""), TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

    # Auth Log
    stream_handler_auth = logging.StreamHandler(open(AUTH_LOGFILE, "a"))
    formatter_auth = logging.Formatter(
        INFO_FORMAT.format("[AUTH-LOG] "), TIMESTAMP_FORMAT
    )
    stream_handler_auth.setFormatter(formatter_auth)
    AUTH_LOG.addHandler(stream_handler_auth)

    # Access Log
    stream_handler_access = logging.StreamHandler(open(ACCESS_LOGFILE, "a"))
    formatter_access = logging.Formatter(
        INFO_FORMAT.format("[ACCESS-LOG] "), TIMESTAMP_FORMAT
    )
    stream_handler_access.setFormatter(formatter_access)
    ACCESS_LOG.addHandler(stream_handler_access)

if APP_ENV == "dev" or APP_ENV == "local":
    # App Log
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(DEBUG_FORMAT.format(""), TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

    # Auth Log
    stream_handler_auth = logging.StreamHandler(open(AUTH_LOGFILE, "a"))
    formatter_auth = logging.Formatter(
        DEBUG_FORMAT.format("[AUTH-LOG] "), TIMESTAMP_FORMAT
    )
    stream_handler_auth.setFormatter(formatter_auth)
    AUTH_LOG.addHandler(stream_handler_auth)

    # Access Log
    stream_handler_access = logging.StreamHandler(open(ACCESS_LOGFILE, "a"))
    formatter_access = logging.Formatter(
        INFO_FORMAT.format("[ACCESS-LOG] "), TIMESTAMP_FORMAT
    )  # Same live's formatter
    stream_handler_access.setFormatter(formatter_access)
    ACCESS_LOG.addHandler(stream_handler_access)


def get_logger():
    return LOG


def auth_info(req: Request, address: str, msg: str):
    AUTH_LOG.info(__auth_format(req, address, msg))


def auth_error(req: Request, address: str, msg: str):
    AUTH_LOG.warning(__auth_format(req, address, msg))


def output_access_log(req: Request, res: Response, request_start_time: datetime):
    url = __get_url(req)
    if url != "/":
        method = req.scope.get("method", "")
        http_version = req.scope.get("http_version", "")
        status_code = res.status_code
        response_time = (
            datetime.now(UTC).replace(tzinfo=None) - request_start_time
        ).total_seconds()
        access_msg = ACCESS_FORMAT % (
            method,
            url,
            http_version,
            status_code,
            response_time,
        )

        address = "None"  # Initial value
        headers = req.scope.get("headers", [])
        for header in headers:
            key_bytes, value_bytes = header
            if "issuer-address" == key_bytes.decode():
                address = value_bytes.decode()

        msg = __auth_format(req, address, access_msg)
        ACCESS_LOG.info(msg)


def __auth_format(req: Request, address: str, msg: str):
    if req.client is None:
        _host = ""
    else:
        _host = req.client.host
    return AUTH_FORMAT % (_host, address, msg)


def __get_url(req: Request):
    scope = req.scope
    url = urllib.parse.quote(scope.get("root_path", "") + scope.get("path", ""))
    if scope.get("query_string", None):
        url = "{}?{}".format(url, scope["query_string"].decode("ascii"))
    return url
