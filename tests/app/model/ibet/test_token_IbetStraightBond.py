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
import time
from binascii import Error
from datetime import UTC, datetime, timedelta
from unittest import mock
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from eth_keyfile import decode_keyfile_json
from pydantic import ValidationError
from sqlalchemy import select
from web3 import Web3
from web3.exceptions import (
    ContractLogicError,
    InvalidAddress,
    MismatchedABI,
    TimeExhausted,
    TransactionNotFound,
)
from web3.middleware import ExtraDataToPOAMiddleware

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import TokenAttrUpdate, TokenCache
from app.model.ibet import IbetStraightBondContract
from app.model.ibet.tx_params.ibet_straight_bond import (
    AdditionalIssueParams,
    ApproveTransferParams,
    BulkTransferParams,
    CancelTransferParams,
    ForceChangeLockedAccountParams,
    ForcedTransferParams,
    ForceLockParams,
    ForceUnlockPrams,
    LockParams,
    RedeemParams,
    UpdateParams,
)
from app.utils.ibet_contract_utils import AsyncContractUtils, ContractUtils
from config import DEFAULT_CURRENCY, TOKEN_CACHE_TTL, WEB3_HTTP_PROVIDER, ZERO_ADDRESS
from tests.account_config import default_eth_account
from tests.contract_utils import (
    IbetSecurityTokenContractTestUtils,
    PersonalInfoContractTestUtils,
)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestCreate:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # execute the function
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        contract_address, _, _ = await IbetStraightBondContract().create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        bond_contract = ContractUtils.get_contract(
            contract_name="IbetStraightBond", contract_address=contract_address
        )
        assert bond_contract.functions.owner().call() == issuer_address
        assert bond_contract.functions.name().call() == "テスト債券"
        assert bond_contract.functions.symbol().call() == "TEST"
        assert bond_contract.functions.totalSupply().call() == 10000
        assert bond_contract.functions.faceValue().call() == 20000
        assert bond_contract.functions.faceValueCurrency().call() == "JPY"
        assert bond_contract.functions.redemptionDate().call() == "20211231"
        assert bond_contract.functions.redemptionValue().call() == 30000
        assert bond_contract.functions.redemptionValueCurrency().call() == "JPY"
        assert bond_contract.functions.returnDate().call() == "20211231"
        assert bond_contract.functions.returnAmount().call() == "リターン内容"
        assert bond_contract.functions.purpose().call() == "発行目的"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Invalid argument (args length)
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # execute the function
        arguments = []
        with pytest.raises(SendTransactionError) as exc_info:
            await IbetStraightBondContract().create(
                args=arguments, tx_from=issuer_address, private_key=private_key
            )

        # assertion
        assert isinstance(exc_info.value.args[0], TypeError)
        assert exc_info.match("Incorrect argument count.")

    # <Error_2>
    # Invalid argument type (args)
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
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
            0,
            0,
            0,
        ]  # invalid types
        with pytest.raises(SendTransactionError) as exc_info:
            await IbetStraightBondContract().create(
                args=arguments, tx_from=issuer_address, private_key=private_key
            )

        # assertion
        assert isinstance(exc_info.value.args[0], TypeError)
        assert exc_info.match(
            "One or more arguments could not be encoded to the necessary ABI type."
        )

    # <Error_3>
    # Invalid argument type (tx_from)
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # execute the function
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        with pytest.raises(SendTransactionError) as exc_info:
            await IbetStraightBondContract().create(
                args=arguments,
                tx_from=issuer_address[:-1],  # short address
                private_key=private_key,
            )

        # assertion
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: '.+' is invalid.")

    # <Error_4>
    # Invalid argument type (private_key)
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")

        # execute the function
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        with pytest.raises(SendTransactionError) as exc_info:
            await IbetStraightBondContract().create(
                args=arguments, tx_from=issuer_address, private_key="some_private_key"
            )

        # assertion
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # Already deployed
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # execute the function
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        contract_address, _, _ = await IbetStraightBondContract().create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        with pytest.raises(SendTransactionError) as exc_info:
            await IbetStraightBondContract(contract_address).create(
                args=arguments, tx_from=issuer_address, private_key=private_key
            )
        # assertion
        assert exc_info.match("contract is already deployed")


