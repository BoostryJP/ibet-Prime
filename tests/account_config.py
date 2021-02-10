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

from web3 import Web3
from web3.middleware import geth_poa_middleware
import yaml

import config

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Account Address(from Ethereum)
eth_account = {
    'deployer': {
        'account_address': web3.eth.accounts[0],
        'password': 'password'
    },
    'issuer': {
        'account_address': web3.eth.accounts[1],
        'password': 'password'
    },
    'agent': {
        'account_address': web3.eth.accounts[2],
        'password': 'password'
    },
    'trader': {
        'account_address': web3.eth.accounts[3],
        'password': 'password'
    },
    'deployer2': {
        'account_address': web3.eth.accounts[4],
        'password': 'password'
    },
    'issuer2': {
        'account_address': web3.eth.accounts[5],
        'password': 'password'
    },
    'agent2': {
        'account_address': web3.eth.accounts[6],
        'password': 'password'
    },
    'trader2': {
        'account_address': web3.eth.accounts[7],
        'password': 'password'
    }
}


# Account Address(from local config)
def config_eth_account(name):
    account_config = yaml.safe_load(open(f"tests/account_config.yml", "r"))
    account_config[name]["keyfile_json"] = json.loads(account_config[name]["keyfile_json"])
    return account_config[name]
