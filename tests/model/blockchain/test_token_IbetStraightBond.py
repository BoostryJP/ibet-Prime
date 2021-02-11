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

from eth_keyfile import decode_keyfile_json

from config import ZERO_ADDRESS
from app.model.blockchain import IbetStraightBondContract
from app.model.blockchain.utils import ContractUtils
from app.exceptions import SendTransactionError

from tests.account_config import config_eth_account


class TestCreate:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            "20211231", 30000,
            "20211231", "リターン内容",
            "発行目的"
        ]

        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        bond_contract = ContractUtils.get_contract(
            contract_name="IbetStraightBond",
            contract_address=contract_address
        )
        assert bond_contract.functions.owner().call() == issuer_address
        assert bond_contract.functions.name().call() == "テスト債券"
        assert bond_contract.functions.symbol().call() == "TEST"
        assert bond_contract.functions.totalSupply().call() == 10000
        assert bond_contract.functions.faceValue().call() == 20000
        assert bond_contract.functions.redemptionDate().call() == "20211231"
        assert bond_contract.functions.redemptionValue().call() == 30000
        assert bond_contract.functions.returnDate().call() == "20211231"
        assert bond_contract.functions.returnAmount().call() == "リターン内容"
        assert bond_contract.functions.purpose().call() == "発行目的"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Invalid argument type (args)
    def test_error_1(self):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        arguments = []

        with pytest.raises(SendTransactionError):
            IbetStraightBondContract.create(
                args=arguments,
                tx_from=issuer_address,
                private_key=private_key
            )

    # <Error_2>
    # Invalid argument type (tx_from)
    def test_error_2(self):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            "20211231", 30000,
            "20211231", "リターン内容",
            "発行目的"
        ]

        with pytest.raises(SendTransactionError):
            IbetStraightBondContract.create(
                args=arguments,
                tx_from=issuer_address[:-1],  # short address
                private_key=private_key
            )

    # <Error_3>
    # Invalid argument type (private_key)
    def test_error_3(self):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            "20211231", 30000,
            "20211231", "リターン内容",
            "発行目的"
        ]

        with pytest.raises(SendTransactionError):
            IbetStraightBondContract.create(
                args=arguments,
                tx_from=issuer_address,
                private_key="some_private_key"
            )


class TestGet:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # default values
    def test_normal_1(self):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            "20211231", 30000,
            "20211231", "リターン内容",
            "発行目的"
        ]

        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # get token data
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)

        assert bond_contract.issuer_address == test_account["address"]
        assert bond_contract.token_address == contract_address
        assert bond_contract.name == arguments[0]
        assert bond_contract.symbol == arguments[1]
        assert bond_contract.total_supply == arguments[2]
        assert bond_contract.image_url == ["", "", ""]
        assert bond_contract.contact_information == ""
        assert bond_contract.privacy_policy == ""
        assert bond_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert bond_contract.status is True
        assert bond_contract.face_value == arguments[3]
        assert bond_contract.redemption_date == arguments[4]
        assert bond_contract.redemption_value == arguments[5]
        assert bond_contract.return_date == arguments[6]
        assert bond_contract.return_amount == arguments[7]
        assert bond_contract.purpose == arguments[8]
        assert bond_contract.interest_rate == 0
        assert bond_contract.interest_payment_date == ["", "", "", "", "", "", "", "", "", "", "", ""]
        assert bond_contract.transferable is True
        assert bond_contract.initial_offering_status is False
        assert bond_contract.is_redeemed is False
        assert bond_contract.personal_info_contract_address == ZERO_ADDRESS
