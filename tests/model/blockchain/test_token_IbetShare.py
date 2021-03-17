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
from app.model.schema import IbetShareAdd, IbetShareTransfer, IbetShareUpdate
from app.exceptions import SendTransactionError

from tests.account_config import config_eth_account


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
            "テスト株式", "TEST", 10000, 20000,
            1, "20211231", "20211231",
            "20221231"
        ]
        contract_address, abi, tx_hash = IbetShareContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # update
        _data = {}
        _add_data = IbetShareUpdate(**_data)
        IbetShareContract.update(
            contract_address=contract_address,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract = IbetShareContract.get(contract_address=contract_address)
        assert share_contract.cancellation_date == "20221231"
        assert share_contract.dividend_record_date == "20211231"
        assert share_contract.dividend_payment_date == "20211231"
        assert share_contract.dividends == 0.01
        assert share_contract.tradable_exchange_contract_address == "0x0000000000000000000000000000000000000000"
        assert share_contract.personal_info_contract_address == "0x0000000000000000000000000000000000000000"
        assert share_contract.image_url == ["", "", ""]
        assert share_contract.transferable == False
        assert share_contract.status == True
        assert share_contract.offering_status == False
        assert share_contract.contact_information == ""
        assert share_contract.privacy_policy == ""

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
            "テスト株式", "TEST", 10000, 20000,
            1, "20211231", "20211231",
            "20221231"
        ]
        contract_address, abi, tx_hash = IbetShareContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # update
        _data = {
            "cancellation_date": "20211231",
            "dividend_record_date": "20210930",
            "dividend_payment_date": "20211001",
            "dividends": 0.01,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",
            "image_url": ["image_1"],
            "transferable": False,
            "status": False,
            "offering_status": True,
            "contact_information": "contact info test",
            "privacy_policy": "privacy policy test"
        }
        _add_data = IbetShareUpdate(**_data)
        IbetShareContract.update(
            contract_address=contract_address,
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract = IbetShareContract.get(contract_address=contract_address)
        assert share_contract.cancellation_date == "20211231"
        assert share_contract.dividend_record_date == "20210930"
        assert share_contract.dividend_payment_date == "20211001"
        assert share_contract.dividends == 0.01
        assert share_contract.tradable_exchange_contract_address == "0x0000000000000000000000000000000000000001"
        assert share_contract.personal_info_contract_address == "0x0000000000000000000000000000000000000002"
        assert share_contract.image_url == ["image_1", "", ""]
        assert share_contract.transferable == False
        assert share_contract.status == False
        assert share_contract.offering_status == True
        assert share_contract.contact_information == "contact info test"
        assert share_contract.privacy_policy == "privacy policy test"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation (IbetShareUpdate)
    # invalid parameter
    def test_error_1(self):
        # update
        _data = {
            "dividends": 0.001,
            "tradable_exchange_contract_address": "invalid contract address",
            "personal_info_contract_address": "invalid contract address",
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetShareUpdate(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("dividends",),
                "msg": "dividends must be rounded to 2 decimal places",
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

    # Error_2
    # invalid parameter (dividends)
    def test_error_2(self):
        # update
        _data = {
            "dividends": 0.01
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetShareUpdate(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("dividends",),
                "msg": "all items are required to update the dividend information",
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
            "テスト株式", "TEST", 10000, 20000,
            1, "20211231", "20211231",
            "20221231"
        ]
        contract_address, abi, tx_hash = IbetShareContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # update
        _data = {
            "cancellation_date": "20211231"
        }
        _add_data = IbetShareUpdate(**_data)
        with pytest.raises(SendTransactionError):
            IbetShareContract.update(
                contract_address=contract_address,
                data=_add_data,
                tx_from=issuer_address,
                private_key="invalid private key"
            )


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
            "テスト株式", "TEST", 10000, 20000,
            1, "20211231", "20211231",
            "20221231"
        ]
        token_address, abi, tx_hash = IbetShareContract.create(
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
        _transfer_data = IbetShareTransfer(**_data)
        IbetShareContract.transfer(
            data=_transfer_data,
            tx_from=from_address,
            private_key=from_private_key
        )

        # assertion
        from_balance = IbetShareContract.get_account_balance(
            contract_address=token_address,
            account_address=from_address
        )
        to_balance = IbetShareContract.get_account_balance(
            contract_address=token_address,
            account_address=to_address
        )
        assert from_balance == arguments[3] - 10
        assert to_balance == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation (IbetShareTransfer)
    # required field
    def test_error_1(self):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            IbetShareTransfer(**_data)
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
    # validation (IbetShareTransfer)
    # invalid parameter
    def test_error_2(self):
        _data = {
            "token_address": "invalid contract address",
            "transfer_from": "invalid transfer_from address",
            "transfer_to": "invalid transfer_to address",
            "amount": 0
        }
        with pytest.raises(ValidationError) as exc_info:
            IbetShareTransfer(**_data)
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
            "テスト株式", "TEST", 10000, 20000,
            1, "20211231", "20211231",
            "20221231"
        ]
        token_address, abi, tx_hash = IbetShareContract.create(
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
        _transfer_data = IbetShareTransfer(**_data)
        with pytest.raises(SendTransactionError):
            IbetShareContract.transfer(
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
            "テスト株式", "TEST", 10000, 20000,
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
            "テスト株式", "TEST", 10000, 20000,
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
