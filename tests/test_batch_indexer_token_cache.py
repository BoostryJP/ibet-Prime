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

import logging
import time
from datetime import datetime
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import Account, Token, TokenCache, TokenType, TokenVersion
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import Web3Wrapper
from batch.indexer_token_cache import LOG, Processor, main
from config import ZERO_ADDRESS
from tests.account_config import config_eth_account

web3 = Web3Wrapper()


@pytest.fixture(scope="function")
def main_func():
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield main
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.fixture(scope="function")
def processor(db, caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor()
    LOG.propagate = False
    LOG.setLevel(default_log_level)


async def deploy_bond_token_contract(
    address,
    private_key,
    personal_info_contract_address,
    tradable_exchange_contract_address=None,
    transfer_approval_required=None,
):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        "JPY",
        "token.redemption_date",
        30,
        "JPY",
        "token.return_date",
        "token.return_amount",
        "token.purpose",
    ]
    bond_contrat = IbetStraightBondContract()
    token_address, _, _ = await bond_contrat.create(arguments, address, private_key)
    await bond_contrat.update(
        data=IbetStraightBondUpdateParams(
            transferable=True,
            personal_info_contract_address=personal_info_contract_address,
            tradable_exchange_contract_address=tradable_exchange_contract_address,
            transfer_approval_required=transfer_approval_required,
        ),
        tx_from=address,
        private_key=private_key,
    )

    return ContractUtils.get_contract("IbetStraightBond", token_address)


async def deploy_share_token_contract(
    address,
    private_key,
    personal_info_contract_address,
    tradable_exchange_contract_address=None,
    transfer_approval_required=None,
):
    arguments = [
        "token.name",
        "token.symbol",
        20,
        100,
        3,
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        30,
    ]
    share_contract = IbetShareContract()
    token_address, _, _ = await share_contract.create(arguments, address, private_key)
    await share_contract.update(
        data=IbetShareUpdateParams(
            transferable=True,
            personal_info_contract_address=personal_info_contract_address,
            tradable_exchange_contract_address=tradable_exchange_contract_address,
            transfer_approval_required=transfer_approval_required,
        ),
        tx_from=address,
        private_key=private_key,
    )

    return ContractUtils.get_contract("IbetShare", token_address)


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Single Token
    # not issue token
    @pytest.mark.asyncio
    async def test_normal_1_1(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Token(processing token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = "abi"
        token_1.tx_hash = "tx_hash"
        token_1.token_status = 0
        token_1.version = TokenVersion.V_23_12
        db.add(token_1)

        db.commit()

        sleep_mock = AsyncMock()
        sleep_mock.return_value = 0

        # Run target process
        with mock.patch("asyncio.sleep", sleep_mock):
            await processor.process()
        # Assertion
        _cache_list = db.scalars(
            select(TokenCache).order_by(TokenCache.cached_datetime)
        ).all()
        assert len(_cache_list) == 0

    # <Normal_1_2>
    # Multi Token
    # issued token
    @pytest.mark.asyncio
    async def test_normal_1_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_23_12
        db.add(token_1)

        # Prepare data : Token
        token_contract_2 = await deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_23_12
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        token_3.version = TokenVersion.V_23_12
        db.add(token_3)

        db.commit()

        before_cache_time = datetime.utcnow()

        sleep_mock = AsyncMock()
        sleep_mock.return_value = 0

        # Run target process
        with mock.patch("asyncio.sleep", sleep_mock):
            await processor.process()

        # Assertion
        _cache_list = db.scalars(
            select(TokenCache).order_by(TokenCache.cached_datetime)
        ).all()
        assert len(_cache_list) == 2

        assert _cache_list[0].token_address == token_contract_1.address
        assert _cache_list[0].cached_datetime >= before_cache_time
        assert _cache_list[0].expiration_datetime >= before_cache_time
        assert _cache_list[0].attributes == {
            "contract_name": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "issuer_address": issuer_address,
            "name": "token.name",
            "symbol": "token.symbol",
            "total_supply": 100,
            "tradable_exchange_contract_address": ZERO_ADDRESS,
            "contact_information": "",
            "privacy_policy": "",
            "status": True,
            "personal_info_contract_address": personal_info_contract.address,
            "transferable": True,
            "is_offering": False,
            "transfer_approval_required": False,
            "face_value": 20,
            "face_value_currency": "JPY",
            "interest_rate": 0.0,
            "interest_payment_currency": "",
            "redemption_date": "token.redemption_date",
            "redemption_value": 30,
            "redemption_value_currency": "JPY",
            "return_date": "token.return_date",
            "return_amount": "token.return_amount",
            "base_fx_rate": 0.0,
            "purpose": "token.purpose",
            "memo": "",
            "is_redeemed": False,
            "interest_payment_date": ["", "", "", "", "", "", "", "", "", "", "", ""],
        }

        assert _cache_list[1].token_address == token_contract_2.address
        assert _cache_list[1].cached_datetime >= before_cache_time
        assert _cache_list[1].expiration_datetime >= before_cache_time
        assert _cache_list[1].attributes == {
            "cancellation_date": "token.cancellation_date",
            "contact_information": "",
            "contract_name": "IbetShare",
            "dividend_payment_date": "token.dividend_payment_date",
            "dividend_record_date": "token.dividend_record_date",
            "dividends": 3e-13,
            "is_canceled": False,
            "is_offering": False,
            "issue_price": 20,
            "issuer_address": issuer_address,
            "memo": "",
            "name": "token.name",
            "personal_info_contract_address": personal_info_contract.address,
            "principal_value": 30,
            "privacy_policy": "",
            "status": True,
            "symbol": "token.symbol",
            "token_address": token_address_2,
            "total_supply": 100,
            "tradable_exchange_contract_address": ZERO_ADDRESS,
            "transfer_approval_required": False,
            "transferable": True,
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # If each error occurs, batch will output logs and continue next sync.
    @pytest.mark.asyncio
    async def test_error_1(
        self,
        main_func,
        db: Session,
        personal_info_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_23_12
        db.add(token_1)

        db.commit()

        # Run mainloop once and fail with web3 utils error
        sleep_mock = AsyncMock()
        sleep_mock.side_effect = [TypeError]

        # Run target process
        with (
            patch("batch.indexer_token_cache.INDEXER_SYNC_INTERVAL", None),
            patch("asyncio.sleep", sleep_mock),
            patch(
                target="app.utils.contract_utils.AsyncContractUtils.call_function",
                side_effect=ServiceUnavailableError(),
            ),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()

        # Run mainloop once and fail with sqlalchemy InvalidRequestError
        with patch("batch.indexer_token_cache.INDEXER_SYNC_INTERVAL", None), patch(
            "batch.indexer_token_cache.INDEXER_SYNC_INTERVAL", None
        ), patch.object(
            AsyncSession, "scalars", side_effect=InvalidRequestError()
        ), pytest.raises(
            TypeError
        ):
            await main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()
