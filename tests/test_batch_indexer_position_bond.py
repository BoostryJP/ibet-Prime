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

from eth_keyfile import decode_keyfile_json

from config import (
    CHAIN_ID,
    TX_GAS_LIMIT,
    ZERO_ADDRESS
)
from app.model.db import (
    Token,
    TokenType,
    IDXPosition,
    IDXPositionBondBlockNumber
)
from app.model.blockchain import IbetStraightBondContract
from app.model.schema import IbetStraightBondUpdate
from app.utils.web3_utils import Web3Wrapper
from app.utils.contract_utils import ContractUtils
from batch.indexer_position_bond import Processor
from tests.account_config import config_eth_account
from tests.utils.contract_utils import PersonalInfoContractTestUtils

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

        # Prepare data : Token(share token)
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = "abi"
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

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

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

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        # Prepare data : BlockNumber
        _idx_position_bond_block_number = IDXPositionBondBlockNumber()
        _idx_position_bond_block_number.latest_block_number = 0
        db.add(_idx_position_bond_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Single Token
    # Single event logs
    # - Issue
    def test_normal_2_1(self, processor, db, personal_info_contract):
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

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Issue
        tx = token_contract_1.functions.issueFrom(user_address_1, ZERO_ADDRESS, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == user_address_1).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_2_1>
    # Single Token
    # Single event logs
    # - Transfer(to account)
    def test_normal_2_2_1(self, processor, db, personal_info_contract):
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

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(issuer_address, user_address_1, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == user_address_1).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_2_2>
    # Single Token
    # Single event logs
    # - Transfer(to DEX)
    def test_normal_2_2_2(self, processor, db, personal_info_contract, ibet_escrow_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      ibet_escrow_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_escrow_contract.address, 40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_2_3>
    # Single Token
    # Single event logs
    # - Transfer(HolderChanged in DEX)
    def test_normal_2_2_3(self, processor, db, personal_info_contract, ibet_escrow_contract):
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
                                                      personal_info_contract.address,
                                                      ibet_escrow_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_escrow_contract.address, 40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # Holder Change
        tx = ibet_escrow_contract.functions.createEscrow(
            token_contract_1.address, user_address_1, 30, issuer_address, ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)
        escrow_id = ContractUtils.call_function(
            ibet_escrow_contract, "latestEscrowId", ())
        tx = ibet_escrow_contract.functions.finishEscrow(escrow_id).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        db.rollback()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == user_address_1).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_3>
    # Single Token
    # Single event logs
    # - Lock
    def test_normal_2_3(self, processor, db, personal_info_contract):
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

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Lock
        tx = token_contract_1.functions.authorizeLockAddress(issuer_address, True).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)
        tx = token_contract_1.functions.lock(issuer_address, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_4>
    # Single Token
    # Single event logs
    # - Unlock
    def test_normal_2_4(self, processor, db, personal_info_contract):
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

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Lock
        tx = token_contract_1.functions.authorizeLockAddress(issuer_address, True).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)
        tx = token_contract_1.functions.lock(issuer_address, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # Unlock
        tx = token_contract_1.functions.unlock(issuer_address, issuer_address, 30).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        db.rollback()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40 + 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_5>
    # Single Token
    # Single event logs
    # - Redeem
    def test_normal_2_5(self, processor, db, personal_info_contract):
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

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Redeem
        tx = token_contract_1.functions.redeemFrom(issuer_address, ZERO_ADDRESS, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_6>
    # Single Token
    # Single event logs
    # - ApplyForTransfer
    def test_normal_2_6(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # ApplyForTransfer
        PersonalInfoContractTestUtils.register(personal_info_contract.address,
                                               user_address_1,
                                               user_private_key_1,
                                               [issuer_address, "test"])
        tx = token_contract_1.functions.applyForTransfer(user_address_1, 40, "").buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_7>
    # Single Token
    # Single event logs
    # - CancelTransfer
    def test_normal_2_7(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # ApplyForTransfer
        PersonalInfoContractTestUtils.register(personal_info_contract.address,
                                               user_address_1,
                                               user_private_key_1,
                                               [issuer_address, "test"])
        tx = token_contract_1.functions.applyForTransfer(user_address_1, 40, "").buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40

        # CancelTransfer
        tx = token_contract_1.functions.cancelTransfer(0, "").buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        db.rollback()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_8>
    # Single Token
    # Single event logs
    # - ApproveTransfer
    def test_normal_2_8(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # ApplyForTransfer
        PersonalInfoContractTestUtils.register(personal_info_contract.address,
                                               user_address_1,
                                               user_private_key_1,
                                               [issuer_address, "test"])
        tx = token_contract_1.functions.applyForTransfer(user_address_1, 40, "").buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40

        # ApproveTransfer
        tx = token_contract_1.functions.approveTransfer(0, "").buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        db.rollback()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == user_address_1).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_9_1>
    # Single Token
    # Single event logs
    # - IbetExchange: NewOrder
    def test_normal_2_9_1(self, processor, db, personal_info_contract, ibet_exchange_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      tradable_exchange_contract_address=ibet_exchange_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_exchange_contract.address, 40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # NewOrder(Sell)
        tx = ibet_exchange_contract.functions.createOrder(
            token_address_1, 30, 10000, False, issuer_address
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        db.rollback()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 30
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_9_2>
    # Single Token
    # Single event logs
    # - IbetExchange: CancelOrder
    def test_normal_2_9_2(self, processor, db, personal_info_contract, ibet_exchange_contract):
        # TODO
        pass

    # <Normal_2_9_3>
    # Single Token
    # Single event logs
    # - IbetExchange: ForceCancelOrder
    def test_normal_2_9_3(self, processor, db, personal_info_contract, ibet_exchange_contract):
        # TODO
        pass

    # <Normal_2_9_4>
    # Single Token
    # Single event logs
    # - IbetExchange: Agree
    def test_normal_2_9_4(self, processor, db, personal_info_contract, ibet_exchange_contract):
        # TODO
        pass

    # <Normal_2_9_5>
    # Single Token
    # Single event logs
    # - IbetExchange: SettlementOK
    def test_normal_2_9_5(self, processor, db, personal_info_contract, ibet_exchange_contract):
        # TODO
        pass

    # <Normal_2_9_6>
    # Single Token
    # Single event logs
    # - IbetExchange: SettlementNG
    def test_normal_2_9_6(self, processor, db, personal_info_contract, ibet_exchange_contract):
        # TODO
        pass

    # <Normal_2_10_1>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowCreated
    def test_normal_2_10_1(self, processor, db, personal_info_contract, ibet_security_token_escrow_contract):
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
                                                      personal_info_contract.address,
                                                      ibet_security_token_escrow_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_escrow_contract.address, 40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # EscrowCreated
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_contract_1.address, user_address_1, 30, issuer_address, "", ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        db.rollback()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 30
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_2_10_2>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowCanceled
    def test_normal_2_10_2(self, processor, db, personal_info_contract, ibet_security_token_escrow_contract):
        # TODO
        pass

    # <Normal_2_10_3>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowFinished
    def test_normal_2_10_3(self, processor, db, personal_info_contract, ibet_security_token_escrow_contract):
        # TODO
        pass

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
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"],
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

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        # Transfer: 1st
        tx = token_contract_1.functions.transferFrom(issuer_address, user_address_1, 40).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Transfer: 2nd
        PersonalInfoContractTestUtils.register(personal_info_contract.address,
                                               user_address_1,
                                               user_private_key_1,
                                               [issuer_address, "test"])
        PersonalInfoContractTestUtils.register(personal_info_contract.address,
                                               user_address_2,
                                               user_private_key_2,
                                               [issuer_address, "test"])
        tx = token_contract_1.functions.transfer(user_address_2, 10).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == issuer_address).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == user_address_1).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = db.query(IDXPosition).filter(IDXPosition.account_address == user_address_2).first()
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_bond_block_number = db.query(IDXPositionBondBlockNumber).first()
        assert _idx_position_bond_block_number.id == 1
        assert _idx_position_bond_block_number.latest_block_number == block_number

    # <Normal_3_2>
    # Single Token
    # Multi event logs
    # - Transfer(BulkTransfer)
    def test_normal_3_2(self, processor, db, personal_info_contract):
        # TODO
        pass

    # <Normal_3_3>
    # Single Token
    # Multi event logs
    # - IbetExchange: NewOrder
    # - IbetExchange: CancelOrder
    def test_normal_3_3(self, processor, db, personal_info_contract):
        # TODO
        pass

    # <Normal_3_4>
    # Single Token
    # Multi event logs
    # - IbetSecurityTokenEscrow: EscrowCreated
    # - IbetSecurityTokenEscrow: EscrowCanceled
    def test_normal_3_4(self, processor, db, personal_info_contract):
        # TODO
        pass

    # <Normal_4>
    # Multi Token
    def test_normal_4(self, processor, db, personal_info_contract):
        # TODO
        pass
