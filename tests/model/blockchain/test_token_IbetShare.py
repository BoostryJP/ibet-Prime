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
import time
from unittest import mock
from binascii import Error
from datetime import datetime, timedelta

from pydantic.error_wrappers import ValidationError
from eth_keyfile import decode_keyfile_json
from unittest.mock import patch, MagicMock
from web3.exceptions import (
    InvalidAddress,
    TimeExhausted,
    TransactionNotFound,
    ValidationError as Web3ValidationError,
    ContractLogicError
)

from config import ZERO_ADDRESS, TOKEN_CACHE_TTL
from app.model.db import (
    TokenAttrUpdate,
    TokenCache
)
from app.model.blockchain import IbetShareContract
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams,
    TransferParams,
    AdditionalIssueParams,
    RedeemParams,
    ApproveTransferParams,
    CancelTransferParams,
    LockParams,
    ForceUnlockPrams
)
from app.utils.contract_utils import ContractUtils
from app.exceptions import SendTransactionError, ContractRevertError

from tests.account_config import config_eth_account
from tests.utils.contract_utils import (
    PersonalInfoContractTestUtils,
    IbetSecurityTokenContractTestUtils
)


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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=contract_address
        )
        _dividend_info = share_contract.functions.dividendInformation().call()
        assert share_contract.functions.owner().call() == issuer_address
        assert share_contract.functions.name().call() == "テスト株式"
        assert share_contract.functions.symbol().call() == "TEST"
        assert share_contract.functions.issuePrice().call() == 10000
        assert share_contract.functions.totalSupply().call() == 20000
        assert _dividend_info[0] == 1  # dividends
        assert _dividend_info[1] == "20211231"  # dividendRecordDate
        assert _dividend_info[2] == "20211231"  # dividendPaymentDate
        assert share_contract.functions.cancellationDate().call() == "20221231"
        assert share_contract.functions.principalValue().call() == 10000

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
        share_contract = IbetShareContract()
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.create(
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
            "string",
            0,
            0,
            0,
            "string"
        ]  # invalid types
        share_contract = IbetShareContract()
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.create(
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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.create(
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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.create(
                args=arguments,
                tx_from=issuer_address,
                private_key="some_private_key"
            )

        # assertion
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # Already deployed
    def test_error_5(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # execute the function
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        contract_address, abi, tx_hash = IbetShareContract().create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        with pytest.raises(SendTransactionError) as exc_info:
            IbetShareContract(contract_address).create(
                args=arguments,
                tx_from=issuer_address,
                private_key=private_key
            )

        # assertion
        assert exc_info.match("contract is already deployed")


class TestGet:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # TOKEN_CACHE is False
    @mock.patch("app.model.blockchain.token.TOKEN_CACHE", False)
    def test_normal_1(self, db):
        # prepare account
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211229",
            "20211230",
            "20221231",
            10001
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # execute the function
        share_contract = share_contract.get()

        # assertion
        assert share_contract.issuer_address == issuer_address
        assert share_contract.token_address == contract_address
        assert share_contract.name == "テスト株式"
        assert share_contract.symbol == "TEST"
        assert share_contract.total_supply == 20000
        assert share_contract.contact_information == ""
        assert share_contract.privacy_policy == ""
        assert share_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert share_contract.status is True
        assert share_contract.personal_info_contract_address == ZERO_ADDRESS
        assert share_contract.transferable is False
        assert share_contract.is_offering is False
        assert share_contract.transfer_approval_required is False
        assert share_contract.issue_price == 10000
        assert share_contract.memo == ""
        assert share_contract.cancellation_date == "20221231"
        assert share_contract.principal_value == 10001
        assert share_contract.is_canceled is False
        assert share_contract.dividends == 0.0000000000001  # dividends
        assert share_contract.dividend_record_date == "20211229"  # dividendRecordDate
        assert share_contract.dividend_payment_date == "20211230"  # dividendPaymentDate

    # <Normal_2>
    # TOKEN_CACHE is True
    @mock.patch("app.model.blockchain.token.TOKEN_CACHE", True)
    def test_normal_2(self, db):

        # prepare account
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211229",
            "20211230",
            "20221231",
            10001
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # create cache
        token_attr = {
            "issuer_address": issuer_address,
            "token_address": contract_address,
            "name": "テスト株式-test",
            "symbol": "TEST-test",
            "total_supply": 999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "issue_price": 999997,
            "cancellation_date": "99991231",
            "memo": "memo_test",
            "principal_value": 999998,
            "is_canceled": True,
            "dividends": 9.99,
            "dividend_record_date": "99991230",
            "dividend_payment_date": "99991229"
        }
        token_cache = TokenCache()
        token_cache.token_address = contract_address
        token_cache.attributes = token_attr
        token_cache.cached_datetime = datetime.utcnow()
        token_cache.expiration_datetime = datetime.utcnow() + timedelta(seconds=TOKEN_CACHE_TTL)
        db.add(token_cache)
        db.commit()

        # execute the function
        share_contract = share_contract.get()

        # assertion
        assert share_contract.issuer_address == issuer_address
        assert share_contract.token_address == contract_address
        assert share_contract.name == "テスト株式-test"
        assert share_contract.symbol == "TEST-test"
        assert share_contract.total_supply == 999999
        assert share_contract.contact_information == "test1"
        assert share_contract.privacy_policy == "test2"
        assert share_contract.tradable_exchange_contract_address == "0x1234567890123456789012345678901234567890"
        assert share_contract.status is False
        assert share_contract.personal_info_contract_address == "0x1234567890123456789012345678901234567891"
        assert share_contract.transferable is True
        assert share_contract.is_offering is True
        assert share_contract.transfer_approval_required is True
        assert share_contract.issue_price == 999997
        assert share_contract.cancellation_date == "99991231"
        assert share_contract.memo == "memo_test"
        assert share_contract.principal_value == 999998
        assert share_contract.is_canceled is True
        assert share_contract.dividends == 9.99  # dividends
        assert share_contract.dividend_record_date == "99991230"  # dividendRecordDate
        assert share_contract.dividend_payment_date == "99991229"  # dividendPaymentDate

    # <Normal_3>
    # TOKEN_CACHE is True, updated token attribute
    @mock.patch("app.model.blockchain.token.TOKEN_CACHE", True)
    def test_normal_3(self, db):

        # prepare account
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211229",
            "20211230",
            "20221231",
            10001
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # create cache
        token_attr = {
            "issuer_address": issuer_address,
            "token_address": contract_address,
            "name": "テスト株式-test",
            "symbol": "TEST-test",
            "total_supply": 999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "issue_price": 999997,
            "cancellation_date": "99991231",
            "memo": "memo_test",
            "principal_value": 999998,
            "is_canceled": True,
            "dividends": 9.99,
            "dividend_record_date": "99991230",
            "dividend_payment_date": "99991229"
        }
        token_cache = TokenCache()
        token_cache.token_address = contract_address
        token_cache.attributes = token_attr
        token_cache.cached_datetime = datetime.utcnow()
        token_cache.expiration_datetime = datetime.utcnow() + timedelta(seconds=TOKEN_CACHE_TTL)
        db.add(token_cache)
        db.commit()

        # updated token attribute
        _token_attr_update = TokenAttrUpdate()
        _token_attr_update.token_address = contract_address
        _token_attr_update.updated_datetime = datetime.utcnow()
        db.add(_token_attr_update)
        db.commit()

        # execute the function
        share_contract = share_contract.get()

        # assertion
        assert share_contract.issuer_address == issuer_address
        assert share_contract.token_address == contract_address
        assert share_contract.name == "テスト株式"
        assert share_contract.symbol == "TEST"
        assert share_contract.total_supply == 20000
        assert share_contract.contact_information == ""
        assert share_contract.privacy_policy == ""
        assert share_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert share_contract.status is True
        assert share_contract.personal_info_contract_address == ZERO_ADDRESS
        assert share_contract.transferable is False
        assert share_contract.is_offering is False
        assert share_contract.transfer_approval_required is False
        assert share_contract.issue_price == 10000
        assert share_contract.cancellation_date == "20221231"
        assert share_contract.memo == ""
        assert share_contract.principal_value == 10001
        assert share_contract.is_canceled is False
        assert share_contract.dividends == 0.0000000000001  # dividends
        assert share_contract.dividend_record_date == "20211229"  # dividendRecordDate
        assert share_contract.dividend_payment_date == "20211230"  # dividendPaymentDate

    # <Normal_4>
    # contract not deployed
    def test_normal_4(self, db):
        share_contract = IbetShareContract()
        # execute the function
        share_contract = share_contract.get()

        # assertion
        assert share_contract.issuer_address == ZERO_ADDRESS
        assert share_contract.token_address == ZERO_ADDRESS
        assert share_contract.name == ""
        assert share_contract.symbol == ""
        assert share_contract.total_supply == 0
        assert share_contract.contact_information == ""
        assert share_contract.privacy_policy == ""
        assert share_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert share_contract.status is True
        assert share_contract.personal_info_contract_address == ZERO_ADDRESS
        assert share_contract.transferable is False
        assert share_contract.is_offering is False
        assert share_contract.transfer_approval_required is False
        assert share_contract.issue_price == 0
        assert share_contract.cancellation_date == ""
        assert share_contract.memo == ""
        assert share_contract.principal_value == 0
        assert share_contract.is_canceled is False
        assert share_contract.dividends == 0  # dividends
        assert share_contract.dividend_record_date == ""  # dividendRecordDate
        assert share_contract.dividend_payment_date == ""  # dividendPaymentDate

    ###########################################################################
    # Error Case
    ###########################################################################


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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # update
        _data = {}
        _add_data = UpdateParams(**_data)
        pre_datetime = datetime.utcnow()
        share_contract.update(
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract = share_contract.get()
        assert share_contract.cancellation_date == "20221231"
        assert share_contract.dividend_record_date == "20211231"
        assert share_contract.dividend_payment_date == "20211231"
        assert share_contract.dividends == 0.0000000000001
        assert share_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert share_contract.personal_info_contract_address == ZERO_ADDRESS
        assert share_contract.transferable is False
        assert share_contract.status is True
        assert share_contract.is_offering is False
        assert share_contract.contact_information == ""
        assert share_contract.privacy_policy == ""
        assert share_contract.transfer_approval_required is False
        assert share_contract.principal_value == 10000
        assert share_contract.is_canceled is False
        assert share_contract.memo == ""

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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
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
            "transferable": False,
            "status": False,
            "is_offering": True,
            "contact_information": "contact info test",
            "privacy_policy": "privacy policy test",
            "transfer_approval_required": True,
            "principal_value": 9000,
            "is_canceled": True,
            "memo": "memo_test",
        }
        _add_data = UpdateParams(**_data)
        pre_datetime = datetime.utcnow()
        share_contract.update(
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract = share_contract.get()
        assert share_contract.cancellation_date == "20211231"
        assert share_contract.dividend_record_date == "20210930"
        assert share_contract.dividend_payment_date == "20211001"
        assert share_contract.dividends == 0.01
        assert share_contract.tradable_exchange_contract_address == "0x0000000000000000000000000000000000000001"
        assert share_contract.personal_info_contract_address == "0x0000000000000000000000000000000000000002"
        assert share_contract.transferable is False
        assert share_contract.status is False
        assert share_contract.is_offering is True
        assert share_contract.contact_information == "contact info test"
        assert share_contract.privacy_policy == "privacy policy test"
        assert share_contract.transfer_approval_required is True
        assert share_contract.principal_value == 9000
        assert share_contract.is_canceled is True
        assert share_contract.memo == "memo_test"
        _token_attr_update = db.query(TokenAttrUpdate).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation (UpdateParams)
    # invalid parameter
    def test_error_1(self, db):
        # update
        _data = {
            "dividends": 0.00000000000001,
            "tradable_exchange_contract_address": "invalid contract address",
            "personal_info_contract_address": "invalid contract address",
        }
        with pytest.raises(ValidationError) as exc_info:
            UpdateParams(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("dividends",),
                "msg": "dividends must be rounded to 13 decimal places",
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

    # <Error_2>
    # invalid tx_from
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # update
        _data = {
            "cancellation_date": "20211231"
        }
        _add_data = UpdateParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.update(
                data=_add_data,
                tx_from="invalid_tx_from",
                private_key="invalid private key"
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # update
        _data = {
            "cancellation_date": "20211231"
        }
        _add_data = UpdateParams(**_data)
        with pytest.raises(SendTransactionError):
            share_contract.update(
                data=_add_data,
                tx_from=issuer_address,
                private_key="invalid private key"
            )

    # <Error_4>
    # TimeExhausted
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TimeExhausted
        )

        # update
        _data = {
            "cancellation_date": "20211231"
        }
        _add_data = UpdateParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.update(
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )

        # assertion
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_5>
    # Transaction Error
    def test_error_5(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound
        )

        # update
        _data = {
            "cancellation_date": "20211231"
        }
        _add_data = UpdateParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.update(
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )

        # assertion
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_6>
    # Transaction REVERT(not owner)
    def test_error_6(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        user_account = config_eth_account("user2")
        user_address = user_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )
        user_private_key = decode_keyfile_json(
            raw_keyfile_json=user_account.get("keyfile_json"),
            password=user_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 500001"))
        )

        # update
        _data = {
            "cancellation_date": "20211231"
        }
        _add_data = UpdateParams(**_data)
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.update(
                data=_add_data,
                tx_from=user_address,
                private_key=user_private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender is not contract owner."


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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=from_address,
            private_key=from_private_key
        )

        # transfer
        _data = {
            "from_address": from_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = TransferParams(**_data)
        share_contract.transfer(
            data=_transfer_data,
            tx_from=from_address,
            private_key=from_private_key
        )

        # assertion
        from_balance = share_contract.get_account_balance(from_address)
        to_balance = share_contract.get_account_balance(to_address)
        assert from_balance == arguments[3] - 10
        assert to_balance == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation (TransferParams)
    # required field
    def test_error_1(self, db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            TransferParams(**_data)
        assert exc_info.value.errors() == [
            {
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
    # validation (TransferParams)
    # invalid parameter
    def test_error_2(self, db):
        _data = {
            "from_address": "invalid from_address",
            "to_address": "invalid to_address",
            "amount": 0
        }
        with pytest.raises(ValidationError) as exc_info:
            TransferParams(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("from_address",),
                "msg": "from_address is not a valid address",
                "type": "value_error"
            },
            {
                "loc": ("to_address",),
                "msg": "to_address is not a valid address",
                "type": "value_error"
            },
            {
                'loc': ('amount',),
                'msg': 'ensure this value is greater than 0',
                'type': 'value_error.number.not_gt',
                'ctx': {'limit_value': 0}
            }
        ]

    # <Error_3>
    # invalid tx_from
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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=from_address,
            private_key=from_private_key
        )

        # transfer
        _data = {
            "from_address": from_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = TransferParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.transfer(
                data=_transfer_data,
                tx_from="invalid_tx_from",
                private_key=from_private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

    # <Error_4>
    # invalid private key
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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=from_address,
            private_key=from_private_key
        )

        # transfer
        _data = {
            "from_address": from_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = TransferParams(**_data)
        with pytest.raises(SendTransactionError):
            share_contract.transfer(
                data=_transfer_data,
                tx_from=from_address,
                private_key="invalid_private_key"
            )

    # <Error_5>
    # TimeExhausted
    def test_error_5(self, db):
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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TimeExhausted
        )

        # transfer
        _data = {
            "from_address": issuer_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = TransferParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.transfer(
                    data=_transfer_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_6>
    # Error
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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound
        )

        # transfer
        _data = {
            "from_address": issuer_address,
            "to_address": to_address,
            "amount": 10
        }
        _transfer_data = TransferParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.transfer(
                    data=_transfer_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_7>
    # Transaction REVERT(insufficient balance)
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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # transfer with insufficient balance
        _data = {
            "from_address": issuer_address,
            "to_address": to_address,
            "amount": 10000000
        }
        _transfer_data = TransferParams(**_data)

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 110401"))
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.transfer(
                data=_transfer_data,
                tx_from=issuer_address,
                private_key=private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender balance is insufficient."


class TestAdditionalIssue:

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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # additional issue
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = AdditionalIssueParams(**_data)
        pre_datetime = datetime.utcnow()
        share_contract.additional_issue(
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract_attr = share_contract.get()
        assert share_contract_attr.total_supply == arguments[3] + 10

        balance = share_contract.get_account_balance(issuer_address)
        assert balance == arguments[3] + 10

        _token_attr_update = db.query(TokenAttrUpdate).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid parameter (AdditionalIssueParams)
    def test_error_1(self, db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            AdditionalIssueParams(**_data)
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
    # invalid parameter (AdditionalIssueParams)
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        _data = {
            "account_address": issuer_address[:-1],  # short address
            "amount": 0
        }

        with pytest.raises(ValidationError) as exc_info:
            AdditionalIssueParams(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("account_address",),
                "msg": "account_address is not a valid address",
                "type": "value_error"
            },
            {
                'loc': ('amount',),
                'msg': 'ensure this value is greater than 0',
                'type': 'value_error.number.not_gt',
                'ctx': {'limit_value': 0}
            }
        ]

    # <Error_3>
    # invalid tx_from
    def test_error_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # additional issue
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = AdditionalIssueParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.additional_issue(
                data=_add_data,
                tx_from="invalid_tx_from",
                private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

    # <Error_4>
    # invalid private key
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # additional issue
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = AdditionalIssueParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.additional_issue(
                data=_add_data,
                tx_from=test_account.get("address"),
                private_key="invalid_private_key"
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # TimeExhausted
    def test_error_5(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TimeExhausted
        )

        # additional issue
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = AdditionalIssueParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.additional_issue(
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_6>
    # Error
    def test_error_6(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound
        )

        # additional issue
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = AdditionalIssueParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.additional_issue(
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_7>
    # Transaction REVERT(not owner)
    def test_error_7(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        user_account = config_eth_account("user2")
        user_address = user_account.get("address")
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )
        user_private_key = decode_keyfile_json(
            raw_keyfile_json=user_account.get("keyfile_json"),
            password=user_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_private_key
        )

        # additional issue
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = AdditionalIssueParams(**_data)
        pre_datetime = datetime.utcnow()

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 500001"))
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.additional_issue(
                data=_add_data,
                tx_from=user_address,
                private_key=user_private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender is not contract owner."


class TestRedeem:

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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # redeem
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = RedeemParams(**_data)
        pre_datetime = datetime.utcnow()
        share_contract.redeem(
            data=_add_data,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        share_contract_attr = share_contract.get()
        assert share_contract_attr.total_supply == arguments[3] - 10

        balance = share_contract.get_account_balance(issuer_address)
        assert balance == arguments[3] - 10

        _token_attr_update = db.query(TokenAttrUpdate).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid parameter (RedeemParams)
    def test_error_1(self, db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            RedeemParams(**_data)
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
    # invalid parameter (RedeemParams)
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        _data = {
            "account_address": issuer_address[:-1],  # short address
            "amount": 0
        }

        with pytest.raises(ValidationError) as exc_info:
            RedeemParams(**_data)
        assert exc_info.value.errors() == [
            {
                "loc": ("account_address",),
                "msg": "account_address is not a valid address",
                "type": "value_error"
            },
            {
                'loc': ('amount',),
                'msg': 'ensure this value is greater than 0',
                'type': 'value_error.number.not_gt',
                'ctx': {'limit_value': 0}
            }
        ]

    # <Error_3>
    # invalid tx_from
    def test_error_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # redeem
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = RedeemParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.redeem(
                data=_add_data,
                tx_from="invalid_tx_from",
                private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

    # <Error_4>
    # invalid private key
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # redeem
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = RedeemParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.redeem(
                data=_add_data,
                tx_from=test_account.get("address"),
                private_key="invalid_private_key"
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # TimeExhausted
    def test_error_5(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TimeExhausted
        )

        # redeem
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = RedeemParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.redeem(
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_6>
    # Error
    def test_error_6(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound
        )

        # redeem
        _data = {
            "account_address": issuer_address,
            "amount": 10
        }
        _add_data = RedeemParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.redeem(
                    data=_add_data,
                    tx_from=issuer_address,
                    private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_7>
    # Transaction REVERT(lack balance)
    def test_error_7(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # redeem
        _data = {
            "account_address": issuer_address,
            "amount": 100_000_000
        }
        _add_data = RedeemParams(**_data)
        pre_datetime = datetime.utcnow()

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 111102"))
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.redeem(
                data=_add_data,
                tx_from=issuer_address,
                private_key=private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Redeem amount is less than target address balance."


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
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # assertion
        balance = share_contract.get_account_balance(issuer_address)
        assert balance == arguments[3]

    # <Normal_2>
    # not deployed contract_address
    def test_normal_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        # execute the function
        share_contract = IbetShareContract(ZERO_ADDRESS)
        balance = share_contract.get_account_balance(issuer_address)

        # assertion
        assert balance == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid account_address
    def test_error_1(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # execute the function
        with pytest.raises(Web3ValidationError):
            share_contract.get_account_balance(
                issuer_address[:-1]  # short
            )


class TestCheckAttrUpdate:
    token_address = "0x0123456789abcDEF0123456789abCDef01234567"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # not exists
    def test_normal_1(self, db):
        before_datetime = datetime.utcnow()

        # Test
        share_contract = IbetShareContract(self.token_address)
        result = share_contract.check_attr_update(db, before_datetime)

        # assertion
        assert result is False

    # <Normal_2>
    # prev data exists
    def test_normal_2(self, db):
        before_datetime = datetime.utcnow()
        time.sleep(1)
        after_datetime = datetime.utcnow()

        # prepare data
        _update = TokenAttrUpdate()
        _update.token_address = self.token_address
        _update.updated_datetime = before_datetime
        db.add(_update)
        db.commit()

        # Test
        share_contract = IbetShareContract(self.token_address)
        result = share_contract.check_attr_update(db, after_datetime)

        # assertion
        assert result is False

    # <Normal_3>
    # next data exists
    def test_normal_3(self, db):
        before_datetime = datetime.utcnow()
        time.sleep(1)
        after_datetime = datetime.utcnow()

        # prepare data
        _update = TokenAttrUpdate()
        _update.token_address = self.token_address
        _update.updated_datetime = after_datetime
        db.add(_update)
        db.commit()

        # Test
        share_contract = IbetShareContract(self.token_address)
        result = share_contract.check_attr_update(db, before_datetime)

        # assertion
        assert result is True

    ###########################################################################
    # Error Case
    ###########################################################################


class TestRecordAttrUpdate:
    token_address = "0x0123456789abcDEF0123456789abCDef01234567"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # data not exists
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_1(self, db):
        # Test
        share_contract = IbetShareContract(self.token_address)
        share_contract.record_attr_update(db)

        # assertion
        _update = db.query(TokenAttrUpdate).first()
        assert _update.id == 1
        assert _update.token_address == self.token_address
        assert _update.updated_datetime == datetime(2021, 4, 27, 12, 34, 56)

    # <Normal_2>
    # data exists
    def test_normal_2(self, db, freezer):

        # prepare data
        _update = TokenAttrUpdate()
        _update.token_address = self.token_address
        _update.updated_datetime = datetime.utcnow()
        db.add(_update)
        db.commit()

        # Mock datetime
        freezer.move_to('2021-04-27 12:34:56')

        # Test
        share_contract = IbetShareContract(self.token_address)
        share_contract.record_attr_update(db)

        # assertion
        _update = db.query(TokenAttrUpdate).filter(TokenAttrUpdate.id == 2).first()
        assert _update.id == 2
        assert _update.token_address == self.token_address
        assert _update.updated_datetime == datetime(2021, 4, 27, 12, 34, 56)

    ###########################################################################
    # Error Case
    ###########################################################################


class TestApproveTransfer:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        to_account = config_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8")
        )

        deployer = config_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8")
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk
        )

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True
        }
        share_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"]
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"]
        )

        # approve transfer (from issuer)
        approve_data = {
            "application_id": 0,
            "data": "approve transfer test"
        }
        tx_hash, tx_receipt = share_contract.approve_transfer(
            data=ApproveTransferParams(**approve_data),
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        share_token = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=token_address
        )
        applications = share_token.functions.applicationsForTransfer(0).call()
        assert applications[0] == issuer_address
        assert applications[1] == to_address
        assert applications[2] == 10
        assert applications[3] is False

        pendingTransfer = share_token.functions.pendingTransfer(issuer_address).call()
        issuer_value = share_token.functions.balanceOf(issuer_address).call()
        to_value = share_token.functions.balanceOf(to_address).call()
        assert pendingTransfer == 0
        assert issuer_value == (20000 - 10)
        assert to_value == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid application index : not integer, data : missing
    def test_error_1(self, db):
        # Transfer approve
        approve_data = {
            "application_id": "not-integer",
        }
        with pytest.raises(ValidationError) as ex_info:
            _approve_transfer_data = ApproveTransferParams(**approve_data)

        assert ex_info.value.errors() == [
            {
                'loc': ('application_id',),
                'msg': 'value is not a valid integer',
                'type': 'type_error.integer'
            }, {
                'loc': ('data',),
                'msg': 'field required',
                'type': 'value_error.missing'
            }
        ]

    # <Error_2>
    # invalid contract_address : does not exists
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # Transfer approve
        approve_data = {
            "application_id": 0,
            "data": "test_data"
        }
        _approve_transfer_data = ApproveTransferParams(**approve_data)
        share_contract = IbetShareContract("not address")
        with pytest.raises(SendTransactionError) as ex_info:
            share_contract.approve_transfer(
                data=_approve_transfer_data,
                tx_from=issuer_address,
                private_key=private_key
            )
        assert ex_info.match("when sending a str, it must be a hex string. Got: 'not address'")

    # <Error_3>
    # invalid issuer_address : does not exists
    def test_error_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # Transfer approve
        approve_data = {
            "application_id": 0,
            "data": "test_data"
        }
        _approve_transfer_data = ApproveTransferParams(**approve_data)
        with pytest.raises(SendTransactionError) as ex_info:
            share_contract.approve_transfer(
                data=_approve_transfer_data,
                tx_from=issuer_address[:-1],
                private_key=private_key
            )
        assert ex_info.match(f"ENS name: '{issuer_address[:-1]}' is invalid.")

    # <Error_4>
    # invalid private_key : not properly
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]

        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # Transfer approve
        approve_data = {
            "application_id": 0,
            "data": "test_data"
        }
        _approve_transfer_data = ApproveTransferParams(**approve_data)
        with pytest.raises(SendTransactionError) as ex_info:
            share_contract.approve_transfer(
                data=_approve_transfer_data,
                tx_from=issuer_address,
                private_key="dummy-private"
            )
        assert ex_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # Transaction REVERT(application invalid)
    def test_error_5(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        to_account = config_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8")
        )

        deployer = config_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8")
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True
        }
        share_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"]
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"]
        )

        # approve transfer (from issuer)
        approve_data = {
            "application_id": 0,
            "data": "approve transfer test"
        }
        share_contract.approve_transfer(
            data=ApproveTransferParams(**approve_data),
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # Then send approveTransfer transaction again.
        # This would be failed.

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 120902"))
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.approve_transfer(
                data=ApproveTransferParams(**approve_data),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

        # assertion
        assert exc_info.value.args[0] == "Application is invalid."


class TestCancelTransfer:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        to_account = config_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8")
        )

        deployer = config_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8")
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk
        )

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True
        }
        share_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"]
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"]
        )

        # cancel transfer (from issuer)
        cancel_data = {
            "application_id": 0,
            "data": "approve transfer test"
        }
        _approve_transfer_data = CancelTransferParams(**cancel_data)

        tx_hash, tx_receipt = share_contract.cancel_transfer(
            data=_approve_transfer_data,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1
        share_token = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=token_address
        )
        applications = share_token.functions.applicationsForTransfer(0).call()
        assert applications[0] == issuer_address
        assert applications[1] == to_address
        assert applications[2] == 10
        assert applications[3] is False
        pendingTransfer = share_token.functions.pendingTransfer(issuer_address).call()
        issuer_value = share_token.functions.balanceOf(issuer_address).call()
        to_value = share_token.functions.balanceOf(to_address).call()
        assert pendingTransfer == 0
        assert issuer_value == 20000
        assert to_value == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid application index : not integer, data : missing
    def test_error_1(self, db):
        # Transfer approve
        cancel_data = {
            "application_id": "not-integer",
        }
        with pytest.raises(ValidationError) as ex_info:
            _approve_transfer_data = CancelTransferParams(**cancel_data)

        assert ex_info.value.errors() == [
            {
                'loc': ('application_id',),
                'msg': 'value is not a valid integer',
                'type': 'type_error.integer'
            }, {
                'loc': ('data',),
                'msg': 'field required',
                'type': 'value_error.missing'
            }
        ]

    # <Error_2>
    # invalid contract_address : does not exists
    def test_error_2(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # Transfer cancel
        cancel_data = {
            "application_id": 0,
            "data": "test_data"
        }
        _cancel_transfer_data = CancelTransferParams(**cancel_data)
        share_contract = IbetShareContract("not address")
        with pytest.raises(SendTransactionError) as ex_info:
            share_contract.cancel_transfer(
                data=_cancel_transfer_data,
                tx_from=issuer_address,
                private_key=private_key
            )
        assert ex_info.match("when sending a str, it must be a hex string. Got: 'not address'")

    # <Error_3>
    # invalid issuer_address : does not exists
    def test_error_3(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]

        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # Transfer cancel
        cancel_data = {
            "application_id": 0,
            "data": "test_data"
        }
        _cancel_transfer_data = CancelTransferParams(**cancel_data)
        with pytest.raises(SendTransactionError) as ex_info:
            share_contract.cancel_transfer(
                data=_cancel_transfer_data,
                tx_from=issuer_address[:-1],
                private_key=private_key
            )
        assert ex_info.match(f"ENS name: '{issuer_address[:-1]}' is invalid.")

    # <Error_4>
    # invalid private_key : not properly
    def test_error_4(self, db):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8")
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]

        share_contract = IbetShareContract()
        contract_address, abi, tx_hash = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )

        # Transfer cancel
        cancel_data = {
            "application_id": 0,
            "data": "test_data"
        }
        _cancel_transfer_data = CancelTransferParams(**cancel_data)
        with pytest.raises(SendTransactionError) as ex_info:
            share_contract.cancel_transfer(
                data=_cancel_transfer_data,
                tx_from=issuer_address,
                private_key="dummy-private"
            )
        assert ex_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # Transaction REVERT(application invalid)
    def test_error_5(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        to_account = config_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8")
        )

        deployer = config_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8")
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk
        )

        # deploy token
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True
        }
        share_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"]
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"]
        )

        # approve transfer (from issuer)
        approve_data = {
            "application_id": 0,
            "data": "approve transfer test"
        }
        share_contract.approve_transfer(
            data=ApproveTransferParams(**approve_data),
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # Then send cancelTransfer transaction. This would be failed.
        cancel_data = approve_data

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 120802"))
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.cancel_transfer(
                data=CancelTransferParams(**cancel_data),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

        # assertion
        assert exc_info.value.args[0] == "Application is invalid."


class TestLock:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        tx_hash, tx_receipt = share_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        share_token = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=token_address
        )
        lock_amount = share_token.functions.lockedOf(lock_address, issuer_address).call()
        assert lock_amount == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # ValidationError
    # field required
    def test_error_1_1(self, db):
        lock_data = {}
        with pytest.raises(ValidationError) as ex_info:
            LockParams(**lock_data)

        assert ex_info.value.errors() == [
            {
                'loc': ('lock_address',),
                'msg': 'field required',
                'type': 'value_error.missing'
            },
            {
                'loc': ('value',),
                'msg': 'field required',
                'type': 'value_error.missing'
            },
            {
                'loc': ('data',),
                'msg': 'field required',
                'type': 'value_error.missing'}
        ]

    # <Error_1_2>
    # ValidationError
    # - lock_address is not a valid address
    # - value is not greater than 0
    def test_error_1_2(self, db):
        lock_data = {
            "lock_address": "test_address",
            "value": 0,
            "data": ""
        }
        with pytest.raises(ValidationError) as ex_info:
            LockParams(**lock_data)

        assert ex_info.value.errors() == [
            {
                'loc': ('lock_address',),
                'msg': 'lock_address is not a valid address',
                'type': 'value_error'
            },
            {
                'loc': ('value',),
                'msg': 'ensure this value is greater than 0',
                'type': 'value_error.number.not_gt',
                'ctx': {'limit_value': 0}
            }
        ]

    # <Error_2_1>
    # SendTransactionError
    # Invalid tx_from
    def test_error_2_1(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.lock(
                data=LockParams(**lock_data),
                tx_from="invalid_tx_from",  # invalid tx from
                private_key="",
            )

        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

    # <Error_2_2>
    # SendTransactionError
    # Invalid pk
    def test_error_2_2(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.lock(
                data=LockParams(**lock_data),
                tx_from=issuer_address,
                private_key="invalid_pk",  # invalid pk
            )

        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_3>
    # SendTransactionError
    # TimeExhausted
    def test_error_3(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TimeExhausted
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.lock(
                    data=LockParams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk
                )

        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_4>
    # SendTransactionError
    # TransactionNotFound
    def test_error_4(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.lock(
                    data=LockParams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk
                )

        assert exc_info.type(SendTransactionError(TransactionNotFound))

    # <Error_5>
    # ContractRevertError
    def test_error_5(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 110002"))
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 20001,
            "data": ""
        }
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.lock(
                data=LockParams(**lock_data),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

        # assertion
        assert exc_info.value.code == 110002
        assert exc_info.value.message == "Lock amount is greater than message sender balance."


class TestForceUnlock:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        share_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 5,
            "data": ""
        }
        tx_hash, tx_receipt = share_contract.force_unlock(
            data=ForceUnlockPrams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        share_token = ContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address=token_address
        )
        lock_amount = share_token.functions.lockedOf(lock_address, issuer_address).call()
        assert lock_amount == 5

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # ValidationError
    # field required
    def test_error_1_1(self, db):
        lock_data = {}
        with pytest.raises(ValidationError) as ex_info:
            ForceUnlockPrams(**lock_data)

        assert ex_info.value.errors() == [
            {
                'loc': ('lock_address',),
                'msg': 'field required',
                'type': 'value_error.missing'
            },
            {
                'loc': ('account_address',),
                'msg': 'field required',
                'type': 'value_error.missing'
            },
            {
                'loc': ('recipient_address',),
                'msg': 'field required',
                'type': 'value_error.missing'
            },
            {
                'loc': ('value',),
                'msg': 'field required',
                'type': 'value_error.missing'
            },
            {
                'loc': ('data',),
                'msg': 'field required',
                'type': 'value_error.missing'
            }
        ]

    # <Error_1_2>
    # ValidationError
    # - address is not a valid address
    # - value is not greater than 0
    def test_error_1_2(self, db):
        lock_data = {
            "lock_address": "test_address",
            "account_address": "test_address",
            "recipient_address": "test_address",
            "value": 0,
            "data": ""
        }
        with pytest.raises(ValidationError) as ex_info:
            ForceUnlockPrams(**lock_data)

        assert ex_info.value.errors() == [
            {
                'loc': ('lock_address',),
                'msg': 'lock_address is not a valid address',
                'type': 'value_error'
            },
            {
                'loc': ('account_address',),
                'msg': 'account_address is not a valid address',
                'type': 'value_error'
            },
            {
                'loc': ('recipient_address',),
                'msg': 'recipient_address is not a valid address',
                'type': 'value_error'
            },
            {
                'loc': ('value',),
                'msg': 'ensure this value is greater than 0',
                'type': 'value_error.number.not_gt',
                'ctx': {'limit_value': 0}
            }
        ]

    # <Error_2_1>
    # SendTransactionError
    # Invalid tx_from
    def test_error_2_1(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        share_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 5,
            "data": ""
        }
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.force_unlock(
                data=ForceUnlockPrams(**lock_data),
                tx_from="invalid_tx_from",  # invalid tx from
                private_key="",
            )

        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: \'invalid_tx_from\' is invalid.")

    # <Error_2_2>
    # SendTransactionError
    # Invalid pk
    def test_error_2_2(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        share_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 5,
            "data": ""
        }
        with pytest.raises(SendTransactionError) as exc_info:
            share_contract.force_unlock(
                data=ForceUnlockPrams(**lock_data),
                tx_from=issuer_address,
                private_key="invalid_pk",  # invalid pk
            )

        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_3>
    # SendTransactionError
    # TimeExhausted
    def test_error_3(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        share_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TimeExhausted
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 5,
            "data": ""
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.force_unlock(
                    data=ForceUnlockPrams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk
                )

        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_4>
    # SendTransactionError
    # TransactionNotFound
    def test_error_4(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        share_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 5,
            "data": ""
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                share_contract.force_unlock(
                    data=ForceUnlockPrams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk
                )

        assert exc_info.type(SendTransactionError(TransactionNotFound))

    # <Error_5>
    # ContractRevertError
    def test_error_5(self, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8")
        )

        lock_account = config_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet share token (from issuer)
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = share_contract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=issuer_pk
        )

        # lock
        lock_data = {
            "lock_address": lock_address,
            "value": 10,
            "data": ""
        }
        share_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        InspectionMock = mock.patch(
            "web3.eth.Eth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 111201"))
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 11,
            "data": ""
        }
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            share_contract.force_unlock(
                data=ForceUnlockPrams(**lock_data),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

        # assertion
        assert exc_info.value.code == 111201
        assert exc_info.value.message == "Unlock amount is greater than locked amount."
