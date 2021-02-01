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

from config import LOG_LEVEL, APP_ENV

logging.basicConfig(level=LOG_LEVEL)
LOG = logging.getLogger("issuer_api")
LOG.propagate = False

INFO_FORMAT = "[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s"
DEBUG_FORMAT = "[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"

if APP_ENV == "live":
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(INFO_FORMAT, TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

if APP_ENV == "dev" or APP_ENV == "local":
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(DEBUG_FORMAT, TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)


def get_logger():
    return LOG