class TestGet:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # TOKEN_CACHE is False
    @pytest.mark.asyncio
    @mock.patch("app.model.ibet.token.TOKEN_CACHE", False)
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        contract_address, _, _ = await IbetStraightBondContract().create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # get token data
        bond_contract = await IbetStraightBondContract(contract_address).get()

        # assertion
        assert bond_contract.issuer_address == test_account["address"]
        assert bond_contract.token_address == contract_address
        assert bond_contract.name == arguments[0]
        assert bond_contract.symbol == arguments[1]
        assert bond_contract.total_supply == arguments[2]
        assert bond_contract.contact_information == ""
        assert bond_contract.privacy_policy == ""
        assert bond_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert bond_contract.status is True
        assert bond_contract.personal_info_contract_address == ZERO_ADDRESS
        assert bond_contract.require_personal_info_registered is True
        assert bond_contract.transferable is False
        assert bond_contract.is_offering is False
        assert bond_contract.transfer_approval_required is False
        assert bond_contract.face_value == arguments[3]
        assert bond_contract.face_value_currency == arguments[4]
        assert bond_contract.interest_rate == 0
        assert bond_contract.interest_payment_date == [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert bond_contract.interest_payment_currency == ""
        assert bond_contract.redemption_date == arguments[5]
        assert bond_contract.redemption_value == arguments[6]
        assert bond_contract.redemption_value_currency == arguments[7]
        assert bond_contract.return_date == arguments[8]
        assert bond_contract.return_amount == arguments[9]
        assert bond_contract.base_fx_rate == 0.0
        assert bond_contract.purpose == arguments[10]
        assert bond_contract.memo == ""
        assert bond_contract.is_redeemed is False

    # <Normal_2>
    # TOKEN_CACHE is True
    @pytest.mark.asyncio
    @mock.patch("app.model.ibet.token.TOKEN_CACHE", True)
    async def test_normal_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        contract_address, _, _ = await IbetStraightBondContract(ZERO_ADDRESS).create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # create cache
        token_attr = {
            "issuer_address": issuer_address,
            "token_address": contract_address,
            "name": "テスト債券-test",
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": True,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_cache = TokenCache()
        token_cache.token_address = contract_address
        token_cache.attributes = token_attr
        token_cache.cached_datetime = datetime.now(UTC).replace(tzinfo=None)
        token_cache.expiration_datetime = datetime.now(UTC).replace(
            tzinfo=None
        ) + timedelta(seconds=TOKEN_CACHE_TTL)
        async_db.add(token_cache)
        await async_db.commit()

        # get token data
        bond_contract = await IbetStraightBondContract(contract_address).get()

        # assertion
        assert bond_contract.issuer_address == test_account["address"]
        assert bond_contract.token_address == contract_address
        assert bond_contract.name == "テスト債券-test"
        assert bond_contract.symbol == "TEST-test"
        assert bond_contract.total_supply == 9999999
        assert bond_contract.contact_information == "test1"
        assert bond_contract.privacy_policy == "test2"
        assert (
            bond_contract.tradable_exchange_contract_address
            == "0x1234567890123456789012345678901234567890"
        )
        assert bond_contract.status is False
        assert (
            bond_contract.personal_info_contract_address
            == "0x1234567890123456789012345678901234567891"
        )
        assert bond_contract.require_personal_info_registered is True
        assert bond_contract.transferable is True
        assert bond_contract.is_offering is True
        assert bond_contract.transfer_approval_required is True
        assert bond_contract.face_value == 9999998
        assert bond_contract.face_value_currency == "JPY"
        assert bond_contract.interest_rate == 99.999
        assert bond_contract.interest_payment_date == [
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
            "99991231",
        ]
        assert bond_contract.interest_payment_currency == "JPY"
        assert bond_contract.redemption_date == "99991231"
        assert bond_contract.redemption_value == 9999997
        assert bond_contract.redemption_value_currency == "JPY"
        assert bond_contract.return_date == "99991230"
        assert bond_contract.return_amount == "return_amount-test"
        assert bond_contract.base_fx_rate == 123.456789
        assert bond_contract.purpose == "purpose-test"
        assert bond_contract.memo == "memo-test"
        assert bond_contract.is_redeemed is True

    # <Normal_3>
    # TOKEN_CACHE is True, updated token attribute
    @pytest.mark.asyncio
    @mock.patch("app.model.ibet.token.TOKEN_CACHE", True)
    async def test_normal_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        contract_address, _, _ = await IbetStraightBondContract(ZERO_ADDRESS).create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # create cache
        token_attr = {
            "issuer_address": issuer_address,
            "token_address": contract_address,
            "name": "テスト債券-test",
            "symbol": "TEST-test",
            "total_supply": 9999999,
            "contact_information": "test1",
            "privacy_policy": "test2",
            "tradable_exchange_contract_address": "0x1234567890123456789012345678901234567890",
            "status": False,
            "personal_info_contract_address": "0x1234567890123456789012345678901234567891",
            "require_personal_info_registered": False,
            "transferable": True,
            "is_offering": True,
            "transfer_approval_required": True,
            "face_value": 9999998,
            "face_value_currency": "JPY",
            "interest_rate": 99.999,
            "interest_payment_date": [
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
                "99991231",
            ],
            "interest_payment_currency": "JPY",
            "redemption_date": "99991231",
            "redemption_value": 9999997,
            "redemption_value_currency": "JPY",
            "return_date": "99991230",
            "return_amount": "return_amount-test",
            "base_fx_rate": 123.456789,
            "purpose": "purpose-test",
            "memo": "memo-test",
            "is_redeemed": True,
        }
        token_cache = TokenCache()
        token_cache.token_address = contract_address
        token_cache.attributes = token_attr
        token_cache.cached_datetime = datetime.now(UTC).replace(tzinfo=None)
        token_cache.expiration_datetime = datetime.now(UTC).replace(
            tzinfo=None
        ) + timedelta(seconds=TOKEN_CACHE_TTL)
        async_db.add(token_cache)

        # updated token attribute
        _token_attr_update = TokenAttrUpdate()
        _token_attr_update.token_address = contract_address
        _token_attr_update.updated_datetime = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_token_attr_update)
        await async_db.commit()

        # get token data
        bond_contract = await IbetStraightBondContract(contract_address).get()

        # assertion
        assert bond_contract.issuer_address == test_account["address"]
        assert bond_contract.token_address == contract_address
        assert bond_contract.name == arguments[0]
        assert bond_contract.symbol == arguments[1]
        assert bond_contract.total_supply == arguments[2]
        assert bond_contract.contact_information == ""
        assert bond_contract.privacy_policy == ""
        assert bond_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert bond_contract.status is True
        assert bond_contract.personal_info_contract_address == ZERO_ADDRESS
        assert bond_contract.require_personal_info_registered is True
        assert bond_contract.transferable is False
        assert bond_contract.is_offering is False
        assert bond_contract.transfer_approval_required is False
        assert bond_contract.face_value == arguments[3]
        assert bond_contract.face_value_currency == arguments[4]
        assert bond_contract.interest_rate == 0
        assert bond_contract.interest_payment_date == [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert bond_contract.interest_payment_currency == ""
        assert bond_contract.redemption_date == arguments[5]
        assert bond_contract.redemption_value == arguments[6]
        assert bond_contract.redemption_value_currency == arguments[7]
        assert bond_contract.return_date == arguments[8]
        assert bond_contract.return_amount == arguments[9]
        assert bond_contract.base_fx_rate == 0.0
        assert bond_contract.purpose == arguments[10]
        assert bond_contract.memo == ""
        assert bond_contract.is_redeemed is False

    # <Normal_4>
    # contract_address not deployed
    @pytest.mark.asyncio
    async def test_normal_4(self, async_db):
        # get token data
        bond_contract = await IbetStraightBondContract(ZERO_ADDRESS).get()

        # assertion
        assert bond_contract.issuer_address == ZERO_ADDRESS
        assert bond_contract.token_address == ZERO_ADDRESS
        assert bond_contract.name == ""
        assert bond_contract.symbol == ""
        assert bond_contract.total_supply == 0
        assert bond_contract.contact_information == ""
        assert bond_contract.privacy_policy == ""
        assert bond_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert bond_contract.status is True
        assert bond_contract.personal_info_contract_address == ZERO_ADDRESS
        assert bond_contract.require_personal_info_registered is True
        assert bond_contract.transferable is False
        assert bond_contract.is_offering is False
        assert bond_contract.transfer_approval_required is False
        assert bond_contract.face_value == 0
        assert bond_contract.face_value_currency == DEFAULT_CURRENCY
        assert bond_contract.interest_rate == 0
        assert bond_contract.interest_payment_date == [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert bond_contract.interest_payment_currency == ""
        assert bond_contract.redemption_date == ""
        assert bond_contract.redemption_value == 0
        assert bond_contract.redemption_value_currency == ""
        assert bond_contract.return_date == ""
        assert bond_contract.return_amount == ""
        assert bond_contract.base_fx_rate == 0.0
        assert bond_contract.purpose == ""
        assert bond_contract.memo == ""
        assert bond_contract.is_redeemed is False

    ###########################################################################
    # Error Case
    ###########################################################################


class TestUpdate:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # All items are None
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        contract_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # update
        _data = {}
        _add_data = UpdateParams(**_data)
        pre_datetime = datetime.now(UTC).replace(tzinfo=None)
        await bond_contract.update(
            data=_add_data, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        bond_contract = await bond_contract.get()
        assert bond_contract.face_value == arguments[3]
        assert bond_contract.face_value_currency == arguments[4]
        assert bond_contract.interest_rate == 0
        assert bond_contract.interest_payment_date == [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert bond_contract.interest_payment_currency == ""
        assert bond_contract.redemption_date == arguments[5]
        assert bond_contract.redemption_value == arguments[6]
        assert bond_contract.redemption_value_currency == arguments[7]
        assert bond_contract.return_date == arguments[8]
        assert bond_contract.return_amount == arguments[9]
        assert bond_contract.base_fx_rate == 0.0
        assert bond_contract.purpose == arguments[10]
        assert bond_contract.transferable is False
        assert bond_contract.status is True
        assert bond_contract.is_offering is False
        assert bond_contract.is_redeemed is False
        assert bond_contract.tradable_exchange_contract_address == ZERO_ADDRESS
        assert bond_contract.personal_info_contract_address == ZERO_ADDRESS
        assert bond_contract.require_personal_info_registered is True
        assert bond_contract.contact_information == ""
        assert bond_contract.privacy_policy == ""
        assert bond_contract.transfer_approval_required is False
        assert bond_contract.memo == ""

        _token_attr_update = (
            await async_db.scalars(select(TokenAttrUpdate).limit(1))
        ).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    # <Normal_2>
    # Update all items
    @pytest.mark.asyncio
    async def test_normal_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        contract_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # update
        _data = {
            "face_value": 20001,
            "face_value_currency": "USD",
            "interest_rate": 0.0001,
            "interest_payment_date": ["0331", "0930"],
            "interest_payment_currency": "USD",
            "redemption_value": 30001,
            "redemption_value_currency": "USD",
            "base_fx_rate": 123.456789,
            "transferable": True,
            "status": False,
            "is_offering": True,
            "is_redeemed": True,
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",
            "require_personal_info_registered": False,
            "contact_information": "contact info test",
            "privacy_policy": "privacy policy test",
            "transfer_approval_required": True,
            "memo": "memo test",
        }
        _add_data = UpdateParams(**_data)
        pre_datetime = datetime.now(UTC).replace(tzinfo=None)
        await bond_contract.update(
            data=_add_data, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        bond_contract = await bond_contract.get()
        assert bond_contract.face_value == 20001
        assert bond_contract.face_value_currency == "USD"
        assert bond_contract.interest_rate == 0.0001
        assert bond_contract.interest_payment_date == [
            "0331",
            "0930",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        assert bond_contract.interest_payment_currency == "USD"
        assert bond_contract.redemption_value == 30001
        assert bond_contract.redemption_value_currency == "USD"
        assert bond_contract.base_fx_rate == 123.456789
        assert bond_contract.transferable is True
        assert bond_contract.status is False
        assert bond_contract.is_offering is True
        assert bond_contract.is_redeemed is True
        assert (
            bond_contract.tradable_exchange_contract_address
            == "0x0000000000000000000000000000000000000001"
        )
        assert (
            bond_contract.personal_info_contract_address
            == "0x0000000000000000000000000000000000000002"
        )
        assert bond_contract.require_personal_info_registered is False
        assert bond_contract.contact_information == "contact info test"
        assert bond_contract.privacy_policy == "privacy policy test"
        assert bond_contract.transfer_approval_required is True
        assert bond_contract.memo == "memo test"

        _token_attr_update = (
            await async_db.scalars(select(TokenAttrUpdate).limit(1))
        ).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation (UpdateParams)
    # invalid parameter
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        # update
        _data = {
            "base_fx_rate": 123.4567899,
            "interest_rate": 0.00001,
            "interest_payment_date": [
                "0101",
                "0201",
                "0301",
                "0401",
                "0501",
                "0601",
                "0701",
                "0801",
                "0901",
                "1001",
                "1101",
                "1201",
                "1231",
            ],
            "tradable_exchange_contract_address": "invalid contract address",
            "personal_info_contract_address": "invalid contract address",
        }
        with pytest.raises(ValidationError) as exc_info:
            UpdateParams(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": 1e-05,
                "loc": ("interest_rate",),
                "msg": "Value error, interest_rate must be rounded to 4 decimal places",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": [
                    "0101",
                    "0201",
                    "0301",
                    "0401",
                    "0501",
                    "0601",
                    "0701",
                    "0801",
                    "0901",
                    "1001",
                    "1101",
                    "1201",
                    "1231",
                ],
                "loc": ("interest_payment_date",),
                "msg": "Value error, list length of interest_payment_date must be less than "
                "13",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": 123.4567899,
                "loc": ("base_fx_rate",),
                "msg": "Value error, base_fx_rate must be rounded to 6 decimal places",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "invalid contract address",
                "loc": ("tradable_exchange_contract_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "invalid contract address",
                "loc": ("personal_info_contract_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
        ]

    # <Error_2>
    # invalid tx_from
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # update
        _data = {"face_value": 20001}
        _add_data = UpdateParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.update(
                data=_add_data, tx_from="DUMMY", private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'DUMMY' is invalid.")

    # <Error_3>
    # invalid private key
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # update
        _data = {"face_value": 20001}
        _add_data = UpdateParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.update(
                data=_add_data,
                tx_from=issuer_address,
                private_key="invalid private key",
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_4>
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # update
        _data = {"face_value": 20001}
        _add_data = UpdateParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.update(
                    data=_add_data, tx_from=issuer_address, private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_5>
    # Error
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # update
        _data = {"face_value": 20001}
        _add_data = UpdateParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.update(
                    data=_add_data, tx_from=issuer_address, private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_6>
    # Transaction REVERT(not owner)
    @pytest.mark.asyncio
    async def test_error_6(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        user_account = default_eth_account("user2")
        user_address = user_account.get("address")
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )
        user_private_key = decode_keyfile_json(
            raw_keyfile_json=user_account.get("keyfile_json"),
            password=user_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_private_key
        )

        # update
        _data = {"face_value": 20001}
        _add_data = UpdateParams(**_data)

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 500001")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.update(
                data=_add_data, tx_from=user_address, private_key=user_private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender is not contract owner."


class TestForcedTransfer:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_private_key
        )

        # transfer
        _data = {"from_address": from_address, "to_address": to_address, "amount": 10}
        _transfer_data = ForcedTransferParams(**_data)
        await bond_contract.forced_transfer(
            data=_transfer_data, tx_from=from_address, private_key=from_private_key
        )

        # assertion
        from_balance = await bond_contract.get_account_balance(from_address)
        to_balance = await bond_contract.get_account_balance(to_address)
        assert from_balance == arguments[2] - 10
        assert to_balance == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation (TransferParams)
    # required field
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            ForcedTransferParams(**_data)
        assert exc_info.value.errors() == [
            {
                "input": {},
                "loc": ("from_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("to_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("amount",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_2>
    # validation (TransferParams)
    # invalid parameter
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        _data = {
            "token_address": "invalid contract address",
            "from_address": "invalid from_address",
            "to_address": "invalid to_address",
            "amount": 0,
        }
        with pytest.raises(ValidationError) as exc_info:
            ForcedTransferParams(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": "invalid from_address",
                "loc": ("from_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "invalid to_address",
                "loc": ("to_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"gt": 0},
                "input": 0,
                "loc": ("amount",),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "url": ANY,
            },
        ]

    # <Error_3>
    # invalid tx_from
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_private_key
        )

        # transfer
        _data = {"from_address": from_address, "to_address": to_address, "amount": 10}
        _transfer_data = ForcedTransferParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.forced_transfer(
                data=_transfer_data,
                tx_from="invalid_tx_from",
                private_key=from_private_key,
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_4>
    # invalid private key
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_private_key
        )

        # transfer
        _data = {"from_address": from_address, "to_address": to_address, "amount": 10}
        _transfer_data = ForcedTransferParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.forced_transfer(
                data=_transfer_data,
                tx_from=from_address,
                private_key="invalid_private_key",
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # transfer
        _data = {"from_address": issuer_address, "to_address": to_address, "amount": 10}
        _transfer_data = ForcedTransferParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.forced_transfer(
                    data=_transfer_data, tx_from=issuer_address, private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_6>
    # Error
    @pytest.mark.asyncio
    async def test_error_6(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # transfer
        _data = {"from_address": issuer_address, "to_address": to_address, "amount": 10}
        _transfer_data = ForcedTransferParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.forced_transfer(
                    data=_transfer_data, tx_from=issuer_address, private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_7>
    # Transaction REVERT(insufficient balance)
    @pytest.mark.asyncio
    async def test_error_7(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # transfer with insufficient balance
        _data = {
            "from_address": issuer_address,
            "to_address": to_address,
            "amount": 10000000,
        }
        _transfer_data = ForcedTransferParams(**_data)

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 120401")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.forced_transfer(
                data=_transfer_data, tx_from=issuer_address, private_key=private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender balance is insufficient."


class TestBulkForcedTransfer:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_private_key
        )

        # bulk transfer
        _data = {"from_address": from_address, "to_address": to_address, "amount": 10}
        transfer_list = [ForcedTransferParams(**_data), ForcedTransferParams(**_data)]
        await bond_contract.bulk_forced_transfer(
            data=transfer_list, tx_from=from_address, private_key=from_private_key
        )

        # assertion
        from_balance = await bond_contract.get_account_balance(from_address)
        to_balance = await bond_contract.get_account_balance(to_address)
        assert from_balance == arguments[2] - 20
        assert to_balance == 20

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_private_key
        )

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            AsyncMock(side_effect=ContractLogicError("execution reverted: 110401")),
        )

        # bulk transfer
        _data = {
            "from_address": from_address,
            "to_address": to_address,
            "amount": arguments[3] + 1,
        }
        transfer_list = [
            ForcedTransferParams(**_data),
        ]
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.bulk_forced_transfer(
                data=transfer_list,
                tx_from=from_address,
                private_key=from_private_key,
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender balance is insufficient."

    # <Error_2>
    # TimeExhausted
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # bulk transfer
        _data = {"from_address": from_address, "to_address": to_address, "amount": 10}
        transfer_list = [ForcedTransferParams(**_data), ForcedTransferParams(**_data)]
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.bulk_forced_transfer(
                    data=transfer_list,
                    tx_from=from_address,
                    private_key=from_private_key,
                )
        # assertion
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_3>
    # Invalid tx_from
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_private_key = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_private_key
        )

        # bulk transfer
        _data = {"from_address": from_address, "to_address": to_address, "amount": 10}
        transfer_list = [ForcedTransferParams(**_data), ForcedTransferParams(**_data)]
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.bulk_forced_transfer(
                data=transfer_list,
                tx_from="invalid_tx_from",  # invalid
                private_key=from_private_key,
            )

        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")


class TestBulkTransfer:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_pk = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to1_account = default_eth_account("user2")
        to1_address = to1_account.get("address")
        to1_pk = decode_keyfile_json(
            raw_keyfile_json=to1_account.get("keyfile_json"),
            password=to1_account.get("password").encode("utf-8"),
        )

        to2_account = default_eth_account("user3")
        to2_address = to2_account.get("address")
        to2_pk = decode_keyfile_json(
            raw_keyfile_json=to2_account.get("keyfile_json"),
            password=to2_account.get("password").encode("utf-8"),
        )

        # deploy new personal info contract
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=from_address,
            private_key=from_pk,
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to1_address,
            private_key=to1_pk,
            args=[from_address, "test_personal_info"],
        )

        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to2_address,
            private_key=to2_pk,
            args=[from_address, "test_personal_info"],
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_pk
        )

        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transferable": True,
        }
        await bond_contract.update(
            data=UpdateParams(**update_data),
            tx_from=from_address,
            private_key=from_pk,
        )

        # bulk transfer
        _data = {"to_address_list": [to1_address, to2_address], "amount_list": [10, 20]}
        _transfer_data = BulkTransferParams(**_data)
        await bond_contract.bulk_transfer(
            data=_transfer_data, tx_from=from_address, private_key=from_pk
        )

        # assertion
        from_balance = await bond_contract.get_account_balance(from_address)
        to1_balance = await bond_contract.get_account_balance(to1_address)
        to2_balance = await bond_contract.get_account_balance(to2_address)
        assert from_balance == arguments[2] - 10 - 20
        assert to1_balance == 10
        assert to2_balance == 20

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation (BulkTransferParams)
    # Required fields
    # -> ValidationError
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            BulkTransferParams(**_data)
        assert exc_info.value.errors() == [
            {
                "type": "missing",
                "loc": ("to_address_list",),
                "msg": "Field required",
                "input": {},
                "url": ANY,
            },
            {
                "type": "missing",
                "loc": ("amount_list",),
                "msg": "Field required",
                "input": {},
                "url": ANY,
            },
        ]

    # <Error_2>
    # Validation (BulkTransferParams)
    # Invalid parameter
    # -> ValidationError
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        _data = {"to_address_list": ["invalid to_address"], "amount_list": [0]}
        with pytest.raises(ValidationError) as exc_info:
            BulkTransferParams(**_data)
        assert exc_info.value.errors() == [
            {
                "type": "value_error",
                "loc": ("to_address_list", 0),
                "msg": "Value error, invalid ethereum address",
                "input": "invalid to_address",
                "ctx": {"error": ANY},
                "url": ANY,
            },
            {
                "type": "greater_than",
                "loc": ("amount_list", 0),
                "msg": "Input should be greater than 0",
                "input": 0,
                "ctx": {"gt": 0},
                "url": ANY,
            },
        ]

    # <Error_3>
    # Invalid tx_from
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_pk = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to1_account = default_eth_account("user2")
        to1_address = to1_account.get("address")

        to2_account = default_eth_account("user3")
        to2_address = to2_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_pk
        )

        # bulk transfer
        _data = {"to_address_list": [to1_address, to2_address], "amount_list": [10, 20]}
        _transfer_data = BulkTransferParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.bulk_transfer(
                data=_transfer_data, tx_from="invalid_tx_from", private_key=from_pk
            )

        # assertion
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_4>
    # Invalid private key
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_pk = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to1_account = default_eth_account("user2")
        to1_address = to1_account.get("address")

        to2_account = default_eth_account("user3")
        to2_address = to2_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_pk
        )

        # bulk transfer
        _data = {"to_address_list": [to1_address, to2_address], "amount_list": [10, 20]}
        _transfer_data = BulkTransferParams(**_data)
        with pytest.raises(SendTransactionError):
            await bond_contract.bulk_transfer(
                data=_transfer_data,
                tx_from=from_address,
                private_key="invalid_private_key",
            )

    # <Error_5_1>
    # Transaction Error
    # REVERT
    # -> ContractRevertError
    @pytest.mark.asyncio
    async def test_error_5_1(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_pk = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to1_account = default_eth_account("user2")
        to1_address = to1_account.get("address")

        to2_account = default_eth_account("user3")
        to2_address = to2_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_pk
        )

        # mock
        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 120502")),
        )

        # bulk transfer
        _data = {"to_address_list": [to1_address, to2_address], "amount_list": [10, 20]}
        _transfer_data = BulkTransferParams(**_data)
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.bulk_transfer(
                data=_transfer_data, tx_from=from_address, private_key=from_pk
            )

        # assertion
        assert (
            exc_info.value.args[0]
            == "Transfer amount is greater than from address balance."
        )

    # <Error_5_2>
    # Transaction Error
    # wait_for_transaction_receipt -> TimeExhausted Exception
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_5_2(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_pk = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to1_account = default_eth_account("user2")
        to1_address = to1_account.get("address")

        to2_account = default_eth_account("user3")
        to2_address = to2_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # bulk transfer
        _data = {"to_address_list": [to1_address, to2_address], "amount_list": [10, 20]}
        _transfer_data = BulkTransferParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.bulk_transfer(
                    data=_transfer_data, tx_from=from_address, private_key=from_pk
                )

        # assertion
        assert isinstance(exc_info.value.args[0], TimeExhausted)

    # <Error_5_3>
    # Transaction Error
    # wait_for_transaction_receipt -> Exception
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_5_3(self, async_db):
        from_account = default_eth_account("user1")
        from_address = from_account.get("address")
        from_pk = decode_keyfile_json(
            raw_keyfile_json=from_account.get("keyfile_json"),
            password=from_account.get("password").encode("utf-8"),
        )

        to1_account = default_eth_account("user2")
        to1_address = to1_account.get("address")

        to2_account = default_eth_account("user3")
        to2_address = to2_account.get("address")

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=from_address, private_key=from_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # bulk transfer
        _data = {"to_address_list": [to1_address, to2_address], "amount_list": [10, 20]}
        _transfer_data = BulkTransferParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.bulk_transfer(
                    data=_transfer_data, tx_from=from_address, private_key=from_pk
                )

        # assertion
        assert isinstance(exc_info.value.args[0], TransactionNotFound)


class TestAdditionalIssue:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        contract_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = AdditionalIssueParams(**_data)
        pre_datetime = datetime.now(UTC).replace(tzinfo=None)
        await bond_contract.additional_issue(
            data=_add_data, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        bond_contract_attr = await bond_contract.get()
        assert bond_contract_attr.total_supply == arguments[2] + 10

        balance = await bond_contract.get_account_balance(issuer_address)
        assert balance == arguments[2] + 10

        _token_attr_update = (
            await async_db.scalars(select(TokenAttrUpdate).limit(1))
        ).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation (AdditionalIssueParams)
    # required field
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            AdditionalIssueParams(**_data)
        assert exc_info.value.errors() == [
            {
                "input": {},
                "loc": ("account_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("amount",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_2>
    # validation (AdditionalIssueParams)
    # invalid parameter
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        _data = {"account_address": "invalid account address", "amount": 0}
        with pytest.raises(ValidationError) as exc_info:
            AdditionalIssueParams(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": "invalid account address",
                "loc": ("account_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"gt": 0},
                "input": 0,
                "loc": ("amount",),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "url": ANY,
            },
        ]

    # <Error_3>
    # invalid tx_from
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = AdditionalIssueParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.additional_issue(
                data=_add_data, tx_from="invalid_tx_from", private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_4>
    # invalid private key
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = AdditionalIssueParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.additional_issue(
                data=_add_data,
                tx_from=test_account.get("address"),
                private_key="invalid_private_key",
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = AdditionalIssueParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.additional_issue(
                    data=_add_data,
                    tx_from=test_account.get("address"),
                    private_key=private_key,
                )
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_6>
    # Error
    @pytest.mark.asyncio
    async def test_error_6(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = AdditionalIssueParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.additional_issue(
                    data=_add_data, tx_from=issuer_address, private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_7>
    # Transaction REVERT(not owner)
    @pytest.mark.asyncio
    async def test_error_7(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        user_account = default_eth_account("user2")
        user_address = user_account.get("address")
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )
        user_private_key = decode_keyfile_json(
            raw_keyfile_json=user_account.get("keyfile_json"),
            password=user_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_private_key
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = AdditionalIssueParams(**_data)

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 500001")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.additional_issue(
                data=_add_data, tx_from=user_address, private_key=user_private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender is not contract owner."


class TestBulkAdditionalIssue:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        contract_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = [AdditionalIssueParams(**_data), AdditionalIssueParams(**_data)]
        pre_datetime = datetime.now(UTC).replace(tzinfo=None)
        await bond_contract.bulk_additional_issue(
            data=_add_data, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        bond_contract_attr = await bond_contract.get()
        assert bond_contract_attr.total_supply == arguments[2] + 20

        balance = await bond_contract.get_account_balance(issuer_address)
        assert balance == arguments[2] + 20

        _token_attr_update = (
            await async_db.scalars(select(TokenAttrUpdate).limit(1))
        ).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Transaction REVERT
    # -> ContractRevertError
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        user_account = default_eth_account("user2")
        user_address = user_account.get("address")
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )
        user_private_key = decode_keyfile_json(
            raw_keyfile_json=user_account.get("keyfile_json"),
            password=user_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_private_key
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = [
            AdditionalIssueParams(**_data),
            AdditionalIssueParams(**_data),
        ]

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            AsyncMock(side_effect=ContractLogicError("execution reverted: 500001")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.bulk_additional_issue(
                data=_add_data, tx_from=user_address, private_key=user_private_key
            )

        # assertion
        assert exc_info.value.args[0] == "Message sender is not contract owner."

    # <Error_2>
    # TimeExhausted
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = [AdditionalIssueParams(**_data), AdditionalIssueParams(**_data)]
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.bulk_additional_issue(
                    data=_add_data, tx_from=issuer_address, private_key=private_key
                )
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_3>
    # Invalid tx_from
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # additional issue
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = [
            AdditionalIssueParams(**_data),
            AdditionalIssueParams(**_data),
        ]
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.bulk_additional_issue(
                data=_add_data, tx_from="invalid_tx_from", private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")


class TestRedeem:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        contract_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = RedeemParams(**_data)
        pre_datetime = datetime.now(UTC).replace(tzinfo=None)
        await bond_contract.redeem(
            data=_add_data, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        bond_contract_attr = await bond_contract.get()
        assert bond_contract_attr.total_supply == arguments[2] - 10

        balance = await bond_contract.get_account_balance(issuer_address)
        assert balance == arguments[2] - 10

        _token_attr_update = (
            await async_db.scalars(select(TokenAttrUpdate).limit(1))
        ).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # validation (RedeemParams)
    # required field
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        _data = {}
        with pytest.raises(ValidationError) as exc_info:
            RedeemParams(**_data)
        assert exc_info.value.errors() == [
            {
                "input": {},
                "loc": ("account_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("amount",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_2>
    # validation (RedeemParams)
    # invalid parameter
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        _data = {"account_address": "invalid account address", "amount": 0}
        with pytest.raises(ValidationError) as exc_info:
            RedeemParams(**_data)
        assert exc_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": "invalid account address",
                "loc": ("account_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"gt": 0},
                "input": 0,
                "loc": ("amount",),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "url": ANY,
            },
        ]

    # <Error_3>
    # invalid tx_from
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = RedeemParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.redeem(
                data=_add_data, tx_from="invalid_tx_from", private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_4>
    # invalid private key
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = RedeemParams(**_data)
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.redeem(
                data=_add_data,
                tx_from=test_account.get("address"),
                private_key="invalid_private_key",
            )
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = RedeemParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.redeem(
                    data=_add_data,
                    tx_from=test_account.get("address"),
                    private_key=private_key,
                )
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_6>
    # Error
    @pytest.mark.asyncio
    async def test_error_6(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = RedeemParams(**_data)
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.redeem(
                    data=_add_data, tx_from=issuer_address, private_key=private_key
                )
        assert isinstance(exc_info.value.args[0], TransactionNotFound)

    # <Error_7>
    # Transaction REVERT(lack balance)
    @pytest.mark.asyncio
    async def test_error_7(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 100_000_000}
        _add_data = RedeemParams(**_data)

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 121102")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.redeem(
                data=_add_data, tx_from=issuer_address, private_key=private_key
            )

        # assertion
        assert (
            exc_info.value.args[0]
            == "Redeem amount is less than target address balance."
        )


class TestBulkRedeem:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        contract_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = [RedeemParams(**_data), RedeemParams(**_data)]
        pre_datetime = datetime.now(UTC).replace(tzinfo=None)
        await bond_contract.bulk_redeem(
            data=_add_data, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        bond_contract_attr = await bond_contract.get()
        assert bond_contract_attr.total_supply == arguments[2] - 20

        balance = await bond_contract.get_account_balance(issuer_address)
        assert balance == arguments[2] - 20

        _token_attr_update = (
            await async_db.scalars(select(TokenAttrUpdate).limit(1))
        ).first()
        assert _token_attr_update.id == 1
        assert _token_attr_update.token_address == contract_address
        assert _token_attr_update.updated_datetime > pre_datetime

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Transaction REVERT
    # -> ContractRevertError
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 100_000_000}
        _add_data = [RedeemParams(**_data), RedeemParams(**_data)]

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            AsyncMock(side_effect=ContractLogicError("execution reverted: 111102")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.bulk_redeem(
                data=_add_data, tx_from=issuer_address, private_key=private_key
            )

        # assertion
        assert (
            exc_info.value.args[0]
            == "Redeem amount is less than target address balance."
        )

    # <Error_2>
    # TimeExhausted
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = [RedeemParams(**_data), RedeemParams(**_data)]
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.bulk_redeem(
                    data=_add_data, tx_from=issuer_address, private_key=private_key
                )
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_3>
    # Invalid tx_from
    # -> SendTransactionError
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # redeem
        _data = {"account_address": issuer_address, "amount": 10}
        _add_data = [RedeemParams(**_data), RedeemParams(**_data)]
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.bulk_redeem(
                data=_add_data, tx_from="invalid_tx_from", private_key=private_key
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")


class TestGetAccountBalance:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # assertion
        balance = await bond_contract.get_account_balance(issuer_address)
        assert balance == arguments[2]

    # <Normal_2>
    # not deployed contract_address
    @pytest.mark.asyncio
    async def test_normal_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")

        # execute the function
        bond_contract = IbetStraightBondContract()
        balance = await bond_contract.get_account_balance(issuer_address)

        # assertion
        assert balance == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_2>
    # invalid account_address
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # execute the function
        with pytest.raises(MismatchedABI):
            await bond_contract.get_account_balance(issuer_address[:-1])  # short


class TestCheckAttrUpdate:
    token_address = "0x0123456789abcDEF0123456789abCDef01234567"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # not exists
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        before_datetime = datetime.now(UTC).replace(tzinfo=None)

        # Test
        bond_contract = IbetStraightBondContract(self.token_address)
        result = await bond_contract.check_attr_update(async_db, before_datetime)

        # assertion
        assert result is False

    # <Normal_2>
    # prev data exists
    @pytest.mark.asyncio
    async def test_normal_2(self, async_db):
        before_datetime = datetime.now(UTC).replace(tzinfo=None)
        time.sleep(1)
        after_datetime = datetime.now(UTC).replace(tzinfo=None)

        # prepare data
        _update = TokenAttrUpdate()
        _update.token_address = self.token_address
        _update.updated_datetime = before_datetime
        async_db.add(_update)
        await async_db.commit()

        # Test
        bond_contract = IbetStraightBondContract(self.token_address)
        result = await bond_contract.check_attr_update(async_db, after_datetime)

        # assertion
        assert result is False

    # <Normal_3>
    # next data exists
    @pytest.mark.asyncio
    async def test_normal_3(self, async_db):
        before_datetime = datetime.now(UTC).replace(tzinfo=None)
        time.sleep(1)
        after_datetime = datetime.now(UTC).replace(tzinfo=None)

        # prepare data
        _update = TokenAttrUpdate()
        _update.token_address = self.token_address
        _update.updated_datetime = after_datetime
        async_db.add(_update)
        await async_db.commit()

        # Test
        bond_contract = IbetStraightBondContract(self.token_address)
        result = await bond_contract.check_attr_update(async_db, before_datetime)

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
    @pytest.mark.asyncio
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    async def test_normal_1(self, async_db):
        # Test
        bond_contract = IbetStraightBondContract(self.token_address)
        await bond_contract.record_attr_update(async_db)

        # assertion
        _update = (await async_db.scalars(select(TokenAttrUpdate).limit(1))).first()
        assert _update.id == 1
        assert _update.token_address == self.token_address
        assert _update.updated_datetime == datetime(2021, 4, 27, 12, 34, 56)

    # <Normal_2>
    # data exists
    @pytest.mark.asyncio
    async def test_normal_2(self, async_db, freezer):
        # prepare data
        _update = TokenAttrUpdate()
        _update.token_address = self.token_address
        _update.updated_datetime = datetime.now(UTC).replace(tzinfo=None)
        async_db.add(_update)
        await async_db.commit()

        # Mock datetime
        freezer.move_to("2021-04-27 12:34:56")

        # Test
        bond_contract = IbetStraightBondContract(self.token_address)
        await bond_contract.record_attr_update(async_db)

        # assertion
        _update = (
            await async_db.scalars(
                select(TokenAttrUpdate).where(TokenAttrUpdate.id == 2).limit(1)
            )
        ).first()
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
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8"),
        )

        deployer = default_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8"),
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk,
        )

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True,
        }
        await bond_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"],
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"],
        )

        # approve transfer (from issuer)
        approve_data = {"application_id": 0, "data": "approve transfer test"}
        tx_hash, tx_receipt = await bond_contract.approve_transfer(
            data=ApproveTransferParams(**approve_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        bond_token = ContractUtils.get_contract(
            contract_name="IbetStraightBond", contract_address=token_address
        )
        applications = bond_token.functions.applicationsForTransfer(0).call()
        assert applications[0] == issuer_address
        assert applications[1] == to_address
        assert applications[2] == 10
        assert applications[3] is False

        pendingTransfer = bond_token.functions.pendingTransfer(issuer_address).call()
        issuer_value = bond_token.functions.balanceOf(issuer_address).call()
        to_value = bond_token.functions.balanceOf(to_address).call()
        assert pendingTransfer == 0
        assert issuer_value == (10000 - 10)
        assert to_value == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid application index : not integer, data : missing
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        # Transfer approve
        approve_data = {
            "application_id": "not-integer",
        }
        with pytest.raises(ValidationError) as ex_info:
            _approve_transfer_data = ApproveTransferParams(**approve_data)

        assert ex_info.value.errors() == [
            {
                "input": "not-integer",
                "loc": ("application_id",),
                "msg": "Input should be a valid integer, unable to parse string as an "
                "integer",
                "type": "int_parsing",
                "url": ANY,
            },
            {
                "input": {"application_id": "not-integer"},
                "loc": ("data",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_2>
    # invalid contract_address : does not exists
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # Transfer approve
        approve_data = {"application_id": 0, "data": "test_data"}
        _approve_transfer_data = ApproveTransferParams(**approve_data)
        bond_contract = IbetStraightBondContract("not address")
        with pytest.raises(SendTransactionError) as ex_info:
            await bond_contract.approve_transfer(
                data=_approve_transfer_data,
                tx_from=issuer_address,
                private_key=private_key,
            )
        assert ex_info.match(
            "when sending a str, it must be a hex string. Got: 'not address'"
        )

    # <Error_3>
    # invalid issuer_address : does not exists
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # Transfer approve
        approve_data = {"application_id": 0, "data": "test_data"}
        _approve_transfer_data = ApproveTransferParams(**approve_data)
        with pytest.raises(SendTransactionError) as ex_info:
            await bond_contract.approve_transfer(
                data=_approve_transfer_data,
                tx_from=issuer_address[:-1],
                private_key=private_key,
            )
        assert ex_info.match(f"ENS name: '{issuer_address[:-1]}' is invalid.")

    # <Error_4>
    # invalid private_key : not properly
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # Transfer approve
        approve_data = {"application_id": 0, "data": "test_data"}
        _approve_transfer_data = ApproveTransferParams(**approve_data)
        with pytest.raises(SendTransactionError) as ex_info:
            await bond_contract.approve_transfer(
                data=_approve_transfer_data,
                tx_from=issuer_address,
                private_key="dummy-private",
            )
        assert ex_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # Transaction REVERT(application invalid)
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8"),
        )

        deployer = default_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8"),
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk,
        )

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True,
        }
        await bond_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"],
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"],
        )

        # approve transfer (from issuer)
        approve_data = {"application_id": 0, "data": "approve transfer test"}
        await bond_contract.approve_transfer(
            data=ApproveTransferParams(**approve_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # Then send approveTransfer transaction again.
        # This would be failed.

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 120902")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.approve_transfer(
                data=ApproveTransferParams(**approve_data),
                tx_from=issuer_address,
                private_key=issuer_pk,
            )

        # assertion
        assert exc_info.value.args[0] == "Application is invalid."


class TestCancelTransfer:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8"),
        )

        deployer = default_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8"),
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk,
        )

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True,
        }
        await bond_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"],
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"],
        )

        # cancel transfer (from issuer)
        cancel_data = {"application_id": 0, "data": "approve transfer test"}
        _approve_transfer_data = CancelTransferParams(**cancel_data)

        tx_hash, tx_receipt = await bond_contract.cancel_transfer(
            data=_approve_transfer_data, tx_from=issuer_address, private_key=issuer_pk
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1
        bond_token = ContractUtils.get_contract(
            contract_name="IbetStraightBond", contract_address=token_address
        )
        applications = bond_token.functions.applicationsForTransfer(0).call()
        assert applications[0] == issuer_address
        assert applications[1] == to_address
        assert applications[2] == 10
        assert applications[3] is False
        pendingTransfer = bond_token.functions.pendingTransfer(issuer_address).call()
        issuer_value = bond_token.functions.balanceOf(issuer_address).call()
        to_value = bond_token.functions.balanceOf(to_address).call()
        assert pendingTransfer == 0
        assert issuer_value == 10000
        assert to_value == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # invalid application index : not integer, data : missing
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        # Transfer approve
        cancel_data = {
            "application_id": "not-integer",
        }
        with pytest.raises(ValidationError) as ex_info:
            _approve_transfer_data = CancelTransferParams(**cancel_data)

        assert ex_info.value.errors() == [
            {
                "input": "not-integer",
                "loc": ("application_id",),
                "msg": "Input should be a valid integer, unable to parse string as an "
                "integer",
                "type": "int_parsing",
                "url": ANY,
            },
            {
                "input": {"application_id": "not-integer"},
                "loc": ("data",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_2>
    # invalid contract_address : does not exists
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # Transfer cancel
        cancel_data = {"application_id": 0, "data": "test_data"}
        _cancel_transfer_data = CancelTransferParams(**cancel_data)
        bond_contract = IbetStraightBondContract("not address")
        with pytest.raises(SendTransactionError) as ex_info:
            await bond_contract.cancel_transfer(
                data=_cancel_transfer_data,
                tx_from=issuer_address,
                private_key=private_key,
            )
        assert ex_info.match(
            "when sending a str, it must be a hex string. Got: 'not address'"
        )

    # <Error_3>
    # invalid issuer_address : does not exists
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # Transfer cancel
        cancel_data = {"application_id": 0, "data": "test_data"}
        _cancel_transfer_data = CancelTransferParams(**cancel_data)
        with pytest.raises(SendTransactionError) as ex_info:
            await bond_contract.cancel_transfer(
                data=_cancel_transfer_data,
                tx_from=issuer_address[:-1],
                private_key=private_key,
            )
        assert ex_info.match(f"ENS name: '{issuer_address[:-1]}' is invalid.")

    # <Error_4>
    # invalid private_key : not properly
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        test_account = default_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # deploy token
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        # Transfer cancel
        cancel_data = {"application_id": 0, "data": "test_data"}
        _cancel_transfer_data = CancelTransferParams(**cancel_data)
        with pytest.raises(SendTransactionError) as ex_info:
            await bond_contract.cancel_transfer(
                data=_cancel_transfer_data,
                tx_from=issuer_address,
                private_key="dummy-private",
            )
        assert ex_info.match("Non-hexadecimal digit found")

    # <Error_5>
    # Transaction REVERT(application invalid)
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        to_account = default_eth_account("user2")
        to_address = to_account.get("address")
        to_pk = decode_keyfile_json(
            raw_keyfile_json=to_account.get("keyfile_json"),
            password=to_account.get("password").encode("utf-8"),
        )

        deployer = default_eth_account("user3")
        deployer_address = deployer.get("address")
        deployer_pk = decode_keyfile_json(
            raw_keyfile_json=deployer.get("keyfile_json"),
            password=deployer.get("password").encode("utf-8"),
        )

        # deploy new personal info contract (from deployer)
        personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
            contract_name="PersonalInfo",
            args=[],
            deployer=deployer_address,
            private_key=deployer_pk,
        )

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # update token (from issuer)
        update_data = {
            "personal_info_contract_address": personal_info_contract_address,
            "transfer_approval_required": True,
            "transferable": True,
        }
        await bond_contract.update(
            data=UpdateParams(**update_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # register personal info (to_account)
        PersonalInfoContractTestUtils.register(
            contract_address=personal_info_contract_address,
            tx_from=to_address,
            private_key=to_pk,
            args=[issuer_address, "test_personal_info"],
        )

        # apply transfer (from issuer)
        IbetSecurityTokenContractTestUtils.apply_for_transfer(
            contract_address=token_address,
            tx_from=issuer_address,
            private_key=issuer_pk,
            args=[to_address, 10, "test_data"],
        )

        # approve transfer (from issuer)
        approve_data = {"application_id": 0, "data": "approve transfer test"}
        await bond_contract.approve_transfer(
            data=ApproveTransferParams(**approve_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # Then send cancelTransfer transaction. This would be failed.

        cancel_data = approve_data

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 120802")),
        )

        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.cancel_transfer(
                data=CancelTransferParams(**cancel_data),
                tx_from=issuer_address,
                private_key=issuer_pk,
            )

        # assertion
        assert exc_info.value.args[0] == "Application is invalid."


class TestLock:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        tx_hash, tx_receipt = await bond_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        bond_token = ContractUtils.get_contract(
            contract_name="IbetStraightBond", contract_address=token_address
        )
        lock_amount = bond_token.functions.lockedOf(lock_address, issuer_address).call()
        assert lock_amount == 10

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # ValidationError
    # field required
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_db):
        lock_data = {}
        with pytest.raises(ValidationError) as ex_info:
            LockParams(**lock_data)

        assert ex_info.value.errors() == [
            {
                "input": {},
                "loc": ("lock_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("value",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("data",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_1_2>
    # ValidationError
    # - lock_address is not a valid address
    # - value is not greater than 0
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_db):
        lock_data = {"lock_address": "test_address", "value": 0, "data": ""}
        with pytest.raises(ValidationError) as ex_info:
            LockParams(**lock_data)

        assert ex_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": "test_address",
                "loc": ("lock_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"gt": 0},
                "input": 0,
                "loc": ("value",),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "url": ANY,
            },
        ]

    # <Error_2_1>
    # SendTransactionError
    # Invalid tx_from
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.lock(
                data=LockParams(**lock_data),
                tx_from="invalid_tx_from",  # invalid tx from
                private_key="",
            )

        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_2_2>
    # SendTransactionError
    # Invalid pk
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.lock(
                data=LockParams(**lock_data),
                tx_from=issuer_address,
                private_key="invalid_pk",  # invalid pk
            )

        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_3>
    # SendTransactionError
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.lock(
                    data=LockParams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_4>
    # SendTransactionError
    # TransactionNotFound
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.lock(
                    data=LockParams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        assert exc_info.type(SendTransactionError(TransactionNotFound))

    # <Error_5>
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 120002")),
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 20001, "data": ""}
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.lock(
                data=LockParams(**lock_data),
                tx_from=issuer_address,
                private_key=issuer_pk,
            )

        # assertion
        assert exc_info.value.code == 120002
        assert (
            exc_info.value.message
            == "Lock amount is greater than message sender balance."
        )


class TestForceLock:
    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # force lock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "value": 10,
            "data": "",
        }
        tx_hash, tx_receipt = await bond_contract.force_lock(
            data=ForceLockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        bond_token = ContractUtils.get_contract(
            contract_name="IbetStraightBond", contract_address=token_address
        )
        lock_amount = bond_token.functions.lockedOf(lock_address, issuer_address).call()
        assert lock_amount == 10

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1_1>
    # ValidationError: Field required
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_db):
        lock_data = {}
        with pytest.raises(ValidationError) as ex_info:
            ForceLockParams(**lock_data)

        assert ex_info.value.errors() == [
            {
                "input": {},
                "loc": ("lock_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("account_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("value",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("data",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_1_2>
    # ValidationError: Value error
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_db):
        lock_data = {
            "lock_address": "test_lock_address",
            "account_address": "test_account_address",
            "value": 0,
            "data": "",
        }
        with pytest.raises(ValidationError) as ex_info:
            ForceLockParams(**lock_data)

        assert ex_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": "test_lock_address",
                "loc": ("lock_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "test_account_address",
                "loc": ("account_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"gt": 0},
                "input": 0,
                "loc": ("value",),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "url": ANY,
            },
        ]

    # <Error_2_1>
    # SendTransactionError: Invalid tx_from
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # force lock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "value": 10,
            "data": "",
        }
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.force_lock(
                data=ForceLockParams(**lock_data),
                tx_from="invalid_tx_from",  # invalid tx_from
                private_key=issuer_pk,
            )

        # assertion
        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_2_2>
    # SendTransactionError: Invalid pk
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # force lock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "value": 10,
            "data": "",
        }
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.force_lock(
                data=ForceLockParams(**lock_data),
                tx_from=issuer_address,
                private_key="invalid_pk",  # invalid pk
            )

        # assertion
        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_2_3>
    # SendTransactionError: TimeExhausted
    @pytest.mark.asyncio
    async def test_error_2_3(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # force lock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "value": 10,
            "data": "",
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.force_lock(
                    data=ForceLockParams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        # assertion
        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_2_4>
    # SendTransactionError: TransactionNotFound
    @pytest.mark.asyncio
    async def test_error_2_4(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # force lock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "value": 10,
            "data": "",
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.force_lock(
                    data=ForceLockParams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        # assertion
        assert exc_info.type(SendTransactionError(TransactionNotFound))

    # <Error_2_5>
    # SendTransactionError: ContractRevertError
    @pytest.mark.asyncio
    async def test_error_2_5(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            AsyncMock(side_effect=ContractLogicError("execution reverted: 121601")),
        )

        # force lock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "value": 20001,
            "data": "",
        }
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.force_lock(
                data=ForceLockParams(**lock_data),
                tx_from=issuer_address,
                private_key=issuer_pk,
            )

        # assertion
        assert exc_info.value.code == 121601
        assert (
            exc_info.value.message
            == "Lock amount is greater than message sender balance."
        )


class TestForceUnlock:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        await bond_contract.lock(
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
            "data": json.dumps({"message": "force_unlock"}),
        }
        block_from = web3.eth.block_number
        tx_hash, tx_receipt = await bond_contract.force_unlock(
            data=ForceUnlockPrams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )
        block_to = web3.eth.block_number

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        bond_token = AsyncContractUtils.get_contract(
            contract_name="IbetStraightBond", contract_address=token_address
        )
        lock_amount = await bond_token.functions.lockedOf(
            lock_address, issuer_address
        ).call()
        assert lock_amount == 5

        logs = await AsyncContractUtils.get_event_logs(
            contract=bond_token,
            event="ForceUnlock",
            block_from=block_from,
            block_to=block_to,
        )
        assert json.loads(logs[0].args["data"]) == {"message": "force_unlock"}

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # ValidationError
    # field required
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_db):
        lock_data = {}
        with pytest.raises(ValidationError) as ex_info:
            ForceUnlockPrams(**lock_data)

        assert ex_info.value.errors() == [
            {
                "input": {},
                "loc": ("lock_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("account_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("recipient_address",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("value",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
            {
                "input": {},
                "loc": ("data",),
                "msg": "Field required",
                "type": "missing",
                "url": ANY,
            },
        ]

    # <Error_1_2>
    # ValidationError
    # - address is not a valid address
    # - value is not greater than 0
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_db):
        lock_data = {
            "lock_address": "test_address",
            "account_address": "test_address",
            "recipient_address": "test_address",
            "value": 0,
            "data": "",
        }
        with pytest.raises(ValidationError) as ex_info:
            ForceUnlockPrams(**lock_data)

        assert ex_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": "test_address",
                "loc": ("lock_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "test_address",
                "loc": ("account_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "test_address",
                "loc": ("recipient_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"gt": 0},
                "input": 0,
                "loc": ("value",),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "url": ANY,
            },
        ]

    # <Error_2_1>
    # SendTransactionError
    # Invalid tx_from
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        await bond_contract.lock(
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
            "data": "",
        }
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.force_unlock(
                data=ForceUnlockPrams(**lock_data),
                tx_from="invalid_tx_from",  # invalid tx from
                private_key="",
            )

        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_2_2>
    # SendTransactionError
    # Invalid pk
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        await bond_contract.lock(
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
            "data": "",
        }
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.force_unlock(
                data=ForceUnlockPrams(**lock_data),
                tx_from=issuer_address,
                private_key="invalid_pk",  # invalid pk
            )

        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_3>
    # SendTransactionError
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        await bond_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 5,
            "data": "",
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.force_unlock(
                    data=ForceUnlockPrams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_4>
    # SendTransactionError
    # TransactionNotFound
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        await bond_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 5,
            "data": "",
        }
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.force_unlock(
                    data=ForceUnlockPrams(**lock_data),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        assert exc_info.type(SendTransactionError(TransactionNotFound))

    # <Error_5>
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        lock_data = {"lock_address": lock_address, "value": 10, "data": ""}
        await bond_contract.lock(
            data=LockParams(**lock_data),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 121201")),
        )

        # forceUnlock
        lock_data = {
            "lock_address": lock_address,
            "account_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 11,
            "data": "",
        }
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.force_unlock(
                data=ForceUnlockPrams(**lock_data),
                tx_from=issuer_address,
                private_key=issuer_pk,
            )

        # assertion
        assert exc_info.value.code == 121201
        assert exc_info.value.message == "Unlock amount is greater than locked amount."


class TestForceChangeLockedAmount:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        other_account = default_eth_account("user3")
        other_address = other_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        token_address, _, _ = await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        await bond_contract.lock(
            data=LockParams(lock_address=lock_address, value=10, data=""),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # forceChangeLockedAmount
        block_from = web3.eth.block_number
        tx_hash, tx_receipt = await bond_contract.force_change_locked_account(
            data=ForceChangeLockedAccountParams(
                lock_address=lock_address,
                before_account_address=issuer_address,
                after_account_address=other_address,
                value=5,
                data=json.dumps({"message": "force_change_locked_account"}),
            ),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )
        block_to = web3.eth.block_number

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        bond_token = AsyncContractUtils.get_contract(
            contract_name="IbetStraightBond", contract_address=token_address
        )
        assert (
            await bond_token.functions.lockedOf(lock_address, issuer_address).call()
        ) == 5
        assert (
            await bond_token.functions.lockedOf(lock_address, other_address).call()
        ) == 5

        logs = await AsyncContractUtils.get_event_logs(
            contract=bond_token,
            event="ForceChangeLockedAccount",
            block_from=block_from,
            block_to=block_to,
        )
        assert json.loads(logs[0].args["data"]) == {
            "message": "force_change_locked_account"
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # ValidationError
    # field required
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_db):
        with pytest.raises(ValidationError) as ex_info:
            ForceChangeLockedAccountParams(**{})

        assert ex_info.value.errors() == [
            {
                "type": "missing",
                "loc": ("lock_address",),
                "msg": "Field required",
                "input": {},
                "url": ANY,
            },
            {
                "type": "missing",
                "loc": ("before_account_address",),
                "msg": "Field required",
                "input": {},
                "url": ANY,
            },
            {
                "type": "missing",
                "loc": ("after_account_address",),
                "msg": "Field required",
                "input": {},
                "url": ANY,
            },
            {
                "type": "missing",
                "loc": ("value",),
                "msg": "Field required",
                "input": {},
                "url": ANY,
            },
            {
                "type": "missing",
                "loc": ("data",),
                "msg": "Field required",
                "input": {},
                "url": ANY,
            },
        ]

    # <Error_1_2>
    # ValidationError
    # - address is not a valid address
    # - value is not greater than 0
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_db):
        with pytest.raises(ValidationError) as ex_info:
            ForceChangeLockedAccountParams(
                lock_address="test_address",
                before_account_address="test_address",
                after_account_address="test_address",
                value=0,
                data="",
            )

        assert ex_info.value.errors() == [
            {
                "ctx": {"error": ANY},
                "input": "test_address",
                "loc": ("lock_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "test_address",
                "loc": ("before_account_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"error": ANY},
                "input": "test_address",
                "loc": ("after_account_address",),
                "msg": "Value error, invalid ethereum address",
                "type": "value_error",
                "url": ANY,
            },
            {
                "ctx": {"gt": 0},
                "input": 0,
                "loc": ("value",),
                "msg": "Input should be greater than 0",
                "type": "greater_than",
                "url": ANY,
            },
        ]

    # <Error_2_1>
    # SendTransactionError
    # Invalid tx_from
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        other_account = default_eth_account("user3")
        other_address = other_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        await bond_contract.lock(
            data=LockParams(lock_address=lock_address, value=10, data=""),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # forceChangeLockedAmount
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.force_change_locked_account(
                data=ForceChangeLockedAccountParams(
                    lock_address=lock_address,
                    before_account_address=issuer_address,
                    after_account_address=other_address,
                    value=5,
                    data=json.dumps({"message": "force_change_locked_account"}),
                ),
                tx_from="invalid_tx_from",  # invalid tx from
                private_key=issuer_pk,
            )

        assert isinstance(exc_info.value.args[0], InvalidAddress)
        assert exc_info.match("ENS name: 'invalid_tx_from' is invalid.")

    # <Error_2_2>
    # SendTransactionError
    # Invalid pk
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        other_account = default_eth_account("user3")
        other_address = other_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        await bond_contract.lock(
            data=LockParams(lock_address=lock_address, value=10, data=""),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # forceChangeLockedAmount
        with pytest.raises(SendTransactionError) as exc_info:
            await bond_contract.force_change_locked_account(
                data=ForceChangeLockedAccountParams(
                    lock_address=lock_address,
                    before_account_address=issuer_address,
                    after_account_address=other_address,
                    value=5,
                    data=json.dumps({"message": "force_change_locked_account"}),
                ),
                tx_from=issuer_address,
                private_key="invalid_pk",  # invalid pk
            )

        assert isinstance(exc_info.value.args[0], Error)
        assert exc_info.match("Non-hexadecimal digit found")

    # <Error_3>
    # SendTransactionError
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        other_account = default_eth_account("user3")
        other_address = other_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        await bond_contract.lock(
            data=LockParams(lock_address=lock_address, value=10, data=""),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted,
        )

        # forceChangeLockedAccount
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.force_change_locked_account(
                    data=ForceChangeLockedAccountParams(
                        lock_address=lock_address,
                        before_account_address=issuer_address,
                        after_account_address=other_address,
                        value=5,
                        data=json.dumps({"message": "force_change_locked_account"}),
                    ),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        assert exc_info.type(SendTransactionError(TimeExhausted))

    # <Error_4>
    # SendTransactionError
    # TransactionNotFound
    @pytest.mark.asyncio
    async def test_error_4(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        other_account = default_eth_account("user3")
        other_address = other_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        await bond_contract.lock(
            data=LockParams(lock_address=lock_address, value=10, data=""),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TransactionNotFound(message=""),
        )

        # forceChangeLockedAccount
        with Web3_send_raw_transaction:
            with pytest.raises(SendTransactionError) as exc_info:
                await bond_contract.force_change_locked_account(
                    data=ForceChangeLockedAccountParams(
                        lock_address=lock_address,
                        before_account_address=issuer_address,
                        after_account_address=other_address,
                        value=5,
                        data=json.dumps({"message": "force_change_locked_account"}),
                    ),
                    tx_from=issuer_address,
                    private_key=issuer_pk,
                )

        assert exc_info.type(SendTransactionError(TransactionNotFound))

    # <Error_5>
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_5(self, async_db):
        issuer = default_eth_account("user1")
        issuer_address = issuer.get("address")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer.get("keyfile_json"),
            password=issuer.get("password").encode("utf-8"),
        )

        lock_account = default_eth_account("user2")
        lock_address = lock_account.get("address")

        other_account = default_eth_account("user3")
        other_address = other_account.get("address")

        # deploy ibet bond token (from issuer)
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_contract = IbetStraightBondContract()
        await bond_contract.create(
            args=arguments, tx_from=issuer_address, private_key=issuer_pk
        )

        # lock
        await bond_contract.lock(
            data=LockParams(lock_address=lock_address, value=10, data=""),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 121701")),
        )

        # forceChangeLockedAccount
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await bond_contract.force_change_locked_account(
                data=ForceChangeLockedAccountParams(
                    lock_address=lock_address,
                    before_account_address=issuer_address,
                    after_account_address=other_address,
                    value=11,
                    data=json.dumps({"message": "force_change_locked_account"}),
                ),
                tx_from=issuer_address,
                private_key=issuer_pk,
            )

        # assertion
        assert exc_info.value.code == 121701
        assert exc_info.value.message == "Locked balance is not sufficient."
