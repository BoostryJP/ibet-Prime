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

from config import ZERO_ADDRESS
from app.model.blockchain import IbetStraightBondContract
from app.model.blockchain.utils import ContractUtils
from app.model.schema import IbetStraightBondAdd, IbetStraightBondTransfer
from app.exceptions import SendTransactionError

from tests.account_config import config_eth_account


class TestCreate:

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


class TestTransfer:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        from_account = config_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8")
        )

        to_account = config_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            "20211231", 30000,
            "20211231", "リターン内容",
            "発行目的"
        ]
        token_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=from_address,
            private_key=from_private_key
        )

        # transfer
        _data = {
            "token_address": token_address,
            "transfer_from": from_address,
            "transfer_to": to_address,
            "amount": 10
        }
        _transfer_data = IbetStraightBondTransfer(**_data)
        IbetStraightBondContract.transfer(
            data=_transfer_data,
            tx_from=from_address,
            private_key=from_private_key
        )

        # assertion
        from_balance = IbetStraightBondContract.get_account_balance(
            contract_address=token_address,
            account_address=from_address
        )
        to_balance = IbetStraightBondContract.get_account_balance(
            contract_address=token_address,
            account_address=to_address
        )
        assert from_balance == arguments[2] - 10
        assert to_balance == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation (IbetStraightBondTransfer)
    # required field
    def test_error_1(self):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondTransfer(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("token_address",),
                "msg": "field required",
                "type": "value_error.missing"
            }, {
                "loc": ("transfer_from",),
                "msg": "field required",
                "type": "value_error.missing"
            }, {
                "loc": ("transfer_to",),
                "msg": "field required",
                "type": "value_error.missing"
            }, {
                "loc": ("amount",),
                "msg": "field required",
                "type": "value_error.missing"
            }
        ]

    # <Error_2>
    # validation (IbetStraightBondTransfer)
    # invalid parameter
    def test_error_2(self):
        _data = {
            "token_address": "invalid contract address",
            "transfer_from": "invalid transfer_from address",
            "transfer_to": "invalid transfer_to address",
            "amount": 0
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondTransfer(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("token_address",),
                "msg": "token_address is not a valid address",
                "type": "value_error"
            }, {
                "loc": ("transfer_from",),
                "msg": "transfer_from is not a valid address",
                "type": "value_error"
            }, {
                "loc": ("transfer_to",),
                "msg": "transfer_to is not a valid address",
                "type": "value_error"
            }, {
                "loc": ("amount",),
                "msg": "amount must be greater than 0",
                "type": "value_error"
            }
        ]

    # <Error_3>
    # invalid private key
    def test_error_3(self, db):
        from_account = config_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8")
        )

        to_account = config_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券", "TEST", 10000, 20000,
            "20211231", 30000,
            "20211231", "リターン内容",
            "発行目的"
        ]
        token_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=from_address,
            private_key=from_private_key
        )

        # transfer
        _data = {
            "token_address": token_address,
            "transfer_from": from_address,
            "transfer_to": to_address,
            "amount": 10
        }
        _transfer_data = IbetStraightBondTransfer(**_data)
        with pytest.raises(SendTransactionError):
            IbetStraightBondContract.transfer(
                data=_transfer_data,
                tx_from=from_address,
                private_key="invalid_private_key"
            )


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
            "20211231", 30000,
            "20211231", "リターン内容",
            "発行目的"
        ]
        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # add supply
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = IbetStraightBondAdd(**_data)
        IbetStraightBondContract.add_supply(
            contract_address=contract_address,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)
        assert bond_contract.total_supply == arguments[2] + 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation (IbetStraightBondAdd)
    # required field
    def test_error_1(self):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondAdd(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("account_address",), 
                "msg": "field required", 
                "type": "value_error.missing"
            }, {
                "loc": ("amount",), 
                "msg": "field required", 
                "type": "value_error.missing"
            }
        ]

    # <Error_2>
    # validation (IbetStraightBondAdd)
    # invalid parameter
    def test_error_2(self):
        _data = {
            "account_address": "invalid account address",
            "amount": 0
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondAdd(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("account_address",), 
                "msg": "account_address is not a valid address", 
                "type": "value_error"
            }, {
                "loc": ("amount",), 
                "msg": "amount must be greater than 0",
                "type": "value_error"
            }
        ]

    # <Error_3>
    # invalid private key
    def test_error_3(self, db):
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

        # add supply
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = IbetStraightBondAdd(**_data)
        with pytest.raises(SendTransactionError):
            IbetStraightBondContract.add_supply(
                contract_address=contract_address,
                data=_add_data,
                tx_from=test_account.get("address"),
                private_key="invalid_private_key"
            )
