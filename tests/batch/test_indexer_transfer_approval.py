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
from datetime import UTC, datetime
from unittest import mock
from unittest.mock import patch
from uuid import UUID

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    Account,
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber,
    Notification,
    NotificationType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch.indexer_transfer_approval import LOG, Processor, main
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER, ZERO_ADDRESS
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


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
def processor(async_db, caplog: pytest.LogCaptureFixture):
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
    # No event log
    #   - Token not yet issued
    @pytest.mark.asyncio
    async def test_normal_1_1(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Token(processing token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = {}
        token_1.tx_hash = "tx_hash"
        token_1.token_status = 0
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_1_2>
    # No event log
    #   - Issued tokens but no events have occurred.
    @pytest.mark.asyncio
    async def test_normal_1_2(self, processor, async_db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 0

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 0

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Event log
    #   - ibetSecurityToken: ApplyForTransfer
    # -> One notification
    @pytest.mark.asyncio
    async def test_normal_2_1(self, processor, async_db, personal_info_contract):
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

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        block = web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_2_1>
    # Event log
    #   - ibetSecurityToken: CancelTransfer
    # Cancel from issuer
    #   -> No notification
    @pytest.mark.asyncio
    async def test_normal_2_2_1(self, processor, async_db, personal_info_contract):
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

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        await processor.sync_new_logs()
        await async_db.commit()
        async_db.expire_all()

        # Assertion
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])
        block_3 = web3.eth.get_block(tx_receipt_3["blockNumber"])

        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block_2["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp == datetime.fromtimestamp(
            block_3["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_2_2>
    # Event log
    #   - ibetSecurityToken: CancelTransfer
    # Cancel from applicant
    #   -> One notification
    @pytest.mark.asyncio
    async def test_normal_2_2_2(self, processor, async_db, personal_info_contract):
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

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        await processor.sync_new_logs()
        await async_db.commit()
        async_db.expire_all()

        # Assertion
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])
        block_3 = web3.eth.get_block(tx_receipt_3["blockNumber"])

        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1
        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block_2["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp == datetime.fromtimestamp(
            block_3["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_3>
    # Event log
    #   - ibetSecurityToken: ApproveTransfer (from issuer)
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_3(self, processor, async_db, personal_info_contract):
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

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        now = datetime.now(UTC).replace(tzinfo=None)
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
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_address_1
        assert _transfer_approval.exchange_address == ZERO_ADDRESS
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == user_address_1
        assert _transfer_approval.to_address == issuer_address
        assert _transfer_approval.amount == 30
        assert _transfer_approval.application_datetime is None
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block_1["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime == now
        block_2 = web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _transfer_approval.approval_blocktimestamp == datetime.fromtimestamp(
            block_2["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_4>
    # Event log
    #   - Exchange: ApplyForTransfer
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_4(
        self,
        processor,
        async_db,
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
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        now = datetime.now(UTC).replace(tzinfo=None)
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
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
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
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 1
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_5>
    # Event log
    #   - Exchange: CancelTransfer
    # Cancel from applicant
    @pytest.mark.asyncio
    async def test_normal_2_5(
        self,
        processor,
        async_db,
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
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = {}
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
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
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block_1["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp == datetime.fromtimestamp(
            block_2["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_6>
    # Single Token
    # Single event logs
    # - Exchange: EscrowFinished
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_6(
        self,
        processor,
        async_db,
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
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.block_number
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
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
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block_1["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 2
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 3
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_2_7>
    # Event logs
    #   - Exchange: ApproveTransfer
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_7(
        self,
        processor,
        async_db,
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
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=True,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BlockNumber
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.latest_block_number = 0
        async_db.add(_idx_transfer_approval_block_number)

        await async_db.commit()

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
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        _transfer_approval_list = (
            await async_db.scalars(select(IDXTransferApproval))
        ).all()
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
        assert _transfer_approval.application_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp == datetime.fromtimestamp(
            block_2["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _transfer_approval.cancellation_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _notification_list = (await async_db.scalars(select(Notification))).all()
        assert len(_notification_list) == 3
        _notification = _notification_list[2]
        assert _notification.id == 3
        assert UUID(_notification.notice_id).version == 4
        assert _notification.issuer_address == issuer_address
        assert _notification.priority == 0
        assert _notification.type == NotificationType.TRANSFER_APPROVAL_INFO
        assert _notification.code == 2
        assert _notification.metainfo == {
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "token_address": token_address_1,
            "id": 1,
        }

        _idx_transfer_approval_block_number = (
            await async_db.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        assert _idx_transfer_approval_block_number.id == 1
        assert _idx_transfer_approval_block_number.latest_block_number == block_number

    # <Normal_3>
    # If block number processed in batch is equal or greater than current block number,
    # batch will output a log "skip process".
    @mock.patch("web3.eth.Eth.block_number", 100)
    @pytest.mark.asyncio
    async def test_normal_3(
        self, processor: Processor, async_db, caplog: pytest.LogCaptureFixture
    ):
        _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()
        _idx_transfer_approval_block_number.id = 1
        _idx_transfer_approval_block_number.latest_block_number = 1000
        async_db.add(_idx_transfer_approval_block_number)
        await async_db.commit()

        await processor.sync_new_logs()
        async_db.expire_all()
        assert (
            caplog.record_tuples.count((LOG.name, logging.DEBUG, "skip process")) == 1
        )

    # <Normal_4>
    # Newly tokens added
    @pytest.mark.asyncio
    async def test_normal_4(
        self,
        processor: Processor,
        async_db,
        personal_info_contract,
        ibet_security_token_escrow_contract,
    ):
        escrow_contract = ibet_security_token_escrow_contract
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
        async_db.add(account)

        # Issuer issues bond token.
        token_contract1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        await async_db.commit()

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        assert len(processor.token_list.keys()) == 1
        assert len(processor.exchange_list) == 1

        # Prepare additional token
        token_contract2 = await deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)

        await async_db.commit()

        # Run target process
        await processor.sync_new_logs()
        async_db.expire_all()

        # Assertion
        # newly issued token is loaded properly
        assert len(processor.token_list.keys()) == 2
        assert len(processor.exchange_list) == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # If each error occurs, batch will output logs and continue next sync.
    @pytest.mark.asyncio
    async def test_error_1(
        self,
        main_func,
        async_db,
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
        async_db.add(account)

        # Prepare data : Token
        token_contract = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address = token_contract.address
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = token_address
        token.issuer_address = issuer_address
        token.abi = token_contract.abi
        token.tx_hash = "tx_hash"
        token.version = TokenVersion.V_25_06
        async_db.add(token)

        await async_db.commit()

        # Run mainloop once and fail with web3 utils error
        with (
            patch("batch.indexer_transfer_approval.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                AsyncWeb3Wrapper().eth,
                "contract",
                side_effect=ServiceUnavailableError(),
            ),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()

        # Run mainloop once and fail with sqlalchemy Error
        with (
            patch("batch.indexer_transfer_approval.INDEXER_SYNC_INTERVAL", None),
            patch.object(
                AsyncSession, "commit", side_effect=SQLAlchemyError(code="dbapi")
            ),
            pytest.raises(TypeError),
        ):
            await main_func()
        assert "A database error has occurred: code=dbapi" in caplog.text
        caplog.clear()
