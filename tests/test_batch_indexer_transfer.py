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
from datetime import datetime

from eth_keyfile import decode_keyfile_json

from config import (
    CHAIN_ID,
    TX_GAS_LIMIT
)
from app.model.db import (
    Token,
    TokenType,
    IDXTransfer,
    IDXTransferBlockNumber
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract
)
from app.model.schema import (
    IbetStraightBondUpdate,
    IbetShareUpdate
)
from app.utils.web3_utils import Web3Wrapper
from app.utils.contract_utils import ContractUtils
from batch.indexer_transfer import Processor
from tests.account_config import config_eth_account

web3 = Web3Wrapper()


@pytest.fixture(scope="function")
def processor(db):
    return Processor()


def deploy_bond_token_contract(address,
                               private_key,
                               personal_info_contract_address,
                               tradable_exchange_contract_address=None,
                               transfer_approval_required=None):
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

    token_address, _, _ = IbetStraightBondContract.create(arguments, address, private_key)
    IbetStraightBondContract.update(
        contract_address=token_address,
        data=IbetStraightBondUpdate(transferable=True,
                                    personal_info_contract_address=personal_info_contract_address,
                                    tradable_exchange_contract_address=tradable_exchange_contract_address,
                                    transfer_approval_required=transfer_approval_required),
        tx_from=address,
        private_key=private_key
    )

    return ContractUtils.get_contract("IbetStraightBond", token_address)


def deploy_share_token_contract(address,
                                private_key,
                                personal_info_contract_address,
                                tradable_exchange_contract_address=None,
                                transfer_approval_required=None):
    arguments = [
        "token.name",
        "token.symbol",
        20,
        100,
        int(0.03 * 100),
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        30
    ]

    token_address, _, _ = IbetShareContract.create(arguments, address, private_key)
    IbetShareContract.update(
        contract_address=token_address,
        data=IbetShareUpdate(transferable=True,
                             personal_info_contract_address=personal_info_contract_address,
                             tradable_exchange_contract_address=tradable_exchange_contract_address,
                             transfer_approval_required=transfer_approval_required),
        tx_from=address,
        private_key=private_key
    )

    return ContractUtils.get_contract("IbetShare", token_address)


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Single Token
    # No event logs
    # not issue token
    def test_normal_1_1(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Token(processing token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = "abi"
        token_1.tx_hash = "tx_hash"
        token_1.token_status = 0
        db.add(token_1)

        db.commit()

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_list = db.query(IDXTransfer).all()
        assert len(_transfer_list) == 0
        _idx_transfer_block_number = db.query(IDXTransferBlockNumber).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # Single Token
    # No event logs
    # issued token
    def test_normal_1_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_block_number = IDXTransferBlockNumber()
        _idx_transfer_block_number.latest_block_number = 0
        db.add(_idx_transfer_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_list = db.query(IDXTransfer).all()
        assert len(_transfer_list) == 0
        _idx_transfer_block_number = db.query(IDXTransferBlockNumber).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_2>
    # Single Token
    # Single event logs
    # - Transfer
    def test_normal_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(issuer_address, user_address_1, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_list = db.query(IDXTransfer).all()
        assert len(_transfer_list) == 1
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer.block_timestamp == datetime.utcfromtimestamp(block["timestamp"])
        _idx_transfer_block_number = db.query(IDXTransferBlockNumber).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_3_1>
    # Single Token
    # Multi event logs
    # - Transfer(twice)
    def test_normal_3_1(self, processor, db, personal_info_contract):
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(issuer_address, user_address_1, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)
        tx = token_contract_1.functions.transferFrom(issuer_address, user_address_2, 30).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_list = db.query(IDXTransfer).all()
        assert len(_transfer_list) == 2
        _transfer = _transfer_list[0]
        assert _transfer.id == 1
        assert _transfer.transaction_hash == tx_hash_1
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_1
        assert _transfer.amount == 40
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer.block_timestamp == datetime.utcfromtimestamp(block["timestamp"])
        _transfer = _transfer_list[1]
        assert _transfer.id == 2
        assert _transfer.transaction_hash == tx_hash_2
        assert _transfer.token_address == token_address_1
        assert _transfer.from_address == issuer_address
        assert _transfer.to_address == user_address_2
        assert _transfer.amount == 30
        block = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _transfer.block_timestamp == datetime.utcfromtimestamp(block["timestamp"])
        _idx_transfer_block_number = db.query(IDXTransferBlockNumber).first()
        assert _idx_transfer_block_number.id == 1
        assert _idx_transfer_block_number.latest_block_number == block_number

    # <Normal_3_2>
    # Single Token
    # Multi event logs
    # - Transfer(BulkTransfer)
    def test_normal_3_2(self, processor, db, personal_info_contract):
        # TODO
        pass

    # <Normal_4>
    # Multi Token
    def test_normal_4(self, processor, db, personal_info_contract):
        # TODO
        pass
