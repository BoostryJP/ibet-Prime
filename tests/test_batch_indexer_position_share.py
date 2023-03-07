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
from unittest import mock
from unittest.mock import patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.db import (
    IDXLock,
    IDXLockedPosition,
    IDXPosition,
    IDXPositionShareBlockNumber,
    IDXUnlock,
    Notification,
    NotificationType,
    Token,
    TokenType,
)
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from batch.indexer_position_share import LOG, Processor, main
from config import CHAIN_ID, TX_GAS_LIMIT, ZERO_ADDRESS
from tests.account_config import config_eth_account
from tests.utils.contract_utils import IbetExchangeContractTestUtils
from tests.utils.contract_utils import (
    IbetSecurityTokenContractTestUtils as STContractUtils,
)
from tests.utils.contract_utils import (
    IbetSecurityTokenEscrowContractTestUtils as STEscrowContractUtils,
)
from tests.utils.contract_utils import PersonalInfoContractTestUtils

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


def deploy_share_token_contract(
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
    token_address, _, _ = share_contract.create(arguments, address, private_key)
    share_contract.update(
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
    # No event logs
    # not issue token
    def test_normal_1_1(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Token(bond token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = "abi"
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # Single Token
    # No event logs
    # issued token
    def test_normal_1_2(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        # Prepare data : BlockNumber
        _idx_position_share_block_number = IDXPositionShareBlockNumber()
        _idx_position_share_block_number.latest_block_number = 0
        db.add(_idx_position_share_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Single Token
    # Single event logs
    # - Issue
    def test_normal_2_1(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Issue
        tx = token_contract_1.functions.issueFrom(
            user_address_1, ZERO_ADDRESS, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_2_1>
    # Single Token
    # Single event logs
    # - Transfer(to account)
    def test_normal_2_2_1(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_2_2>
    # Single Token
    # Single event logs
    # - Transfer(to DEX)
    def test_normal_2_2_2(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_escrow_contract,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            ibet_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
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
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_2_3>
    # Single Token
    # Single event logs
    # - Transfer(HolderChanged in DEX)
    def test_normal_2_2_3(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_escrow_contract,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            ibet_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
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
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # Holder Change
        tx = ibet_escrow_contract.functions.createEscrow(
            token_contract_1.address, user_address_1, 30, issuer_address, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)
        escrow_id = ContractUtils.call_function(
            ibet_escrow_contract, "latestEscrowId", ()
        )
        tx = ibet_escrow_contract.functions.finishEscrow(escrow_id).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_3>
    # Single Token
    # Single event logs
    # - Lock
    def test_normal_2_3(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Lock
        tx = token_contract_1.functions.lock(
            issuer_address, 40, '{"message": "locked1"}'
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1

        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _locked_position = (
            db.query(IDXLockedPosition)
            .filter(IDXLockedPosition.token_address == token_address_1)
            .filter(IDXLockedPosition.account_address == issuer_address)
            .first()
        )
        assert _locked_position.token_address == token_address_1
        assert _locked_position.lock_address == issuer_address
        assert _locked_position.account_address == issuer_address
        assert _locked_position.value == 40

        _lock_list = db.query(IDXLock).order_by(IDXLock.id).all()
        assert len(_lock_list) == 1

        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token_address_1
        assert _lock1.lock_address == issuer_address
        assert _lock1.account_address == issuer_address
        assert _lock1.value == 40
        assert _lock1.data == {"message": "locked1"}

        _notification_list = db.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 1

        _notification1 = _notification_list[0]
        assert _notification1.id == 1
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.LOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 40,
            "data": {"message": "locked1"},
        }

        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_4>
    # Single Token
    # Single event logs
    # - Unlock
    def test_normal_2_4(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Lock
        tx = token_contract_1.functions.lock(
            issuer_address, 40, '{"message": "locked1"}'
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1

        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # Unlock
        tx = token_contract_1.functions.unlock(
            issuer_address, issuer_address, 30, '{"message": "unlocked1"}'
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1

        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40 + 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        _locked_position = (
            db.query(IDXLockedPosition)
            .filter(IDXLockedPosition.token_address == token_address_1)
            .filter(IDXLockedPosition.account_address == issuer_address)
            .first()
        )
        assert _locked_position.token_address == token_address_1
        assert _locked_position.lock_address == issuer_address
        assert _locked_position.account_address == issuer_address
        assert _locked_position.value == 40 - 30

        _lock_list = db.query(IDXLock).order_by(IDXLock.id).all()
        assert len(_lock_list) == 1

        _lock1 = _lock_list[0]
        assert _lock1.id == 1
        assert _lock1.token_address == token_address_1
        assert _lock1.lock_address == issuer_address
        assert _lock1.account_address == issuer_address
        assert _lock1.value == 40
        assert _lock1.data == {"message": "locked1"}

        _unlock_list = db.query(IDXUnlock).order_by(IDXUnlock.id).all()
        assert len(_unlock_list) == 1

        _unlock1 = _unlock_list[0]
        assert _unlock1.id == 1
        assert _unlock1.token_address == token_address_1
        assert _unlock1.lock_address == issuer_address
        assert _unlock1.account_address == issuer_address
        assert _unlock1.recipient_address == issuer_address
        assert _unlock1.value == 30
        assert _unlock1.data == {"message": "unlocked1"}

        _notification_list = db.query(Notification).order_by(Notification.created).all()
        assert len(_notification_list) == 2

        _notification1 = _notification_list[0]
        assert _notification1.id == 1
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.LOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "value": 40,
            "data": {"message": "locked1"},
        }

        _notification1 = _notification_list[1]
        assert _notification1.id == 2
        assert _notification1.issuer_address == issuer_address
        assert _notification1.priority == 0
        assert _notification1.type == NotificationType.UNLOCK_INFO
        assert _notification1.metainfo == {
            "token_address": token_address_1,
            "token_type": "IbetShare",
            "account_address": issuer_address,
            "lock_address": issuer_address,
            "recipient_address": issuer_address,
            "value": 30,
            "data": {"message": "unlocked1"},
        }

        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_5>
    # Single Token
    # Single event logs
    # - Redeem
    def test_normal_2_5(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # Redeem
        tx = token_contract_1.functions.redeemFrom(
            issuer_address, ZERO_ADDRESS, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_6>
    # Single Token
    # Single event logs
    # - ApplyForTransfer
    def test_normal_2_6(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # ApplyForTransfer
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_private_key_1,
            [issuer_address, "test"],
        )
        tx = token_contract_1.functions.applyForTransfer(
            user_address_1, 40, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_7>
    # Single Token
    # Single event logs
    # - CancelTransfer
    def test_normal_2_7(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # ApplyForTransfer
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_private_key_1,
            [issuer_address, "test"],
        )
        tx = token_contract_1.functions.applyForTransfer(
            user_address_1, 40, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40

        # CancelTransfer
        tx = token_contract_1.functions.cancelTransfer(0, "").build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_8>
    # Single Token
    # Single event logs
    # - ApproveTransfer
    def test_normal_2_8(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
        token_3.token_address = "test1"
        token_3.issuer_address = issuer_address
        token_3.abi = "abi"
        token_3.tx_hash = "tx_hash"
        token_3.token_status = 0
        db.add(token_3)

        db.commit()

        # ApplyForTransfer
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_private_key_1,
            [issuer_address, "test"],
        )
        tx = token_contract_1.functions.applyForTransfer(
            user_address_1, 40, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 40

        # ApproveTransfer
        tx = token_contract_1.functions.approveTransfer(0, "").build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 2
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_1>
    # Single Token
    # Single event logs
    # - IbetExchange: NewOrder
    def test_normal_2_9_1(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_exchange_contract,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_exchange_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
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
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # NewOrder(Sell)
        tx = ibet_exchange_contract.functions.createOrder(
            token_address_1, 30, 10000, False, issuer_address
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 30
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_2>
    # Single Token
    # Single event logs
    # - IbetExchange: CancelOrder
    def test_normal_2_9_2(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_exchange_contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # NewOrder(Sell) & CancelOrder
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [exchange_contract.address, 10],
        )
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            exchange_contract.address
        )
        IbetExchangeContractTestUtils.cancel_order(
            exchange_contract.address, user_address_1, user_pk_1, [latest_order_id]
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_3>
    # Single Token
    # Single event logs
    # - IbetExchange: ForceCancelOrder
    def test_normal_2_9_3(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_exchange_contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # NewOrder(Sell) & ForceCancelOrder
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [exchange_contract.address, 10],
        )
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            exchange_contract.address
        )
        IbetExchangeContractTestUtils.force_cancel_order(
            exchange_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_order_id],
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_4>
    # Single Token
    # Single event logs
    # - IbetExchange: Agree
    def test_normal_2_9_4(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_exchange_contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # NewOrder(Sell) & ExecuteOrder
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [exchange_contract.address, 10],
        )
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            exchange_contract.address
        )
        IbetExchangeContractTestUtils.execute_order(
            exchange_contract.address,
            user_address_2,
            user_pk_2,
            [latest_order_id, 10, True],
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 10
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_5>
    # Single Token
    # Single event logs
    # - IbetExchange: SettlementOK
    def test_normal_2_9_5(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_exchange_contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # NewOrder(Sell) & ExecuteOrder & ConfirmAgreement
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [exchange_contract.address, 10],
        )
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            exchange_contract.address
        )
        IbetExchangeContractTestUtils.execute_order(
            exchange_contract.address,
            user_address_2,
            user_pk_2,
            [latest_order_id, 10, True],
        )
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(
            exchange_contract.address, latest_order_id
        )
        IbetExchangeContractTestUtils.confirm_agreement(
            exchange_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_order_id, latest_agreement_id],
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_9_6>
    # Single Token
    # Single event logs
    # - IbetExchange: SettlementNG
    def test_normal_2_9_6(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_exchange_contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # NewOrder(Sell) & ExecuteOrder & CancelAgreement
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [exchange_contract.address, 10],
        )
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            exchange_contract.address
        )
        IbetExchangeContractTestUtils.execute_order(
            exchange_contract.address,
            user_address_2,
            user_pk_2,
            [latest_order_id, 10, True],
        )
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(
            exchange_contract.address, latest_order_id
        )
        IbetExchangeContractTestUtils.cancel_agreement(
            exchange_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_order_id, latest_agreement_id],
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 20
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 10
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_10_1>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowCreated
    def test_normal_2_10_1(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
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
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Before run(consume accumulated events)
        processor.sync_new_logs()
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0

        # EscrowCreated
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_contract_1.address, user_address_1, 30, issuer_address, "", ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 1
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 40 - 30
        assert _position.exchange_commitment == 30
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_10_2>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowCanceled
    def test_normal_2_10_2(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # CreateEscrow & CancelEscrow
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [escrow_contract.address, 30],
        )

        STEscrowContractUtils.create_escrow(
            escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 10, issuer_address, "", ""],
        )
        latest_escrow_id = STEscrowContractUtils.get_latest_escrow_id(
            escrow_contract.address
        )
        STEscrowContractUtils.cancel_escrow(
            escrow_contract.address, user_address_1, user_pk_1, [latest_escrow_id]
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_2_10_3>
    # Single Token
    # Single event logs
    # - IbetSecurityTokenEscrow: EscrowFinished
    def test_normal_2_10_3(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # CreateEscrow & CancelEscrow
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [escrow_contract.address, 30],
        )

        STEscrowContractUtils.create_escrow(
            escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 10, issuer_address, "", ""],
        )
        latest_escrow_id = STEscrowContractUtils.get_latest_escrow_id(
            escrow_contract.address
        )
        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_escrow_id],
        )
        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 20
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 10
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_3_1>
    # Single Token
    # Multi event logs
    # - Transfer(twice)
    def test_normal_3_1(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(bond token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        # Prepare data : Token(processing token)
        token_3 = Token()
        token_3.type = TokenType.IBET_SHARE.value
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
        tx = token_contract_1.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Transfer: 2nd
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_private_key_1,
            [issuer_address, "test"],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_private_key_2,
            [issuer_address, "test"],
        )
        tx = token_contract_1.functions.transfer(user_address_2, 10).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 40 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_3_2>
    # Single Token
    # Multi event logs
    # - Transfer(BulkTransfer)
    def test_normal_3_2(
        self, processor: Processor, db: Session, personal_info_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )
        user_4 = config_eth_account("user4")
        user_address_3 = user_4["address"]
        user_pk_3 = decode_keyfile_json(
            raw_keyfile_json=user_4["keyfile_json"], password="password".encode("utf-8")
        )
        user_5 = config_eth_account("user5")
        user_address_4 = user_5["address"]
        user_pk_4 = decode_keyfile_json(
            raw_keyfile_json=user_5["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(share token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_3,
            user_pk_3,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_4,
            user_pk_4,
            [issuer_address, ""],
        )

        # BulkTransfer: 1st
        address_list1 = [user_address_1, user_address_2, user_address_3]
        value_list1 = [10, 20, 30]
        tx = token_contract_1.functions.bulkTransfer(
            address_list1, value_list1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, _ = ContractUtils.send_transaction(tx, issuer_private_key)

        # BulkTransfer: 2nd
        address_list2 = [user_address_1, user_address_2, user_address_3, user_address_4]
        value_list2 = [1, 2, 3, 4]
        tx = token_contract_1.functions.bulkTransfer(
            address_list2, value_list2
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, _ = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 5
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 60 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 11
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 22
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_3)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_3
        assert _position.balance == 33
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_4)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_4
        assert _position.balance == 4
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_3_3>
    # Single Token
    # Multi event logs
    # - IbetExchange: NewOrder
    # - IbetExchange: CancelOrder
    def test_normal_3_3(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_exchange_contract,
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # NewOrder(Sell) & CancelOrder
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [exchange_contract.address, 10],
        )
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            exchange_contract.address
        )
        IbetExchangeContractTestUtils.cancel_order(
            exchange_contract.address, user_address_1, user_pk_1, [latest_order_id]
        )

        # NewOrder(Buy) & CancelOrder
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, 10, 100, True, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            exchange_contract.address
        )
        IbetExchangeContractTestUtils.cancel_order(
            exchange_contract.address, user_address_1, user_pk_1, [latest_order_id]
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_3_4>
    # Single Token
    # Multi event logs
    # - IbetSecurityTokenEscrow: EscrowCreated
    # - IbetSecurityTokenEscrow: EscrowCanceled
    def test_normal_3_4(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        # CreateEscrow & CancelEscrow
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [escrow_contract.address, 30],
        )
        for _ in range(3):
            STEscrowContractUtils.create_escrow(
                escrow_contract.address,
                user_address_1,
                user_pk_1,
                [token_contract.address, user_address_2, 10, issuer_address, "", ""],
            )
            latest_escrow_id = STEscrowContractUtils.get_latest_escrow_id(
                escrow_contract.address
            )
            STEscrowContractUtils.cancel_escrow(
                escrow_contract.address, user_address_1, user_pk_1, [latest_escrow_id]
            )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 3
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 0
        assert _position.exchange_balance == 30
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_4>
    # Multi Token
    def test_normal_4(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues share token.
        token_contract1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Issuer issues share token.
        token_contract2 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract2.abi
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        db.commit()

        # Before run(consume accumulated events)
        processor.sync_new_logs()

        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_1,
            user_pk_1,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            user_address_2,
            user_pk_2,
            [issuer_address, ""],
        )
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [issuer_address, ""],
        )

        STContractUtils.transfer(
            token_contract1.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 30],
        )
        STContractUtils.transfer(
            token_contract1.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10],
        )

        STContractUtils.transfer(
            token_contract2.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 40],
        )
        STContractUtils.transfer(
            token_contract2.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 60],
        )

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _position_list = db.query(IDXPosition).all()
        assert len(_position_list) == 6
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .filter(IDXPosition.token_address == token_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == issuer_address
        assert _position.balance == 100 - 30 - 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .filter(IDXPosition.token_address == token_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_1
        assert _position.balance == 30
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .filter(IDXPosition.token_address == token_address_1)
            .first()
        )
        assert _position.token_address == token_address_1
        assert _position.account_address == user_address_2
        assert _position.balance == 10
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == issuer_address)
            .filter(IDXPosition.token_address == token_address_2)
            .first()
        )
        assert _position.token_address == token_address_2
        assert _position.account_address == issuer_address
        assert _position.balance == 0
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_1)
            .filter(IDXPosition.token_address == token_address_2)
            .first()
        )
        assert _position.token_address == token_address_2
        assert _position.account_address == user_address_1
        assert _position.balance == 40
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _position = (
            db.query(IDXPosition)
            .filter(IDXPosition.account_address == user_address_2)
            .filter(IDXPosition.token_address == token_address_2)
            .first()
        )
        assert _position.token_address == token_address_2
        assert _position.account_address == user_address_2
        assert _position.balance == 60
        assert _position.exchange_balance == 0
        assert _position.exchange_commitment == 0
        assert _position.pending_transfer == 0
        _idx_position_share_block_number = db.query(IDXPositionShareBlockNumber).first()
        assert _idx_position_share_block_number.id == 1
        assert _idx_position_share_block_number.latest_block_number == block_number

    # <Normal_5>
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip process".
    @mock.patch("web3.eth.Eth.block_number", 100)
    def test_normal_5(
        self, processor: Processor, db: Session, caplog: pytest.LogCaptureFixture
    ):
        _idx_position_share_block_number = IDXPositionShareBlockNumber()
        _idx_position_share_block_number.id = 1
        _idx_position_share_block_number.latest_block_number = 1000
        db.add(_idx_position_share_block_number)
        db.commit()

        processor.sync_new_logs()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.DEBUG, "skip process")
        )

    # <Normal_6>
    # Newly tokens added
    def test_normal_6(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Issuer issues bond token.
        token_contract1 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        assert len(processor.token_list.keys()) == 1
        assert len(processor.exchange_address_list) == 1

        # Prepare additional token
        token_contract2 = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract2.abi
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        db.commit()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        # newly issued token is loaded properly
        assert len(processor.token_list.keys()) == 2
        assert len(processor.exchange_address_list) == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # If exception occurs out of Processor except-catch, batch outputs logs in mainloop.
    def test_error_1(
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

        # Prepare data : Token
        token_contract_1 = deploy_share_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Run mainloop once and fail with web3 utils error
        with patch(
            "batch.indexer_position_share.INDEXER_SYNC_INTERVAL", None
        ), patch.object(
            web3.eth, "contract", side_effect=ServiceUnavailableError()
        ), pytest.raises(
            TypeError
        ):
            main_func()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()

        # Run mainloop once and fail with sqlalchemy InvalidRequestError
        with patch(
            "batch.indexer_position_share.INDEXER_SYNC_INTERVAL", None
        ), patch.object(
            Session, "query", side_effect=InvalidRequestError()
        ), pytest.raises(
            TypeError
        ):
            main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()

        # Run mainloop once and fail with connection to blockchain
        with patch(
            "batch.indexer_position_share.INDEXER_SYNC_INTERVAL", None
        ), patch.object(
            ContractUtils, "call_function", side_effect=ConnectionError()
        ), pytest.raises(
            TypeError
        ):
            main_func()
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.ERROR,
                "An exception occurred during event synchronization",
            )
        )
        caplog.clear()
