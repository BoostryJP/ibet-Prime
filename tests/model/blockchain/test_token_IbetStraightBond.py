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
from unittest import mock
from binascii import Error
from unittest.mock import patch
from datetime import datetime

from pydantic.error_wrappers import ValidationError
from eth_keyfile import decode_keyfile_json
from web3.exceptions import (
    BadFunctionCallOutput,
    InvalidAddress,
    TimeExhausted,
    TransactionNotFound,
    ValidationError as Web3ValidationError
)
from config import ZERO_ADDRESS
from app.model.db import TokenAttrUpdate
from app.model.blockchain import IbetStraightBondContract
from app.utils.contract_utils import ContractUtils
from app.model.schema import (
    IbetStraightBondUpdate,
    IbetStraightBondAdd,
    IbetStraightBondTransfer
)
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

        # execute the function
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "20211231",
            30000,
            "20211231",
            "リターン内容",
            "発行目的"
        ]
        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
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
    # Invalid argument (args length)
    def test_error_1(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # execute the function
        arguments = []
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.create(
                args=arguments,
                tx_from=issuer_address,
                private_key=private_key
            )

        # assertion
        assert isinstance(exc_info.value.args[0], TypeError)
        assert exc_info.match("Incorrect argument count.")

    # <Error_2>
    # Invalid argument type (args)
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # execute the function
        arguments = [
            0,
            0,
            "string",
            "string",
            0,
            0,
            "string",
            0,
            0
        ]  # invalid types
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.create(
                args=arguments,
                tx_from=issuer_address,
                private_key=private_key
            )

        # assertion
        assert isinstance(exc_info.value.args[0], TypeError)
        assert exc_info.match("One or more arguments could not be encoded to the necessary ABI type.")

    # <Error_3>
    # Invalid argument type (tx_from)
    def test_error_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # execute the function
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "20211231",
            30000,
            "20211231",
            "リターン内容",
            "発行目的"
        ]
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.create(
                args=arguments,
                tx_from=issuer_address[:-1],  # short address
                private_key=private_key
            )

        # assertion
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'.+\' is invalid.")

    # <Error_4>
    # Invalid argument type (private_key)
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        # execute the function
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "20211231",
            30000,
            "20211231",
            "リターン内容",
            "発行目的"
        ]
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.create(
                args=arguments,
                tx_from=issuer_address,
                private_key="some_private_key"
            )

        # assertion
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")


