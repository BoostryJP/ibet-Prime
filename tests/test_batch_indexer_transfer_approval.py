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
from uuid import UUID

from eth_keyfile import decode_keyfile_json

from config import (
    CHAIN_ID,
    TX_GAS_LIMIT
)
from app.model.db import (
    Token,
    TokenType,
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber,
    Notification,
    NotificationType,
    AdditionalTokenInfo
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
from batch.indexer_transfer_approval import Processor
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
        db.add(token_1)

        db.commit()

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # No event log
    #   - Issued tokens but no events have occurred.
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
                                                      personal_info_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_1_1>
    # Event log
    #   - ibetSecurityToken: ApplyForTransfer
    # Token with automatic transfer approval
    #   - not exists AdditionalTokenInfo
    def test_normal_2_1_1(self, processor, db, personal_info_contract):
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
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # ApplyForTransfer
        tx = token_contract_1.functions.applyForTransfer(
            issuer_address,
            30,
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_1_2>
    # Event log
    #   - ibetSecurityToken: ApplyForTransfer
    # Token with automatic transfer approval
    #   - AdditionalTokenInfo.is_manual_transfer_approval = false
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_1_2(self, processor, db, personal_info_contract):
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
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : AdditionalTokenInfo
        additional_token_info_1 = AdditionalTokenInfo()
        additional_token_info_1.token_address = token_address_1
        additional_token_info_1.is_manual_transfer_approval = False
        db.add(additional_token_info_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # ApplyForTransfer
        now = datetime.utcnow()
        tx = token_contract_1.functions.applyForTransfer(
            issuer_address,
            30,
            str(now.timestamp())
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime == now
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_1_3>
    # Event log
    #   - ibetSecurityToken: ApplyForTransfer
    # Token with manual transfer approval
    def test_normal_2_1_3(self, processor, db, personal_info_contract):
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
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : AdditionalTokenInfo
        additional_token_info_1 = AdditionalTokenInfo()
        additional_token_info_1.token_address = token_address_1
        additional_token_info_1.is_manual_transfer_approval = True
        db.add(additional_token_info_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # ApplyForTransfer
        tx = token_contract_1.functions.applyForTransfer(
            issuer_address,
            30,
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_address": token_address_1,
            "id": 1
        }

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
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
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer: issuer -> user
        tx_1 = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx_1, issuer_private_key)

        # ApplyForTransfer from user
        tx_2 = token_contract_1.functions.applyForTransfer(
            issuer_address,
            30,
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_2 = ContractUtils.send_transaction(tx_2, user_private_key_1)

        # CancelTransfer from issuer
        tx_3 = token_contract_1.functions.cancelTransfer(
            0,
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_3 = ContractUtils.send_transaction(tx_3, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()
        db.commit()

        # Assertion
        block = web3.eth.get_block(tx_receipt_2["blockNumber"])

        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
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
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer: issuer -> user
        tx_1 = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx_1, issuer_private_key)

        # ApplyForTransfer from user
        tx_2 = token_contract_1.functions.applyForTransfer(
            issuer_address,
            30,
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_2 = ContractUtils.send_transaction(tx_2, user_private_key_1)

        # CancelTransfer from applicant
        tx_3 = token_contract_1.functions.cancelTransfer(
            0,
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_3 = ContractUtils.send_transaction(tx_3, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()
        db.commit()

        # Assertion
        block = web3.eth.get_block(tx_receipt_2["blockNumber"])

        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_address": token_address_1,
            "id": 1
        }

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_3>
    # Event log
    #   - ibetSecurityToken: ApproveTransfer (from issuer)
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_3(self, processor, db, personal_info_contract):
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
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Transfer: issuer -> user
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # ApplyForTransfer from user
        tx = token_contract_1.functions.applyForTransfer(
            issuer_address,
            30,
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block_1 = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # ApproveTransfer from issuer
        now = datetime.utcnow()
        tx = token_contract_1.functions.approveTransfer(
            0,
            str(now.timestamp())
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_2 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block_1["timestamp"])
        assert _transfer_approval.approval_datetime == now
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _transfer_approval.approval_blocktimestamp == datetime.utcfromtimestamp(block_2["timestamp"])
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_address": token_address_1,
            "id": 1
        }

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_4>
    # Event log
    #   - Exchange: ApplyForTransfer
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_4(self, processor, db, personal_info_contract, ibet_security_token_escrow_contract):
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        # Prepare data : AdditionalTokenInfo
        additional_token_info_1 = AdditionalTokenInfo()
        additional_token_info_1.token_address = token_address_1
        additional_token_info_1.is_manual_transfer_approval = True
        db.add(additional_token_info_1)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        now = datetime.utcnow()
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1,
            user_address_2,
            30,
            user_address_1,
            str(now.timestamp()),
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ibet_security_token_escrow_contract.address
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime == now
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_address": token_address_1,
            "id": 1
        }

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_5>
    # Event log
    #   - Exchange: CancelTransfer
    # Cancel from applicant
    def test_normal_2_5(self, processor, db, personal_info_contract, ibet_security_token_escrow_contract):
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1,
            user_address_2,
            30,
            user_address_1,
            "",
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # CancelTransfer from applicant
        tx = ibet_security_token_escrow_contract.functions.cancelEscrow(1).buildTransaction({
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
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ibet_security_token_escrow_contract.address
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_address": token_address_1,
            "id": 1
        }

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_6>
    # Single Token
    # Single event logs
    # - Exchange: EscrowFinished
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_6(self, processor, db, personal_info_contract, ibet_security_token_escrow_contract):
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1,
            user_address_2,
            30,
            user_address_1,
            "",
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block_1 = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # FinishTransfer
        tx = ibet_security_token_escrow_contract.functions.finishEscrow(1).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ibet_security_token_escrow_contract.address
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block_1["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 3
        assert _notification.metainfo == {
            "token_address": token_address_1,
            "id": 1
        }

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_7>
    # Event logs
    #   - Exchange: ApproveTransfer
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_7(self, processor, db, personal_info_contract, ibet_security_token_escrow_contract):
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

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address,
                                                      tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
                                                      transfer_approval_required=True)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        db.add(_idx_transfer_approval_block_number)

        db.commit()

        # Deposit
        tx = token_contract_1.functions.transferFrom(
            issuer_address,
            user_address_1,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        tx = token_contract_1.functions.transfer(
            ibet_security_token_escrow_contract.address,
            40
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # ApplyForTransfer
        tx = ibet_security_token_escrow_contract.functions.createEscrow(
            token_address_1,
            user_address_2,
            30,
            user_address_1,
            "",
            ""
        ).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_1 = ContractUtils.send_transaction(tx, user_private_key_1)
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])

        # FinishTransfer
        tx = ibet_security_token_escrow_contract.functions.finishEscrow(1).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        _, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])

        # ApproveTransfer
        tx = ibet_security_token_escrow_contract.functions.approveTransfer(
            1,
            ""
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
        _transfer_approval_list = db.query(IDXTransferApproval).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ibet_security_token_escrow_contract.address
        assert _transfer_approval.application_id == 1
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == user_address_2
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.utcfromtimestamp(block["timestamp"])
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp == datetime.utcfromtimestamp(block_2["timestamp"])
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = db.query(Notification).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_address": token_address_1,
            "id": 1
        }

        _idx_transfer_approval_block_number = db.query(IDXTransferApprovalBlockNumber).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number
