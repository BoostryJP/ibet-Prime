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
import pytest

from pydantic.error_wrappers import ValidationError
from eth_keyfile import decode_keyfile_json

from app.model.blockchain import IbetShareContract
from app.model.schema import IbetShareAdd
from app.exceptions import SendTransactionError

from tests.account_config import config_eth_account


class TestAddSupply:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            1, "20211231", "20211231",
            "20221231"
        ]
        contract_address, abi, tx_hash = IbetShareContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # add supply
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = IbetShareAdd(**_data)
        IbetShareContract.add_supply(
            contract_address=contract_address,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract = IbetShareContract.get(contract_address=contract_address)
        assert share_contract.total_supply == arguments[3] + 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid parameter (IbetShareAdd)
    def test_error_1(self):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        _data = {}
        with pytest.raises(ValidationError):
            IbetShareAdd(**_data)

        _data = {
            "account_address": issuer_address[:-1],  # short address
            "amount": 1
        }
        with pytest.raises(ValidationError):
            IbetShareAdd(**_data)

        _data = {
            "account_address": issuer_address,
            "amount": -1  # short address
        }
        with pytest.raises(ValidationError):
            IbetShareAdd(**_data)

    # <Error_2>
    # invalid private key
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            1, "20211231", "20211231",
            "20221231"
        ]
        contract_address, abi, tx_hash = IbetShareContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # add supply
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = IbetShareAdd(**_data)
        with pytest.raises(SendTransactionError):
            IbetShareContract.add_supply(
                contract_address=contract_address,
                data=_add_data,
                tx_from=test_account.get("address"),
                private_key="invalid_private_key"
            )
