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
from datetime import datetime
from unittest import mock
from unittest.mock import patch
from uuid import UUID

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import config
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber,
    Notification,
    NotificationType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from batch.indexer_transfer_approval import LOG, Processor, main
from config import CHAIN_ID, TX_GAS_LIMIT
from tests.account_config import config_eth_account
from tests.utils.contract_utils import (
    IbetSecurityTokenContractTestUtils as STContractUtils,
    IbetSecurityTokenEscrowContractTestUtils as STEscrowContractUtils,
    PersonalInfoContractTestUtils,
)

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


def deploy_bond_token_contract(
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
    token_address, _, _ = bond_contrat.create(arguments, address, private_key)
    bond_contrat.update(
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
    # No event log
    #   - Token not yet issued
    def test_normal_1_1(self, processor, db, personal_info_contract):
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

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # No event log
    #   - Issued tokens but no events have occurred.
    def test_normal_1_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_23_12
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Event log
    #   - ibetSecurityToken: ApplyForTransfer
    # -> One notification
    def test_normal_2_1(self, processor, db, personal_info_contract):
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
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_23_12
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

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

        # ApplyForTransfer
        tx = token_contract_1.functions.applyForTransfer(
            issuer_address, 30, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == config.ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block["timestamp"])
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_2_1>
    # Event log
    #   - ibetSecurityToken: CancelTransfer
    # Cancel from issuer
    #   -> No notification
    def test_normal_2_2_1(self, processor, db, personal_info_contract):
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
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer: issuer -> user
        tx_1 = token_contract_1.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx_1, issuer_private_key)

        # ApplyForTransfer from user
        tx_2 = token_contract_1.functions.applyForTransfer(
            issuer_address, 30, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_2 = ContractUtils.send_transaction(tx_2, user_private_key_1)

        # CancelTransfer from issuer
        tx_3 = token_contract_1.functions.cancelTransfer(0, "").build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_3 = ContractUtils.send_transaction(tx_3, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()
        db.commit()

        # Assertion
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])
        block_3 = web3.eth.get_block(tx_receipt_3["blockNumber"])

        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == config.ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block_2["timestamp"])
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert (
            _transfer_approval.cancellation_blocktimestamp
            == datetime.utcfromtimestamp(block_3["timestamp"])
        )
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_2_2>
    # Event log
    #   - ibetSecurityToken: CancelTransfer
    # Cancel from applicant
    #   -> One notification
    def test_normal_2_2_2(self, processor, db, personal_info_contract):
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
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer: issuer -> user
        tx_1 = token_contract_1.functions.transferFrom(
            issuer_address, user_address_1, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx_1, issuer_private_key)

        # ApplyForTransfer from user
        tx_2 = token_contract_1.functions.applyForTransfer(
            issuer_address, 30, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_2 = ContractUtils.send_transaction(tx_2, user_private_key_1)

        # CancelTransfer from applicant
        tx_3 = token_contract_1.functions.cancelTransfer(0, "").build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_3 = ContractUtils.send_transaction(tx_3, user_private_key_1)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()
        db.commit()

        # Assertion
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])
        block_3 = web3.eth.get_block(tx_receipt_3["blockNumber"])

        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == config.ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block_2["timestamp"])
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert (
            _transfer_approval.cancellation_blocktimestamp
            == datetime.utcfromtimestamp(block_3["timestamp"])
        )
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_3>
    # Event log
    #   - ibetSecurityToken: ApproveTransfer (from issuer)
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    def test_normal_2_3(self, processor, db, personal_info_contract):
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
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer: issuer -> user
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

        # ApplyForTransfer from user
        tx = token_contract_1.functions.applyForTransfer(
            issuer_address, 30, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block_1 = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # ApproveTransfer from issuer
        now = datetime.utcnow()
        tx = token_contract_1.functions.approveTransfer(
            0, str(now.timestamp())
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_2 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == config.ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block_1["timestamp"])
        )
        assert _transfer_approval.approval_datetime == now
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _transfer_approval.approval_blocktimestamp == datetime.utcfromtimestamp(
            block_2["timestamp"]
        )
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_4>
    # Event log
    #   - Exchange: ApplyForTransfer
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    def test_normal_2_4(
        self, processor, db, personal_info_contract, ibet_security_token_escrow_contract
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Deposit
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

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        now = datetime.utcnow()
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1,
            user_address_2,
            30,
            user_address_1,
            str(now.timestamp()),
            "",
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime == now
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block["timestamp"])
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_5>
    # Event log
    #   - Exchange: CancelTransfer
    # Cancel from applicant
    def test_normal_2_5(
        self, processor, db, personal_info_contract, ibet_security_token_escrow_contract
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_23_12
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Deposit
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

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1, user_address_2, 30, user_address_1, "", ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block_1 = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # CancelTransfer from applicant
        tx = ibet_security_token_escrow_contract.functions.cancelEscrow(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block_1["timestamp"])
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert (
            _transfer_approval.cancellation_blocktimestamp
            == datetime.utcfromtimestamp(block_2["timestamp"])
        )
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_6>
    # Single Token
    # Single event logs
    # - Exchange: EscrowFinished
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    def test_normal_2_6(
        self, processor, db, personal_info_contract, ibet_security_token_escrow_contract
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Deposit
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

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1, user_address_2, 30, user_address_1, "", ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block_1 = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # FinishTransfer
        tx = ibet_security_token_escrow_contract.functions.finishEscrow(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block_1["timestamp"])
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 3
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_7>
    # Event logs
    #   - Exchange: ApproveTransfer
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    def test_normal_2_7(
        self, processor, db, personal_info_contract, ibet_security_token_escrow_contract
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
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

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Deposit
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

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1, user_address_2, 30, user_address_1, "", ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # FinishTransfer
        tx = ibet_security_token_escrow_contract.functions.finishEscrow(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApproveTransfer
        tx = ibet_security_token_escrow_contract.functions.approveTransfer(
            1, ""
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        _, tx_receipt_2 = ContractUtils.send_transaction(tx, issuer_private_key)
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])

        # Run target process
        block_number = web3.eth.block_number
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.scalars(select(IDXTransferApproval)).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert (
            _transfer_approval.exchange_address
            == ibet_security_token_escrow_contract.address
        )
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert (
            _transfer_approval.application_blocktimestamp
            == datetime.utcfromtimestamp(block["timestamp"])
        )
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp == datetime.utcfromtimestamp(
            block_2["timestamp"]
        )
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = db.scalars(select(Notification)).all()
        assert len(_notification_list) == 3
        _notification = _notification_list[2]
        assert _notification.id == 3
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_type": token_1.type,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = db.scalars(
            select(IDXTransferApprovalBlockNumber).limit(1)
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_3>
    # If block number processed in batch is equal or greater than current block number,
    # batch will output a log "skip process".
    @mock.patch("web3.eth.Eth.block_number", 100)
    def test_normal_3(
        self, processor: Processor, db: Session, caplog: pytest.LogCaptureFixture
    ):
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.id = 1
        _idx_transfer_approval_block_number.latest_block_number = 1000
        db.add(_idx_transfer_approval_block_number)
        db.commit()

        processor.sync_new_logs()
        assert (
            caplog.record_tuples.count((LOG.name, logging.DEBUG, "skip process")) == 1
        )

    # <Normal_4>
    # If DB session fails in sinking phase each event, batch outputs a log "exception occurred".
    def test_normal_4(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_escrow_contract,
        caplog: pytest.LogCaptureFixture,
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

        # Prepare data : Token
        token_contract = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
        )
        token_address = token_contract.address
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.token_address = token_address
        token.issuer_address = issuer_address
        token.abi = token_contract.abi
        token.tx_hash = "tx_hash"
        token.version = TokenVersion.V_23_12
        db.add(token)
        db.commit()

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
        PersonalInfoContractTestUtils.register(
            personal_info_contract.address,
            issuer_address,
            issuer_private_key,
            [ibet_security_token_escrow_contract.address, ""],
        )

        STContractUtils.set_transfer_approve_required(
            token_contract.address, issuer_address, issuer_private_key, [True]
        )
        STContractUtils.apply_for_transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 10, "to user1#1"],
        )
        STContractUtils.apply_for_transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 20, "to user1#2"],
        )
        STContractUtils.apply_for_transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [user_address_2, 10, "to user2#1"],
        )

        STContractUtils.cancel_transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [0, "to user1#1"],
        )
        STContractUtils.approve_transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [1, "to user1#2"],
        )
        STContractUtils.approve_transfer(
            token_contract.address,
            issuer_address,
            issuer_private_key,
            [2, "to user2#1"],
        )

        STContractUtils.set_transfer_approve_required(
            token_contract.address, issuer_address, issuer_private_key, [False]
        )
        STContractUtils.transfer(
            token_contract.address,
            user_address_1,
            user_pk_1,
            [ibet_security_token_escrow_contract.address, 20],
        )
        STContractUtils.set_transfer_approve_required(
            token_contract.address, issuer_address, issuer_private_key, [True]
        )

        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 10, issuer_address, "", ""],
        )
        latest_security_escrow_id = STEscrowContractUtils.get_latest_escrow_id(
            ibet_security_token_escrow_contract.address
        )

        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_security_escrow_id],
        )
        STEscrowContractUtils.approve_transfer(
            ibet_security_token_escrow_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_security_escrow_id, ""],
        )

        with caplog.at_level(logging.ERROR, LOG.name), patch.object(
            Session, "add", side_effect=Exception()
        ):
            # Then execute processor.
            processor.sync_new_logs()

        # Error occurs in events with exception of Escrow.
        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.ERROR,
                    "An exception occurred during event synchronization",
                )
            )
            == 3
        )

    # <Normal_5>
    # Newly tokens added
    def test_normal_5(
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
        token_contract1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_23_12
        db.add(token_1)

        db.commit()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        assert len(processor.token_list.keys()) == 1
        assert len(processor.exchange_list) == 1

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
        token_2.version = TokenVersion.V_22_12
        db.add(token_2)

        db.commit()

        # Run target process
        processor.sync_new_logs()

        # Assertion
        # newly issued token is loaded properly
        assert len(processor.token_list.keys()) == 2
        assert len(processor.exchange_list) == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # If each error occurs, batch will output logs and continue next sync.
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
        token_contract = deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address = token_contract.address
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.token_address = token_address
        token.issuer_address = issuer_address
        token.abi = token_contract.abi
        token.tx_hash = "tx_hash"
        token.version = TokenVersion.V_23_12
        db.add(token)

        db.commit()

        # Run mainloop once and fail with web3 utils error
        with patch(
            "batch.indexer_transfer_approval.INDEXER_SYNC_INTERVAL", None
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

        # Run mainloop once and fail with sqlalchemy Error
        with patch(
            "batch.indexer_transfer_approval.INDEXER_SYNC_INTERVAL", None
        ), patch.object(
            Session, "commit", side_effect=SQLAlchemyError(code="dbapi")
        ), pytest.raises(
            TypeError
        ):
            main_func()
        assert "A database error has occurred: code=dbapi" in caplog.text
        caplog.clear()