class TestGet:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # TOKEN_CACHE is False
    @mock.patch("app.model.blockchain.token.TOKEN_CACHE", False)
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
        pre_datetime = datetime.utcnow()
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)

        # assertion
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

    # <Normal_2>
    # TOKEN_CACHE is True
    @mock.patch("app.model.blockchain.token.TOKEN_CACHE", True)
    def test_normal_2(self, db):

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

        # cache put
        IbetStraightBondContract.get(contract_address=contract_address)
        token_cache = IbetStraightBondContract.cache[contract_address]["token"]
        token_cache["issuer_address"] = issuer_address
        token_cache["token_address"] = contract_address
        token_cache["name"] = "テスト債券-test"
        token_cache["symbol"] = "TEST-test"
        token_cache["total_supply"] = 9999999
        token_cache["image_url"] = ["http://test1", "http://test2", "http://test3"]
        token_cache["contact_information"] = "test1"
        token_cache["privacy_policy"] = "test2"
        token_cache["tradable_exchange_contract_address"] = "0x1234567890123456789012345678901234567890"
        token_cache["status"] = False
        token_cache["face_value"] = 9999998
        token_cache["redemption_date"] = "99991231"
        token_cache["redemption_value"] = 9999997
        token_cache["return_date"] = "99991230"
        token_cache["return_amount"] = "return_amount-test"
        token_cache["purpose"] = "purpose-test"
        token_cache["interest_rate"] = 99.999
        token_cache["interest_payment_date"] = ["99991231", "99991231", "99991231", "99991231", "99991231",
                                                "99991231", "99991231", "99991231", "99991231", "99991231",
                                                "99991231", "99991231"]
        token_cache["transferable"] = False
        token_cache["initial_offering_status"] = True
        token_cache["is_redeemed"] = True
        token_cache["personal_info_contract_address"] = "0x1234567890123456789012345678901234567891"

        # get token data
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)

        # assertion
        assert bond_contract.issuer_address == test_account["address"]
        assert bond_contract.token_address == contract_address
        assert bond_contract.name == "テスト債券-test"
        assert bond_contract.symbol == "TEST-test"
        assert bond_contract.total_supply == 9999999
        assert bond_contract.image_url == ["http://test1", "http://test2", "http://test3"]
        assert bond_contract.contact_information == "test1"
        assert bond_contract.privacy_policy == "test2"
        assert bond_contract.tradable_exchange_contract_address == "0x1234567890123456789012345678901234567890"
        assert bond_contract.status is False
        assert bond_contract.face_value == 9999998
        assert bond_contract.redemption_date == "99991231"
        assert bond_contract.redemption_value == 9999997
        assert bond_contract.return_date == "99991230"
        assert bond_contract.return_amount == "return_amount-test"
        assert bond_contract.purpose == "purpose-test"
        assert bond_contract.interest_rate == 99.999
        assert bond_contract.interest_payment_date == ["99991231", "99991231", "99991231", "99991231", "99991231",
                                                       "99991231", "99991231", "99991231", "99991231", "99991231",
                                                       "99991231", "99991231"]
        assert bond_contract.transferable is False
        assert bond_contract.initial_offering_status is True
        assert bond_contract.is_redeemed is True
        assert bond_contract.personal_info_contract_address == "0x1234567890123456789012345678901234567891"

    # <Normal_3>
    # TOKEN_CACHE is True, updated token attribute
    @mock.patch("app.model.blockchain.token.TOKEN_CACHE", True)
    def test_normal_3(self, db):

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

        # cache put
        IbetStraightBondContract.get(contract_address=contract_address)
        token_cache = IbetStraightBondContract.cache[contract_address]["token"]
        token_cache["issuer_address"] = issuer_address
        token_cache["token_address"] = contract_address
        token_cache["name"] = "テスト債券-test"
        token_cache["symbol"] = "TEST-test"
        token_cache["total_supply"] = 9999999
        token_cache["image_url"] = ["http://test1", "http://test2", "http://test3"]
        token_cache["contact_information"] = "test1"
        token_cache["privacy_policy"] = "test2"
        token_cache["tradable_exchange_contract_address"] = "0x1234567890123456789012345678901234567890"
        token_cache["status"] = False
        token_cache["face_value"] = 9999998
        token_cache["redemption_date"] = "99991231"
        token_cache["redemption_value"] = 9999997
        token_cache["return_date"] = "99991230"
        token_cache["return_amount"] = "return_amount-test"
        token_cache["purpose"] = "purpose-test"
        token_cache["interest_rate"] = 99.999
        token_cache["interest_payment_date"] = ["99991231", "99991231", "99991231", "99991231", "99991231",
                                                "99991231", "99991231", "99991231", "99991231", "99991231",
                                                "99991231", "99991231"]
        token_cache["transferable"] = False
        token_cache["initial_offering_status"] = True
        token_cache["is_redeemed"] = True
        token_cache["personal_info_contract_address"] = "0x1234567890123456789012345678901234567891"

        # updated token attribute
        _token_attr_update = TokenAttrUpdate()
        _token_attr_update.token_address = contract_address
        _token_attr_update.updated_datetime = datetime.utcnow()
        db.add(_token_attr_update)
        db.commit()

        # get token data
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)

        # assertion
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

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Invalid argument type (contract_address does not exists)
    def test_error_1(self, db):
        # get token data
        with pytest.raises(BadFunctionCallOutput) as exc_info:
            IbetStraightBondContract.get(contract_address=ZERO_ADDRESS)
        # assertion
        assert exc_info.match("Could not transact with/call contract function,")
        assert exc_info.match(", is contract deployed correctly and chain synced?")

    # <Error_2>
    # Invalid argument type (contract_address is not address)
    def test_error_2(self, db):
        # get token data
        with pytest.raises(ValueError) as exc_info:
            IbetStraightBondContract.get(contract_address=ZERO_ADDRESS[:-1])
        # assertion
        assert exc_info.match("Unknown format.*, attempted to normalize to.*")


