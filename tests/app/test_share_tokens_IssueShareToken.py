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

import hashlib
import random
import string
from datetime import UTC, datetime
from unittest import mock
from unittest.mock import ANY, patch

import pytest
from sqlalchemy import select
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import config
from app.exceptions import SendTransactionError
from app.model.db import (
    UTXO,
    Account,
    AuthToken,
    EthIbetWSTTx,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    IDXPosition,
    Token,
    TokenType,
    TokenUpdateOperationLog,
    TokenVersion,
    UpdateToken,
)
from app.model.ibet.token import IbetShareContract
from app.model.ibet.token_list import TokenListContract
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestIssueShareToken:
    # target API endpoint
    apiurl = "/share/tokens"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # create only
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        token_before = (await async_db.scalars(select(Token))).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetShareContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.4567898765432,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234567898765432,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_SHARE,
                tx_from=test_account["address"],
                private_key=ANY,
            )
            await AsyncContractUtils.get_block_by_transaction_hash(
                tx_hash="0x0000000000000000000000000000000000000000000000000000000000000001"
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = (await async_db.scalars(select(Token))).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)

            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE
            assert (
                token_1.tx_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 1
            assert token_1.version == TokenVersion.V_25_06
            assert token_1.ibet_wst_activated is None
            assert token_1.ibet_wst_version is None

            position = (await async_db.scalars(select(IDXPosition).limit(1))).first()
            assert position.token_address == "contract_address_test1"
            assert position.account_address == test_account["address"]
            assert position.balance == req_param["total_supply"]
            assert position.exchange_balance == 0
            assert position.exchange_commitment == 0
            assert position.pending_transfer == 0

            utxo = (await async_db.scalars(select(UTXO).limit(1))).first()
            assert (
                utxo.transaction_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert utxo.account_address == test_account["address"]
            assert utxo.token_address == "contract_address_test1"
            assert utxo.amount == req_param["total_supply"]
            assert utxo.block_number == 12345
            assert utxo.block_timestamp == datetime(2021, 4, 27, 12, 34, 56)

            update_token = (
                await async_db.scalars(select(UpdateToken).limit(1))
            ).first()
            assert update_token is None

            operation_log = (
                await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
            ).first()
            assert operation_log.token_address == "contract_address_test1"
            assert operation_log.type == TokenType.IBET_SHARE
            assert operation_log.original_contents is None
            assert operation_log.operation_category == "Issue"

            ibet_wst_tx = (await async_db.scalars(select(EthIbetWSTTx))).all()
            assert len(ibet_wst_tx) == 0

    # <Normal_1_2>
    # create only
    # No input for symbol, dividends and cancellation_date.
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        token_before = (await async_db.scalars(select(Token))).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetShareContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "principal_value": 1000,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=["name_test1", "", 1000, 10000, 0, "", "", "", 1000],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_SHARE,
                tx_from=test_account["address"],
                private_key=ANY,
            )
            await AsyncContractUtils.get_block_by_transaction_hash(
                tx_hash="0x0000000000000000000000000000000000000000000000000000000000000001"
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = (await async_db.scalars(select(Token))).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)

            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE
            assert (
                token_1.tx_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 1
            assert token_1.version == TokenVersion.V_25_06
            assert token_1.ibet_wst_activated is None
            assert token_1.ibet_wst_version is None

            position = (await async_db.scalars(select(IDXPosition).limit(1))).first()
            assert position.token_address == "contract_address_test1"
            assert position.account_address == test_account["address"]
            assert position.balance == req_param["total_supply"]
            assert position.exchange_balance == 0
            assert position.exchange_commitment == 0
            assert position.pending_transfer == 0

            utxo = (await async_db.scalars(select(UTXO).limit(1))).first()
            assert (
                utxo.transaction_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert utxo.account_address == test_account["address"]
            assert utxo.token_address == "contract_address_test1"
            assert utxo.amount == req_param["total_supply"]
            assert utxo.block_number == 12345
            assert utxo.block_timestamp == datetime(2021, 4, 27, 12, 34, 56)

            update_token = (
                await async_db.scalars(select(UpdateToken).limit(1))
            ).first()
            assert update_token is None

            operation_log = (
                await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
            ).first()
            assert operation_log.token_address == "contract_address_test1"
            assert operation_log.type == TokenType.IBET_SHARE
            assert operation_log.original_contents is None
            assert operation_log.operation_category == "Issue"

            ibet_wst_tx = (await async_db.scalars(select(EthIbetWSTTx))).all()
            assert len(ibet_wst_tx) == 0

    # <Normal_2>
    # include updates
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        token_before = (await async_db.scalars(select(Token))).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetShareContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "require_personal_info_registered": False,  # update
                "transferable": False,  # update
                "status": False,  # update
                "is_offering": True,  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test",  # update
                "transfer_approval_required": True,  # update
                "principal_value": 1000,
                "is_canceled": True,
                "activate_ibet_wst": None,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_not_called()
            AsyncContractUtils.get_block_by_transaction_hash.assert_not_called()

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 0

            token_after = (await async_db.scalars(select(Token))).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)

            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE
            assert (
                token_1.tx_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 0
            assert token_1.version == TokenVersion.V_25_06
            assert token_1.ibet_wst_version is None

            position = (await async_db.scalars(select(IDXPosition).limit(1))).first()
            assert position is None

            utxo = (await async_db.scalars(select(UTXO).limit(1))).first()
            assert utxo is None

            update_token = (
                await async_db.scalars(select(UpdateToken).limit(1))
            ).first()
            assert update_token.id == 1
            assert update_token.token_address == "contract_address_test1"
            assert update_token.issuer_address == test_account["address"]
            assert update_token.type == TokenType.IBET_SHARE
            assert update_token.arguments == req_param
            assert update_token.status == 0
            assert update_token.trigger == "Issue"

            ibet_wst_tx = (await async_db.scalars(select(EthIbetWSTTx))).all()
            assert len(ibet_wst_tx) == 0

    # <Normal_3>
    # Authorization by auth-token
    @pytest.mark.asyncio
    async def test_normal_3(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = test_account["address"]
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        async_db.add(auth_token)

        await async_db.commit()

        token_before = (await async_db.scalars(select(Token))).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetShareContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "auth-token": "test_auth_token",
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_SHARE,
                tx_from=test_account["address"],
                private_key=ANY,
            )
            await AsyncContractUtils.get_block_by_transaction_hash(
                tx_hash="0x0000000000000000000000000000000000000000000000000000000000000001"
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = (await async_db.scalars(select(Token))).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)

            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE
            assert (
                token_1.tx_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 1
            assert token_1.version == TokenVersion.V_25_06
            assert token_1.ibet_wst_activated is None
            assert token_1.ibet_wst_version is None

            position = (await async_db.scalars(select(IDXPosition).limit(1))).first()
            assert position.token_address == "contract_address_test1"
            assert position.account_address == test_account["address"]
            assert position.balance == req_param["total_supply"]
            assert position.exchange_balance == 0
            assert position.exchange_commitment == 0
            assert position.pending_transfer == 0

            utxo = (await async_db.scalars(select(UTXO).limit(1))).first()
            assert (
                utxo.transaction_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert utxo.account_address == test_account["address"]
            assert utxo.token_address == "contract_address_test1"
            assert utxo.amount == req_param["total_supply"]
            assert utxo.block_number == 12345
            assert utxo.block_timestamp == datetime(2021, 4, 27, 12, 34, 56)

            update_token = (
                await async_db.scalars(select(UpdateToken).limit(1))
            ).first()
            assert update_token is None

            operation_log = (
                await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
            ).first()
            assert operation_log.token_address == "contract_address_test1"
            assert operation_log.type == TokenType.IBET_SHARE
            assert operation_log.original_contents is None
            assert operation_log.operation_category == "Issue"

            ibet_wst_tx = (await async_db.scalars(select(EthIbetWSTTx))).all()
            assert len(ibet_wst_tx) == 0

    # <Normal_4_1>
    # YYYYMMDD parameter is not empty
    @pytest.mark.asyncio
    async def test_normal_4_1(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetShareContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

    # <Normal_4_2>
    # YYYYMMDD parameter is empty
    @pytest.mark.asyncio
    async def test_normal_4_2(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetShareContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "",
                "dividend_payment_date": "",
                "cancellation_date": "",
                "principal_value": 1000,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234500000000000,
                    "",
                    "",
                    "",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

    # <Normal_5>
    # Activate IbetWST
    @mock.patch(
        "app.routers.issuer.share.ETH_MASTER_ACCOUNT_ADDRESS",
        "0x1234567890123456789012345678901234567890",
    )
    @pytest.mark.asyncio
    async def test_normal_5(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        token_before = (await async_db.scalars(select(Token))).all()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            return_value=None,
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetShareContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.4567898765432,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
                "activate_ibet_wst": True,  # Activate IbetWST
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            IbetShareContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    1000,
                    10000,
                    1234567898765432,
                    "20211231",
                    "20211231",
                    "20221231",
                    1000,
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_SHARE,
                tx_from=test_account["address"],
                private_key=ANY,
            )
            await AsyncContractUtils.get_block_by_transaction_hash(
                tx_hash="0x0000000000000000000000000000000000000000000000000000000000000001"
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 1

            token_after = (await async_db.scalars(select(Token))).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)

            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_SHARE
            assert (
                token_1.tx_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 1
            assert token_1.version == TokenVersion.V_25_06
            assert token_1.ibet_wst_activated is True
            assert token_1.ibet_wst_version == IbetWSTVersion.V_1

            position = (await async_db.scalars(select(IDXPosition).limit(1))).first()
            assert position.token_address == "contract_address_test1"
            assert position.account_address == test_account["address"]
            assert position.balance == req_param["total_supply"]
            assert position.exchange_balance == 0
            assert position.exchange_commitment == 0
            assert position.pending_transfer == 0

            utxo = (await async_db.scalars(select(UTXO).limit(1))).first()
            assert (
                utxo.transaction_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert utxo.account_address == test_account["address"]
            assert utxo.token_address == "contract_address_test1"
            assert utxo.amount == req_param["total_supply"]
            assert utxo.block_number == 12345
            assert utxo.block_timestamp == datetime(2021, 4, 27, 12, 34, 56)

            update_token = (
                await async_db.scalars(select(UpdateToken).limit(1))
            ).first()
            assert update_token is None

            operation_log = (
                await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
            ).first()
            assert operation_log.token_address == "contract_address_test1"
            assert operation_log.type == TokenType.IBET_SHARE
            assert operation_log.original_contents is None
            assert operation_log.operation_category == "Issue"

            ibet_wst_tx = (await async_db.scalars(select(EthIbetWSTTx))).all()
            assert len(ibet_wst_tx) == 1
            ibet_wst_tx_1 = ibet_wst_tx[0]
            assert ibet_wst_tx_1.tx_type == IbetWSTTxType.DEPLOY
            assert ibet_wst_tx_1.version == IbetWSTVersion.V_1
            assert ibet_wst_tx_1.status == IbetWSTTxStatus.PENDING
            assert ibet_wst_tx_1.tx_params == {
                "name": "name_test1",
                "initial_owner": test_account["address"],
            }
            assert (
                ibet_wst_tx_1.tx_sender == "0x1234567890123456789012345678901234567890"
            )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Validation Error
    # missing fields
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # request target api
        resp = await async_client.post(self.apiurl)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
        }

    # <Error_2_1>
    # Validation Error
    # format error
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 0.00000000000001,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0",
            "personal_info_contract_address": "0x0",
            "principal_value": 1000,
        }
        resp = await async_client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "value_error",
                    "loc": ["body", "dividends"],
                    "msg": "Value error, dividends must be rounded to 13 decimal places",
                    "input": 1e-14,
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "tradable_exchange_contract_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "0x0",
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "personal_info_contract_address"],
                    "msg": "Value error, invalid ethereum address",
                    "input": "0x0",
                    "ctx": {"error": {}},
                },
            ],
        }

    # <Error_2_2>
    # Validation Error
    # required headers
    @pytest.mark.asyncio
    async def test_error_2_2(self, async_client, async_db):
        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = await async_client.post(
            self.apiurl, json=req_param, headers={"issuer-address": "issuer-address"}
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "issuer-address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2_3>
    # Validation Error
    # eoa-password is not a Base64-encoded encrypted data
    @pytest.mark.asyncio
    async def test_error_2_3(self, async_client, async_db):
        test_account_1 = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = await async_client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_1["address"],
                "eoa-password": "password",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "password",
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                }
            ],
        }

    # <Error_2_4>
    # Validation Error
    # min value
    @pytest.mark.asyncio
    async def test_error_2_4(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": -1,
            "total_supply": -1,
            "dividends": -0.01,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "transferable": False,  # update
            "status": False,  # update
            "is_offering": True,  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "principal_value": -1,
            "is_canceled": True,
        }
        resp = await async_client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "issue_price"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "principal_value"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "total_supply"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0.0},
                    "input": -0.01,
                    "loc": ["body", "dividends"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
        }

    # <Error_2_5>
    # Validation Error
    # max value or max length
    @pytest.mark.asyncio
    async def test_error_2_5(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # request target api
        req_param = {
            "name": GetRandomStr(101),
            "symbol": GetRandomStr(101),
            "issue_price": 5_000_000_001,
            "total_supply": 1_000_000_000_001,
            "dividends": 5_000_000_000.01,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "transferable": False,  # update
            "status": False,  # update
            "is_offering": True,  # update
            "contact_information": GetRandomStr(2001),  # update
            "privacy_policy": GetRandomStr(5001),  # update
            "transfer_approval_required": True,  # update
            "principal_value": 5_000_000_001,
            "is_canceled": True,
        }
        resp = await async_client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"max_length": 100},
                    "input": mock.ANY,
                    "loc": ["body", "name"],
                    "msg": "String should have at most 100 characters",
                    "type": "string_too_long",
                },
                {
                    "ctx": {"le": 5000000000},
                    "input": 5000000001,
                    "loc": ["body", "issue_price"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"le": 5000000000},
                    "input": 5000000001,
                    "loc": ["body", "principal_value"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"le": 1000000000000},
                    "input": 1000000000001,
                    "loc": ["body", "total_supply"],
                    "msg": "Input should be less than or equal to 1000000000000",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"max_length": 100},
                    "input": mock.ANY,
                    "loc": ["body", "symbol"],
                    "msg": "String should have at most 100 characters",
                    "type": "string_too_long",
                },
                {
                    "ctx": {"le": 5000000000.0},
                    "input": 5000000000.01,
                    "loc": ["body", "dividends"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "type": "less_than_equal",
                },
                {
                    "ctx": {"max_length": 2000},
                    "input": mock.ANY,
                    "loc": ["body", "contact_information"],
                    "msg": "String should have at most 2000 characters",
                    "type": "string_too_long",
                },
                {
                    "ctx": {"max_length": 5000},
                    "input": mock.ANY,
                    "loc": ["body", "privacy_policy"],
                    "msg": "String should have at most 5000 characters",
                    "type": "string_too_long",
                },
            ],
        }

    # <Error_2_6>
    # Validation Error
    # YYYYMMDD regex
    @pytest.mark.asyncio
    async def test_error_2_6(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "202101010",
            "dividend_payment_date": "202101010",
            "cancellation_date": "202201010",
            "principal_value": 1000,
        }
        resp = await async_client.post(
            self.apiurl,
            json=req_param,
            headers={"issuer-address": test_account["address"]},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "202101010",
                    "loc": ["body", "dividend_record_date", "constrained-str"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "202101010",
                    "loc": ["body", "dividend_record_date", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
                {
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "202101010",
                    "loc": ["body", "dividend_payment_date", "constrained-str"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "202101010",
                    "loc": ["body", "dividend_payment_date", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
                {
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "202201010",
                    "loc": ["body", "cancellation_date", "constrained-str"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {"expected": "''"},
                    "input": "202201010",
                    "loc": ["body", "cancellation_date", "literal['']"],
                    "msg": "Input should be ''",
                    "type": "literal_error",
                },
            ],
        }

    # <Error_3_1>
    # Not Exists Address
    @pytest.mark.asyncio
    async def test_error_3_1(self, async_client, async_db):
        test_account_1 = default_eth_account("user1")
        test_account_2 = default_eth_account("user2")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = await async_client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_2["address"],
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_3_2>
    # Password Mismatch
    @pytest.mark.asyncio
    async def test_error_3_2(self, async_client, async_db):
        test_account_1 = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "principal_value": 1000,
        }
        resp = await async_client.post(
            self.apiurl,
            json=req_param,
            headers={
                "issuer-address": test_account_1["address"],
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
        }

    # <Error_4_1>
    # Send Transaction Error
    # IbetShareContract.create
    @pytest.mark.asyncio
    async def test_error_4_1(self, async_client, async_db):
        test_account_1 = default_eth_account("user1")
        test_account_2 = default_eth_account("user2")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_2["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            side_effect=SendTransactionError(),
        )

        with IbetShareContract_create:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account_1["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 503
            assert resp.json() == {
                "meta": {"code": 2, "title": "SendTransactionError"},
                "detail": "failed to send transaction",
            }

    # <Error_5>
    # Send Transaction Error
    # TokenListContract.register
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        test_account_1 = default_eth_account("user1")
        test_account_2 = default_eth_account("user2")

        # prepare data
        account = Account()
        account.issuer_address = test_account_1["address"]
        account.keyfile = test_account_2["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # mock
        IbetShareContract_create = patch(
            target="app.model.ibet.token.IbetShareContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        TokenListContract_register = patch(
            target="app.model.ibet.token_list.TokenListContract.register",
            side_effect=SendTransactionError(),
        )

        with IbetShareContract_create, TokenListContract_register:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "principal_value": 1000,
            }
            resp = await async_client.post(
                self.apiurl,
                json=req_param,
                headers={
                    "issuer-address": test_account_1["address"],
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

            # assertion
            assert resp.status_code == 503
            assert resp.json() == {
                "meta": {"code": 2, "title": "SendTransactionError"},
                "detail": "failed to register token address token list",
            }


def GetRandomStr(num):
    dat = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return "".join([random.choice(dat) for i in range(num)])
