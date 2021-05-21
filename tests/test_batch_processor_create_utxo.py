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
from unittest.mock import call, MagicMock
import time
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_keyfile import decode_keyfile_json

from config import WEB3_HTTP_PROVIDER
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import Token, TokenType, UTXO, UTXOBlockNumber
from app.model.schema import IbetShareTransfer, IbetStraightBondTransfer
from batch.processor_create_utxo import Sinks, DBSink, Processor
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope='function')
def processor(db):
    _sink = Sinks()
    _sink.register(DBSink(db))
    return Processor(sink=_sink, db=db)


def deploy_bond_token_contract(address, private_key):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        "token.redemption_date",
        30,
        "token.return_date",
        "token.return_amount",
        "token.purpose"
    ]

    contract_address, _, _ = IbetStraightBondContract.create(arguments, address, private_key)

    return contract_address


def deploy_share_token_contract(address, private_key):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        int(0.03 * 100),
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date"
    ]

    contract_address, _, _ = IbetShareContract.create(arguments, address, private_key)

    return contract_address


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Execute Batch Run 1st: No Event
    # Execute Batch Run 2nd: Executed Transfer Event
    # Localized:JPN
    @mock.patch("batch.lib.create_ledger.create_ledger")
    def test_normal_1(self, mock_func, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        token_address_2 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        # Execute batch(Run 1st)
        # Assume: Skip processing
        latest_block = web3.eth.blockNumber
        processor.process()

        # assertion
        _utox_list = db.query(UTXO).all()
        assert len(_utox_list) == 0
        _utox_block_number = db.query(UTXOBlockNumber).first()
        assert _utox_block_number.latest_block_number == latest_block

        # Execute Transfer Event
        latest_block = web3.eth.blockNumber
        # Share:issuer -> user1
        _transfer_1 = IbetShareTransfer(
            token_address=token_address_2,
            transfer_from=issuer_address,
            transfer_to=user_address_1,
            amount=70
        )
        IbetShareContract.transfer(_transfer_1, issuer_address, issuer_private_key)
        time.sleep(1)

        # Bond:issuer -> user1
        _transfer_2 = IbetStraightBondTransfer(
            token_address=token_address_1,
            transfer_from=issuer_address,
            transfer_to=user_address_1,
            amount=40
        )
        IbetStraightBondContract.transfer(_transfer_2, issuer_address, issuer_private_key)
        time.sleep(1)

        # Bond:issuer -> user2
        _transfer_3 = IbetStraightBondTransfer(
            token_address=token_address_1,
            transfer_from=issuer_address,
            transfer_to=user_address_2,
            amount=20
        )
        IbetStraightBondContract.transfer(_transfer_3, issuer_address, issuer_private_key)
        time.sleep(1)

        # Share:user1 -> user2
        _transfer_4 = IbetShareTransfer(
            token_address=token_address_2,
            transfer_from=user_address_1,
            transfer_to=user_address_2,
            amount=10
        )
        IbetShareContract.transfer(_transfer_4, issuer_address, issuer_private_key)
        time.sleep(1)

        # Execute batch(Run 2nd)
        # Assume: Create UTXO
        pre_datetime = datetime.utcnow()
        processor.process()

        # assertion
        _utox_list = db.query(UTXO).all()
        # 1.Bond token:issuer -> user1 (tx2)
        # 2.Bond token:issuer -> user2 (tx3)
        # 3.Share token:issuer -> user1 (tx1)
        # 4.Share token:user1 -> issuer (tx4)
        assert len(_utox_list) == 4
        _utox = _utox_list[0]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 40
        assert _utox.block_number > _utox_list[2].block_number
        assert _utox.block_timestamp > _utox_list[2].block_timestamp
        _utox = _utox_list[1]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 20
        assert _utox.block_number > _utox_list[0].block_number
        assert _utox.block_timestamp > _utox_list[0].block_timestamp
        _utox = _utox_list[2]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_2
        assert _utox.amount == 60  # spend to user2(70 - 10)
        assert _utox.block_number is not None
        assert _utox.block_timestamp is not None
        _utox = _utox_list[3]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_2
        assert _utox.amount == 10
        assert _utox.block_number > _utox_list[1].block_number
        assert _utox.block_timestamp > _utox_list[1].block_timestamp
        _utox_block_number = db.query(UTXOBlockNumber).first()
        assert _utox_block_number.latest_block_number == _utox_list[3].block_number

        mock_func.assert_has_calls([
            call(token_address_1, db),
            call(token_address_1, db),
            call(token_address_2, db),
            call(token_address_2, db)
        ])

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Web3 Error
    def test_error_1(self, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        # Execute batch
        latest_block = web3.eth.blockNumber
        with mock.patch("web3.eth.Eth.uninstallFilter", MagicMock(side_effect=Exception("mock test"))) as web3_mock:
            processor.process()

        _utox_list = db.query(UTXO).all()
        assert len(_utox_list) == 0
        _utox_block_number = db.query(UTXOBlockNumber).first()
        assert _utox_block_number.latest_block_number == latest_block
