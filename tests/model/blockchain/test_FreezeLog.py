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

from unittest import mock
from unittest.mock import AsyncMock

import pytest
from web3 import Web3
from web3.exceptions import TimeExhausted
from web3.middleware import geth_poa_middleware

from app.exceptions import SendTransactionError
from app.model.blockchain import FreezeLogContract
from app.model.db import FreezeLogAccount
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from config import WEB3_HTTP_PROVIDER
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestRecordLog:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )
        log_message = "test message"

        # Run Test
        tx_hash, log_index = await FreezeLogContract(
            log_account=log_account, contract_address=freeze_log_contract.address
        ).record_log(log_message=log_message, freezing_grace_block_count=100)

        # Assertion
        last_index = freeze_log_contract.functions.lastLogIndex(
            log_account.account_address
        ).call()
        assert log_index == last_index - 1

        last_message = freeze_log_contract.functions.getLog(
            log_account.account_address, last_index - 1
        ).call()
        block = ContractUtils.get_block_by_transaction_hash(tx_hash)
        assert last_message[0] == block["number"]
        assert last_message[1] == 100
        assert last_message[2] == "test message"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Transaction Error
    @pytest.mark.asyncio
    async def test_error_1(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )
        log_message = "test message"

        # Run Test
        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.AsyncContractUtils.send_transaction",
                AsyncMock(side_effect=Exception("tx error")),
            ):
                await FreezeLogContract(
                    log_account=log_account,
                    contract_address=freeze_log_contract.address,
                ).record_log(log_message=log_message, freezing_grace_block_count=100)

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, Exception)
        assert "tx error" in str(cause)

    # <Error_2>
    # Transaction Timeout
    @pytest.mark.asyncio
    async def test_error_2(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )
        log_message = "test message"

        # Run Test
        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.AsyncContractUtils.send_transaction",
                AsyncMock(side_effect=TimeExhausted("Timeout Error test")),
            ):
                await FreezeLogContract(
                    log_account=log_account,
                    contract_address=freeze_log_contract.address,
                ).record_log(log_message=log_message, freezing_grace_block_count=100)

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, TimeExhausted)
        assert "Timeout Error test" in str(cause)


class TestUpdateLog:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )

        # Run Test
        log_contract = FreezeLogContract(
            log_account=log_account, contract_address=freeze_log_contract.address
        )
        tx_hash, log_index = await log_contract.record_log(
            log_message="before message", freezing_grace_block_count=100
        )
        _ = await log_contract.update_log(
            log_index=log_index, log_message="after message"
        )

        # Assertion
        last_message = freeze_log_contract.functions.getLog(
            log_account.account_address, log_index
        ).call()
        block = ContractUtils.get_block_by_transaction_hash(tx_hash)
        assert last_message[0] == block["number"]
        assert last_message[1] == 100
        assert last_message[2] == "after message"

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Transaction Error
    @pytest.mark.asyncio
    async def test_error_1(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )
        log_message = "test message"

        # Run Test
        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.AsyncContractUtils.send_transaction",
                AsyncMock(side_effect=Exception("tx error")),
            ):
                await FreezeLogContract(
                    log_account=log_account,
                    contract_address=freeze_log_contract.address,
                ).update_log(log_index=1, log_message=log_message)

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, Exception)
        assert "tx error" in str(cause)

    # <Error_2>
    # Transaction Timeout
    @pytest.mark.asyncio
    async def test_error_2(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )
        log_message = "test message"

        # Run Test
        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.AsyncContractUtils.send_transaction",
                AsyncMock(side_effect=TimeExhausted("Timeout Error test")),
            ):
                await FreezeLogContract(
                    log_account=log_account,
                    contract_address=freeze_log_contract.address,
                ).update_log(log_index=1, log_message=log_message)

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, TimeExhausted)
        assert "Timeout Error test" in str(cause)


class TestGetLog:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )

        # Run Test
        log_contract = FreezeLogContract(
            log_account=log_account, contract_address=freeze_log_contract.address
        )
        tx_hash, log_index = await log_contract.record_log(
            log_message="test message", freezing_grace_block_count=100
        )
        _block_number, _grace_block_count, _log_message = await log_contract.get_log(
            log_index
        )

        # Assertion
        block = ContractUtils.get_block_by_transaction_hash(tx_hash)
        assert _block_number == block["number"]
        assert _grace_block_count == 100
        assert _log_message == "test message"

    # <Normal_2>
    # Default value
    @pytest.mark.asyncio
    async def test_normal_2(self, db, freeze_log_contract):
        user = config_eth_account("user1")
        user_address = user["address"]

        log_account = FreezeLogAccount(
            account_address=user_address,
            keyfile=user["keyfile_json"],
            eoa_password=E2EEUtils.encrypt("password"),
        )

        # Run Test
        log_contract = FreezeLogContract(
            log_account=log_account, contract_address=freeze_log_contract.address
        )
        _block_number, _grace_block_count, _log_message = await log_contract.get_log(
            9999999
        )

        # Assertion
        assert _block_number == 0
        assert _grace_block_count == 0
        assert _log_message == ""
