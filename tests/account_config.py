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

import yaml
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


# Account Address(from local config)
def config_eth_account(name):
    account_config = yaml.safe_load(open(f"tests/data/account_config.yml", "r"))
    account_config[name]["keyfile_json"] = json.loads(
        account_config[name]["keyfile_json"]
    )
    return account_config[name]
