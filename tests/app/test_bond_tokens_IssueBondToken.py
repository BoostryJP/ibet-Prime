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
from app.model.ibet import TokenListContract
from app.model.ibet.token import IbetStraightBondContract
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestIssueBondToken:
    # target API endpoint
    apiurl = "/bond/tokens"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # create only
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
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
        IbetStraightBondContract_create = patch(
            target="app.model.ibet.token.IbetStraightBondContract.create",
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
            IbetStraightBondContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "20231231",
                "redemption_value": 200,
                "redemption_value_currency": "JPY",
                "purpose": "purpose_test1",
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
            IbetStraightBondContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "",
                    10000,
                    200,
                    "JPY",
                    "20231231",
                    200,
                    "JPY",
                    "",
                    "",
                    "purpose_test1",
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_STRAIGHT_BOND,
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
            assert token_1.type == TokenType.IBET_STRAIGHT_BOND
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

            operation_log = (
                await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
            ).first()
            assert operation_log.token_address == "contract_address_test1"
            assert operation_log.type == TokenType.IBET_STRAIGHT_BOND
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
        IbetStraightBondContract_create = patch(
            target="app.model.ibet.token.IbetStraightBondContract.create",
            return_value=(
                "contract_address_test1",
                "abi_test1",
                "0x0000000000000000000000000000000000000000000000000000000000000001",
            ),
        )
        ContractUtils_get_block_by_transaction_hash = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.get_block_by_transaction_hash",
            return_value={
                "number": 12345,
                "timestamp": datetime(2021, 4, 27, 12, 34, 56, tzinfo=UTC).timestamp(),
            },
        )

        with (
            IbetStraightBondContract_create,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "20211231",
                "redemption_value": 4000,
                "redemption_value_currency": "JPY",
                "return_date": "20211231",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.57,  # update
                "interest_payment_date": ["0331", "0930"],  # update
                "interest_payment_currency": "JPY",  # update
                "base_fx_rate": 123.456789,  # update
                "transferable": False,  # update
                "image_url": ["image_1"],  # update
                "status": False,  # update
                "is_offering": True,  # update
                "is_redeemed": True,  # update
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "require_personal_info_registered": False,  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test",  # update
                "transfer_approval_required": True,  # update
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
            IbetStraightBondContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "symbol_test1",
                    10000,
                    200,
                    "JPY",
                    "20211231",
                    4000,
                    "JPY",
                    "20211231",
                    "return_amount_test1",
                    "purpose_test1",
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            await AsyncContractUtils.get_block_by_transaction_hash(
                tx_hash="0x0000000000000000000000000000000000000000000000000000000000000001"
            )

            assert resp.status_code == 200
            assert resp.json()["token_address"] == "contract_address_test1"
            assert resp.json()["token_status"] == 0

            token_after = (await async_db.scalars(select(Token))).all()
            assert 0 == len(token_before)
            assert 1 == len(token_after)

            token_1 = token_after[0]
            assert token_1.id == 1
            assert token_1.type == TokenType.IBET_STRAIGHT_BOND
            assert (
                token_1.tx_hash
                == "0x0000000000000000000000000000000000000000000000000000000000000001"
            )
            assert token_1.issuer_address == test_account["address"]
            assert token_1.token_address == "contract_address_test1"
            assert token_1.abi == "abi_test1"
            assert token_1.token_status == 0
            assert token_1.version == TokenVersion.V_25_06
            assert token_1.ibet_wst_activated is None
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
            assert update_token.type == TokenType.IBET_STRAIGHT_BOND
            assert update_token.arguments == req_param
            assert update_token.status == 0
            assert update_token.trigger == "Issue"

            ibet_wst_tx = (await async_db.scalars(select(EthIbetWSTTx))).all()
            assert len(ibet_wst_tx) == 0

    # <Normal_3>
    # Authorization by auth token
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
        IbetStraightBondContract_create = patch(
            target="app.model.ibet.token.IbetStraightBondContract.create",
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
            IbetStraightBondContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "20231231",
                "redemption_value": 200,
                "redemption_value_currency": "JPY",
                "purpose": "purpose_test1",
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
            IbetStraightBondContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "",
                    10000,
                    200,
                    "JPY",
                    "20231231",
                    200,
                    "JPY",
                    "",
                    "",
                    "purpose_test1",
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_STRAIGHT_BOND,
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
            assert token_1.type == TokenType.IBET_STRAIGHT_BOND
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

            operation_log = (
                await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
            ).first()
            assert operation_log.token_address == "contract_address_test1"
            assert operation_log.type == TokenType.IBET_STRAIGHT_BOND
            assert operation_log.operation_category == "Issue"

            ibet_wst_tx = (await async_db.scalars(select(EthIbetWSTTx))).all()
            assert len(ibet_wst_tx) == 0

    # <Normal_4>
    # Activate IbetWST
    @mock.patch(
        "app.routers.issuer.bond.ETH_MASTER_ACCOUNT_ADDRESS",
        "0x1234567890123456789012345678901234567890",
    )
    @pytest.mark.asyncio
    async def test_normal_4(self, async_client, async_db):
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
        IbetStraightBondContract_create = patch(
            target="app.model.ibet.token.IbetStraightBondContract.create",
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
            IbetStraightBondContract_create,
            TokenListContract_register,
            ContractUtils_get_block_by_transaction_hash,
        ):
            # request target api
            req_param = {
                "name": "name_test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "20231231",
                "redemption_value": 200,
                "redemption_value_currency": "JPY",
                "purpose": "purpose_test1",
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
            IbetStraightBondContract.create.assert_called_with(
                args=[
                    "name_test1",
                    "",
                    10000,
                    200,
                    "JPY",
                    "20231231",
                    200,
                    "JPY",
                    "",
                    "",
                    "purpose_test1",
                ],
                tx_from=test_account["address"],
                private_key=ANY,
            )
            TokenListContract.register.assert_called_with(
                token_address="contract_address_test1",
                token_template=TokenType.IBET_STRAIGHT_BOND,
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
            assert token_1.type == TokenType.IBET_STRAIGHT_BOND
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

            operation_log = (
                await async_db.scalars(select(TokenUpdateOperationLog).limit(1))
            ).first()
            assert operation_log.token_address == "contract_address_test1"
            assert operation_log.type == TokenType.IBET_STRAIGHT_BOND
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
    #  - base_fx_rate
    #  - interest_rate
    #  - interest_payment_date
    #  - tradable_exchange_contract_address
    #  - personal_info_contract_address
    @pytest.mark.asyncio
    async def test_error_2_1(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "base_fx_rate": 123.4567899,
            "interest_rate": 12.34567,
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
            "tradable_exchange_contract_address": "0x0",
            "personal_info_contract_address": "0x0",
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
                    "type": "missing",
                    "loc": ["body", "face_value_currency"],
                    "msg": "Field required",
                    "input": {
                        "name": "name_test1",
                        "symbol": "symbol_test1",
                        "total_supply": 10000,
                        "face_value": 200,
                        "redemption_date": "20211231",
                        "redemption_value": 4000,
                        "return_date": "20211231",
                        "return_amount": "return_amount_test1",
                        "purpose": "purpose_test1",
                        "base_fx_rate": 123.4567899,
                        "interest_rate": 12.34567,
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
                        "tradable_exchange_contract_address": "0x0",
                        "personal_info_contract_address": "0x0",
                    },
                },
                {
                    "type": "value_error",
                    "loc": ["body", "interest_rate"],
                    "msg": "Value error, interest_rate must be less than or equal to four decimal places",
                    "input": 12.34567,
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "interest_payment_date"],
                    "msg": "Value error, list length of interest_payment_date must be less than 13",
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
                    "ctx": {"error": {}},
                },
                {
                    "type": "value_error",
                    "loc": ["body", "base_fx_rate"],
                    "msg": "Value error, base_fx_rate must be less than or equal to six decimal places",
                    "input": 123.4567899,
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
            "total_supply": 10000,
            "face_value": 200,
            "face_value_currency": "JPY",
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
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
            "total_supply": 10000,
            "face_value": 200,
            "face_value_currency": "JPY",
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
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
    # optional fields
    @pytest.mark.asyncio
    async def test_error_2_4(self, async_client, async_db):
        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "face_value_currency": "JPY",
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "is_redeemed": "invalid value",
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
                    "input": "invalid value",
                    "loc": ["body", "is_redeemed"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "type": "bool_parsing",
                }
            ],
        }

    # <Error_2_5>
    # Validation Error
    # min value
    @pytest.mark.asyncio
    async def test_error_2_5(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": -1,
            "face_value": -1,
            "face_value_currency": "JPY",
            "redemption_date": "20211231",
            "redemption_value": -1,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "base_fx_rate": -0.000001,  # update
            "interest_rate": -0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "is_offering": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
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
                    "type": "greater_than_equal",
                    "loc": ["body", "total_supply"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -1,
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "face_value"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -1,
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "redemption_value"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -1,
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "interest_rate"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -0.0001,
                    "ctx": {"ge": 0.0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["body", "base_fx_rate"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": -1e-06,
                    "ctx": {"ge": 0.0},
                },
            ],
        }

    # <Error_2_6>
    # Validation Error
    # max value or max length
    @pytest.mark.asyncio
    async def test_error_2_6(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # request target api
        req_param = {
            "name": GetRandomStr(101),
            "symbol": GetRandomStr(101),
            "total_supply": 1_000_000_000_001,
            "face_value": 5_000_000_001,
            "redemption_date": "20211231",
            "redemption_value": 5_000_000_001,
            "return_date": "20211231",
            "return_amount": GetRandomStr(2001),
            "purpose": GetRandomStr(2001),
            "interest_rate": 100.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "is_offering": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": GetRandomStr(2001),  # update
            "privacy_policy": GetRandomStr(5001),  # update
            "transfer_approval_required": True,  # update
            "face_value_currency": "JPYY",
            "redemption_value_currency": "JPYY",
            "interest_payment_currency": "JPYY",
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
                    "type": "string_too_long",
                    "loc": ["body", "name"],
                    "msg": "String should have at most 100 characters",
                    "input": ANY,
                    "ctx": {"max_length": 100},
                },
                {
                    "type": "less_than_equal",
                    "loc": ["body", "total_supply"],
                    "msg": "Input should be less than or equal to 1000000000000",
                    "input": 1000000000001,
                    "ctx": {"le": 1000000000000},
                },
                {
                    "type": "less_than_equal",
                    "loc": ["body", "face_value"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "input": 5000000001,
                    "ctx": {"le": 5000000000},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "face_value_currency"],
                    "msg": "String should have at most 3 characters",
                    "input": "JPYY",
                    "ctx": {"max_length": 3},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "purpose"],
                    "msg": "String should have at most 2000 characters",
                    "input": ANY,
                    "ctx": {"max_length": 2000},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "symbol"],
                    "msg": "String should have at most 100 characters",
                    "input": ANY,
                    "ctx": {"max_length": 100},
                },
                {
                    "type": "less_than_equal",
                    "loc": ["body", "redemption_value"],
                    "msg": "Input should be less than or equal to 5000000000",
                    "input": 5000000001,
                    "ctx": {"le": 5000000000},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "redemption_value_currency"],
                    "msg": "String should have at most 3 characters",
                    "input": "JPYY",
                    "ctx": {"max_length": 3},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "return_amount"],
                    "msg": "String should have at most 2000 characters",
                    "input": ANY,
                    "ctx": {"max_length": 2000},
                },
                {
                    "type": "less_than_equal",
                    "loc": ["body", "interest_rate"],
                    "msg": "Input should be less than or equal to 100",
                    "input": 100.0001,
                    "ctx": {"le": 100.0},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "interest_payment_currency"],
                    "msg": "String should have at most 3 characters",
                    "input": "JPYY",
                    "ctx": {"max_length": 3},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "contact_information"],
                    "msg": "String should have at most 2000 characters",
                    "input": ANY,
                    "ctx": {"max_length": 2000},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "privacy_policy"],
                    "msg": "String should have at most 5000 characters",
                    "input": ANY,
                    "ctx": {"max_length": 5000},
                },
            ],
        }

    # <Error_2_7>
    # Validation Error
    # YYYYMMDD/MMDD regex
    @pytest.mark.asyncio
    async def test_error_2_7(self, async_client, async_db):
        # request target api
        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "face_value_currency": "JPY",
            "redemption_date": "invalid_date",
            "redemption_value": 4000,
            "return_date": "invalid_date",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_payment_date": ["invalid_date"],  # update
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
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "invalid_date",
                    "loc": ["body", "redemption_date"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {
                        "pattern": "^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"
                    },
                    "input": "invalid_date",
                    "loc": ["body", "return_date"],
                    "msg": "String should match pattern "
                    "'^(19[0-9]{2}|20[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
                },
                {
                    "ctx": {"pattern": "^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$"},
                    "input": "invalid_date",
                    "loc": ["body", "interest_payment_date", 0],
                    "msg": "String should match pattern "
                    "'^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$'",
                    "type": "string_pattern_mismatch",
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
            "total_supply": 10000,
            "face_value": 200,
            "face_value_currency": "JPY",
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
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
            "total_supply": 10000,
            "face_value": 200,
            "face_value_currency": "JPY",
            "redemption_date": "20211231",
            "redemption_value": 4000,
            "return_date": "20211231",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
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
    # IbetStraightBondContract.create
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
        IbetStraightBondContract_create = patch(
            target="app.model.ibet.token.IbetStraightBondContract.create",
            side_effect=SendTransactionError(),
        )

        with IbetStraightBondContract_create:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "20211231",
                "redemption_value": 4000,
                "return_date": "20211231",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
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

    # <Error_4_2>
    # Send Transaction Error
    # TokenListContract.register
    @pytest.mark.asyncio
    async def test_error_4_2(self, async_client, async_db):
        test_account = default_eth_account("user1")

        # prepare data
        account = Account()
        account.issuer_address = test_account["address"]
        account.keyfile = test_account["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        await async_db.commit()

        # mock
        IbetStraightBondContract_create = patch(
            target="app.model.ibet.token.IbetStraightBondContract.create",
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

        with IbetStraightBondContract_create, TokenListContract_register:
            # request target api
            req_param = {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 10000,
                "face_value": 200,
                "face_value_currency": "JPY",
                "redemption_date": "20211231",
                "redemption_value": 4000,
                "redemption_value_currency": "JPY",
                "return_date": "20211231",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
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
            assert resp.status_code == 503
            assert resp.json() == {
                "meta": {"code": 2, "title": "SendTransactionError"},
                "detail": "failed to register token address token list",
            }


def GetRandomStr(num):
    dat = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return "".join([random.choice(dat) for i in range(num)])