class TestUpdate:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # All items are None
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

        # update
        _data = {}
        _add_data = IbetStraightBondUpdate(**_data)
        pre_datetime = datetime.utcnow()
        IbetStraightBondContract.update(
            contract_address=contract_address,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)
        assert bond_contract.face_value == 20000
        assert bond_contract.interest_rate == 0
        assert bond_contract.interest_payment_date == ["", "", "", "", "", "", "", "", "", "", "", ""]
        assert bond_contract.redemption_value == 30000
        assert bond_contract.transferable is True
        assert bond_contract.image_url == ["", "", ""]
        assert bond_contract.status is True
        assert bond_contract.initial_offering_status is False
        assert bond_contract.is_redeemed is False
        assert bond_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert bond_contract.personal_info_contract_address == ZERO_ADDRESS
        assert bond_contract.contact_information == ""
        assert bond_contract.privacy_policy == ""
        _token_attr_update = db.query(TokenAttrUpdate).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    # <Normal_2>
    # Update all items
    def test_normal_2(self, db):
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

        # update
        _data = {
            "face_value": 20001,
            "interest_rate": 0.0001,
            "interest_payment_date": ["0331", "0930"],
            "redemption_value": 30001,
            "transferable": False,
            "image_url": ["image_1"],
            "status": False,
            "initial_offering_status": True,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",
            "contact_information": "contact info test",
            "privacy_policy": "privacy policy test"
        }
        _add_data = IbetStraightBondUpdate(**_data)
        pre_datetime = datetime.utcnow()
        IbetStraightBondContract.update(
            contract_address=contract_address,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)
        assert bond_contract.face_value == 20001
        assert bond_contract.interest_rate == 0.0001
        assert bond_contract.interest_payment_date == ["0331", "0930", "", "", "", "", "", "", "", "", "", ""]
        assert bond_contract.redemption_value == 30001
        assert bond_contract.transferable is False
        assert bond_contract.image_url == ["image_1", "", ""]
        assert bond_contract.status is False
        assert bond_contract.initial_offering_status is True
        assert bond_contract.is_redeemed is True
        assert bond_contract.tradable_exchange_contract_address == "0x0000000000000000000000000000000000000001"
        assert bond_contract.personal_info_contract_address == "0x0000000000000000000000000000000000000002"
        assert bond_contract.contact_information == "contact info test"
        assert bond_contract.privacy_policy == "privacy policy test"
        _token_attr_update = db.query(TokenAttrUpdate).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    # <Normal_3>
    # contract_address does not exists
    def test_normal_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )
        # update
        _data = {
            "interest_rate": 0.0001
        }
        _add_data = IbetStraightBondUpdate(**_data)
        IbetStraightBondContract.update(
            contract_address=ZERO_ADDRESS,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )
        with pytest.raises(BadFunctionCallOutput) as exc_info:
            IbetStraightBondContract.get(contract_address=ZERO_ADDRESS)
        assert exc_info.match("Could not transact with/call contract function,")
        assert exc_info.match(", is contract deployed correctly and chain synced?")

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Invalid argument type (contract_address is not address)
    def test_error_1(self, db):
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

        # update
        _data = {
            "interest_rate": 0.0001,
        }
        _add_data = IbetStraightBondUpdate(**_data)
        with pytest.raises(ValueError) as exc_info:
            IbetStraightBondContract.update(
                contract_address=contract_address[:-1],  # short
                data=_add_data,
                tx_from=issuer_address,
                private_key=private_key
            )
        assert exc_info.match("Unknown format.*, attempted to normalize to.*")

    # <Error_2>
    # Validation (IbetStraightBondUpdate)
    # invalid parameter
    def test_error_2(self, db):
        # update
        _data = {
            "interest_rate": 0.00001,
            "interest_payment_date": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
            "tradable_exchange_contract_address": "invalid contract address",
            "personal_info_contract_address": "invalid contract address",
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondUpdate(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("interest_rate",),
                "msg": "interest_rate must be rounded to 4 decimal places",
                "type": "value_error"
            }, {
                "loc": ("interest_payment_date",),
                "msg": "list length of interest_payment_date must be less than 13",
                "type": "value_error"
            }, {
                "loc": ("tradable_exchange_contract_address",),
                "msg": "tradable_exchange_contract_address is not a valid address",
                "type": "value_error"
            }, {
                "loc": ("personal_info_contract_address",),
                "msg": "personal_info_contract_address is not a valid address",
                "type": "value_error"
            }
        ]

    # <Error_3>
    # Validation (IbetStraightBondUpdate)
    # invalid parameter (min value)
    def test_error_3(self, db):
        # update
        _data = {
            "face_value": -1,
            "interest_rate": -0.0001,
            "redemption_value": -1,
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondUpdate(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {
                    "limit_value": 0
                },
                "loc": ("face_value",),
                "msg": "ensure this value is greater than or equal to 0",
                "type": "value_error.number.not_ge"
            },
            {
                "ctx": {
                    "limit_value": 0.0000
                },
                "loc": ("interest_rate",),
                "msg": "ensure this value is greater than or equal to 0.0",
                "type": "value_error.number.not_ge"
            },
            {
                "ctx": {
                    "limit_value": 0
                },
                "loc": ("redemption_value",),
                "msg": "ensure this value is greater than or equal to 0",
                "type": "value_error.number.not_ge"
            },
        ]

    # <Error_4>
    # Validation (IbetStraightBondUpdate)
    # invalid parameter (max value)
    def test_error_4(self, db):
        # update
        _data = {
            "face_value": 5_000_000_001,
            "interest_rate": 100.0001,
            "redemption_value": 5_000_000_001,
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondUpdate(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {
                    "limit_value": 5_000_000_000
                },
                "loc": ("face_value",),
                "msg": "ensure this value is less than or equal to 5000000000",
                "type": "value_error.number.not_le"
            },
            {
                "ctx": {
                    "limit_value": 100.0000
                },
                "loc": ("interest_rate",),
                "msg": "ensure this value is less than or equal to 100.0",
                "type": "value_error.number.not_le"
            },
            {
                "ctx": {
                    "limit_value": 5_000_000_000
                },
                "loc": ("redemption_value",),
                "msg": "ensure this value is less than or equal to 5000000000",
                "type": "value_error.number.not_le"
            },
        ]

    # <Error_5>
    # invalid tx_from
    def test_error_5(self, db):
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

        # update
        _data = {
            "face_value": 20001
        }
        _add_data = IbetStraightBondUpdate(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.update(
                contract_address=contract_address,
                data=_add_data,
                tx_from="DUMMY",
                private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'DUMMY\' is invalid.")

    # <Error_6>
    # invalid private key
    def test_error_6(self, db):
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

        # update
        _data = {
            "face_value": 20001
        }
        _add_data = IbetStraightBondUpdate(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.update(
                contract_address=contract_address,
                data=_add_data,
                tx_from=issuer_address,
                private_key="invalid private key"
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_7>
    # TimeExhausted
    def test_error_7(self, db):
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

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            side_effect=TimeExhausted
        )

        # update
        _data = {
            "face_value": 20001
        }
        _add_data = IbetStraightBondUpdate(**_data)
        with Web3_sendRawTransaction:
            with pytest.raises(SendTransactionError) as exc_info:
                IbetStraightBondContract.update(
                    contract_address=contract_address,
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_8>
    # Error
    def test_error_8(self, db):
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

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            side_effect=TransactionNotFound
        )

        # update
        _data = {
            "face_value": 20001
        }
        _add_data = IbetStraightBondUpdate(**_data)
        with Web3_sendRawTransaction:
            with pytest.raises(SendTransactionError) as exc_info:
                IbetStraightBondContract.update(
                    contract_address=contract_address,
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)


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
            "from_address": from_address,
            "to_address": to_address,
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
    def test_error_1(self, db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondTransfer(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("token_address",),
                "msg": "field required",
                "type": "value_error.missing"
            }, {
                "loc": ("from_address",),
                "msg": "field required",
                "type": "value_error.missing"
            }, {
                "loc": ("to_address",),
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
    def test_error_2(self, db):
        _data = {
            "token_address": "invalid contract address",
            "from_address": "invalid from_address",
            "to_address": "invalid to_address",
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
                "loc": ("from_address",),
                "msg": "from_address is not a valid address",
                "type": "value_error"
            }, {
                "loc": ("to_address",),
                "msg": "to_address is not a valid address",
                "type": "value_error"
            }, {
                "ctx": {
                    "limit_value": 1
                },
                "loc": ("amount",),
                "msg": "ensure this value is greater than or equal to 1",
                "type": "value_error.number.not_ge"
            }
        ]

    # <Error_3>
    # validation (IbetStraightBondTransfer)
    # invalid parameter: max value
    def test_error_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        to_account = config_eth_account("user2")
        to_address = to_account.get("address")

        token_address = "0x1234567890123456789012345678901234567890"

        _data = {
            "token_address": token_address,
            "from_address": issuer_address,
            "to_address": to_address,
            "amount": 100_000_001
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondTransfer(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {
                    "limit_value": 100_000_000
                },
                "loc": ("amount",),
                "msg": "ensure this value is less than or equal to 100000000",
                "type": "value_error.number.not_le"
            }
        ]

    # <Error_4>
    # invalid tx_from
    def test_error_4(self, db):
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
            "from_address": from_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = IbetStraightBondTransfer(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.transfer(
                data=_transfer_data,
                tx_from="invalid_tx_from",
                private_key=from_private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

    # <Error_5>
    # invalid private key
    def test_error_5(self, db):
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
            "from_address": from_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = IbetStraightBondTransfer(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.transfer(
                data=_transfer_data,
                tx_from=from_address,
                private_key="invalid_private_key"
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_6>
    # TimeExhausted
    def test_error_6(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
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
        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            side_effect=TimeExhausted
        )

        # transfer
        _data = {
            "token_address": contract_address,
            "from_address": issuer_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = IbetStraightBondTransfer(**_data)
        with Web3_sendRawTransaction:
            with pytest.raises(SendTransactionError) as exc_info:
                IbetStraightBondContract.transfer(
                    data=_transfer_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_7>
    # Error
    def test_error_7(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
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
        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            side_effect=TransactionNotFound
        )

        # transfer
        _data = {
            "token_address": contract_address,
            "from_address": issuer_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = IbetStraightBondTransfer(**_data)
        with Web3_sendRawTransaction:
            with pytest.raises(SendTransactionError) as exc_info:
                IbetStraightBondContract.transfer(
                    data=_transfer_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)


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
        pre_datetime = datetime.utcnow()
        IbetStraightBondContract.add_supply(
            contract_address=contract_address,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        bond_contract = IbetStraightBondContract.get(contract_address=contract_address)
        assert bond_contract.total_supply == arguments[2] + 10
        _token_attr_update = db.query(TokenAttrUpdate).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    # <Normal_2>
    # contract_address does not exists
    def test_normal_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )
        # add supply
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = IbetStraightBondAdd(**_data)
        IbetStraightBondContract.add_supply(
            contract_address=ZERO_ADDRESS,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )
        with pytest.raises(BadFunctionCallOutput) as exc_info:
            IbetStraightBondContract.get(contract_address=ZERO_ADDRESS)
        assert exc_info.match("Could not transact with/call contract function,")
        assert exc_info.match(", is contract deployed correctly and chain synced?")

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Invalid argument type (contract_address is not address)
    def test_error_1(self, db):
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
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.add_supply(
                contract_address=contract_address[:-1],  # short
                data=_add_data,
                tx_from=issuer_address,
                private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], ValueError)
        assert exc_info.match("Unknown format.*, attempted to normalize to.*")

    # <Error_2>
    # validation (IbetStraightBondAdd)
    # required field
    def test_error_2(self, db):
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

    # <Error_3>
    # validation (IbetStraightBondAdd)
    # invalid parameter
    def test_error_3(self, db):
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
                "ctx": {
                    "limit_value": 1
                },
                "loc": ("amount",),
                "msg": "ensure this value is greater than or equal to 1",
                "type": "value_error.number.not_ge"
            }
        ]

    # <Error_4>
    # validation (IbetStraightBondAdd)
    # invalid parameter: max value
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        _data = {
            "account_address": issuer_address,
            "amount": 100_000_001
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetStraightBondAdd(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {
                    "limit_value": 100_000_000
                },
                "loc": ("amount",),
                "msg": "ensure this value is less than or equal to 100000000",
                "type": "value_error.number.not_le"
            }
        ]

    # <Error_5>
    # invalid tx_from
    def test_error_5(self, db):
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
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.add_supply(
                contract_address=contract_address,
                data=_add_data,
                tx_from="invalid_tx_from",
                private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

    # <Error_6>
    # invalid private key
    def test_error_6(self, db):
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
        with pytest.raises(SendTransactionError) as exc_info:
            IbetStraightBondContract.add_supply(
                contract_address=contract_address,
                data=_add_data,
                tx_from=test_account.get("address"),
                private_key="invalid_private_key"
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_7>
    # TimeExhausted
    def test_error_7(self, db):
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

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            side_effect=TimeExhausted
        )

        # add supply
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = IbetStraightBondAdd(**_data)
        with Web3_sendRawTransaction:
            with pytest.raises(SendTransactionError) as exc_info:
                IbetStraightBondContract.add_supply(
                    contract_address=contract_address,
                    data=_add_data,
                    tx_from=test_account.get("address"),
                    private_key=private_key
                )
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_8>
    # Error
    def test_error_8(self, db):
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

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            side_effect=TransactionNotFound
        )

        # add supply
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = IbetStraightBondAdd(**_data)
        with Web3_sendRawTransaction:
            with pytest.raises(SendTransactionError) as exc_info:
                IbetStraightBondContract.add_supply(
                    contract_address=contract_address,
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)


class TestGetAccountBalance:

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
            "テスト債券",
            "TEST",
            10000,
            20000,
            "20211231",
            30000,
            "20211231",
            "リターン内容",
            "発行目的"
        ]
        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        balance = IbetStraightBondContract.get_account_balance(
            contract_address=contract_address,
            account_address=issuer_address
        )
        assert balance == arguments[2]

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid contract_address
    def test_error_1(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "20211231",
            30000,
            "20211231",
            "リターン内容",
            "発行目的"
        ]
        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # execute the function
        with pytest.raises(ValueError) as exc_info:
            IbetStraightBondContract.get_account_balance(
                contract_address[:-1],  # short
                issuer_address
            )

        # assertion
        assert exc_info.match(f"Unknown format {contract_address[:-1]}, attempted to normalize to ")

    # <Error_2>
    # invalid contract_address : not deployed contract_address
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        # execute the function
        with pytest.raises(BadFunctionCallOutput) as exc_info:
            IbetStraightBondContract.get_account_balance(
                ZERO_ADDRESS,
                issuer_address
            )

        # assertion
        assert exc_info.match("Could not transact with/call contract function,")
        assert exc_info.match(", is contract deployed correctly and chain synced?")

    # <Error_3>
    # invalid account_address
    def test_error_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "20211231",
            30000,
            "20211231",
            "リターン内容",
            "発行目的"
        ]
        contract_address, abi, tx_hash = IbetStraightBondContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # execute the function
        with pytest.raises(Web3ValidationError):
            IbetStraightBondContract.get_account_balance(
                contract_address,
                issuer_address[:-1]  # short
            )

    # <Error_4>
    # invalid contract_address : not deployed contract_address
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        # execute the function
        with pytest.raises(BadFunctionCallOutput) as exc_info:
            IbetStraightBondContract.get_account_balance(
                ZERO_ADDRESS,
                issuer_address
            )

        # assertion
        assert exc_info.match("Could not transact with/call contract function,")
        assert exc_info.match(", is contract deployed correctly and chain synced?")
