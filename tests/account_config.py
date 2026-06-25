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

import json
from typing import Any, cast

import yaml
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import config
from tests.types import RawUnitTestAccount, UnitTestAccount

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


# Account Address(from local config)
def default_eth_account(name: str) -> UnitTestAccount:
    with open("tests/data/account_config.yml", "r") as fp:
        account_config = cast(dict[str, RawUnitTestAccount], yaml.safe_load(fp))
    raw_account = account_config[name]
    return {
        "address": raw_account["address"],
        "private_key": raw_account["private_key"],
        "password": raw_account["password"],
        "keyfile_json": cast(dict[str, Any], json.loads(raw_account["keyfile_json"])),
        "rsa_private_key": raw_account["rsa_private_key"],
        "rsa_public_key": raw_account["rsa_public_key"],
    }
