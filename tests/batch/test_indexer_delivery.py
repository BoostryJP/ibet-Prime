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

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
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
from app.model.db import (
    Account,
    DeliveryStatus,
    IDXDelivery,
    IDXDeliveryBlockNumber,
    Notification,
    NotificationType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper, Web3Wrapper
from batch.indexer_delivery import LOG, Processor, main
from config import CHAIN_ID, TX_GAS_LIMIT
from tests.account_config import config_eth_account
from tests.contract_utils import (
    IbetSecurityTokenContractTestUtils as STContractUtils,
    IbetSecurityTokenEscrowContractTestUtils as STEscrowContractUtils,
    PersonalInfoContractTestUtils,
)

web3 = AsyncWeb3Wrapper()


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
    # No event log
    #   - Token not yet issued
    @pytest.mark.asyncio
    async def test_normal_1_1(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = user_1["rsa_private_key"]
        account.rsa_public_key = user_1["rsa_public_key"]
        account.rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token(processing token)
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = "test1"
        token_1.issuer_address = issuer_address
        token_1.abi = "abi"
        token_1.tx_hash = "tx_hash"
        token_1.token_status = 0
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        db.commit()

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 0

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert _idx_delivery_block_number is None

    # <Normal_1_2>
    # No event log
    #   - Issued tokens but no exchange address is set.
    @pytest.mark.asyncio
    async def test_normal_1_2(
        self, processor, db, personal_info_contract, caplog: pytest.LogCaptureFixture
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = user_1["rsa_private_key"]
        account.rsa_public_key = user_1["rsa_public_key"]
        account.rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=None,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        db.commit()

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 0

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert _idx_delivery_block_number is None

    # <Normal_1_3>
    # No event log
    #   - Issued tokens but the exchange contract other than DVP contract is set.
    @pytest.mark.asyncio
    async def test_normal_1_3(
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

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = user_1["rsa_private_key"]
        account.rsa_public_key = user_1["rsa_public_key"]
        account.rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        db.commit()

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 0

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert _idx_delivery_block_number.latest_block_number == block_number
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_escrow_contract.address
        )

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_escrow_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_1>
    # Event log
    #   - Exchange: CreateDelivery (from issuer)
    @pytest.mark.asyncio
    async def test_normal_2_1(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_address_1, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        block = await web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _delivery.create_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is True
        assert _delivery.status == DeliveryStatus.DELIVERY_CREATED

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_2_1>
    # Event log
    #   - Exchange: CancelDelivery (from issuer)
    @pytest.mark.asyncio
    async def test_normal_2_2_1(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_address_1, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # CancelDelivery
        tx = ibet_security_token_dvp_contract.functions.cancelDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        block = await web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _delivery.create_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.create_transaction_hash == tx_hash_1
        block = await web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _delivery.cancel_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.cancel_transaction_hash == tx_hash_2
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_CANCELED

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_2_2>
    # Event log
    #   - Exchange: CancelDelivery (from buyer)
    @pytest.mark.asyncio
    async def test_normal_2_2_2(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_address_1, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # CancelDelivery
        tx = ibet_security_token_dvp_contract.functions.cancelDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        block = await web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _delivery.create_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.create_transaction_hash == tx_hash_1
        block = await web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _delivery.cancel_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.cancel_transaction_hash == tx_hash_2
        assert _delivery.confirm_blocktimestamp is None
        assert _delivery.confirm_transaction_hash is None
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is False
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_CANCELED

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_3>
    # Event log
    #   - Exchange: ConfirmDelivery (from buyer)
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_3(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_address_1, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # ConfirmDelivery
        tx = ibet_security_token_dvp_contract.functions.confirmDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        block = await web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _delivery.create_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        block = await web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _delivery.confirm_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is True
        assert _delivery.valid is True
        assert _delivery.status == DeliveryStatus.DELIVERY_CONFIRMED

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_4>
    # Event log
    #   - Exchange: FinishDelivery (from agent)
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    @pytest.mark.asyncio
    async def test_normal_2_4(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_address_1, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # ConfirmDelivery
        tx = ibet_security_token_dvp_contract.functions.confirmDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)

        # FinishDelivery
        tx = ibet_security_token_dvp_contract.functions.finishDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": agent_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_3, tx_receipt_3 = ContractUtils.send_transaction(tx, agent_private_key)

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        block = await web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _delivery.create_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        block = await web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _delivery.confirm_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.confirm_transaction_hash == tx_hash_2
        block = await web3.eth.get_block(tx_receipt_3["blockNumber"])
        assert _delivery.finish_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.finish_transaction_hash == tx_hash_3
        assert _delivery.abort_blocktimestamp is None
        assert _delivery.abort_transaction_hash is None
        assert _delivery.confirmed is True
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_FINISHED

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_2_5>
    # Event log
    #   - Exchange: AbortDelivery (from agent)
    @pytest.mark.asyncio
    async def test_normal_2_5(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        # Transfer
        tx = token_contract_1.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_address_1, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # ConfirmDelivery
        tx = ibet_security_token_dvp_contract.functions.confirmDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)

        # FinishDelivery
        tx = ibet_security_token_dvp_contract.functions.abortDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": agent_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_3, tx_receipt_3 = ContractUtils.send_transaction(tx, agent_private_key)

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_1
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        block = await web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _delivery.create_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        block = await web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _delivery.confirm_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        block = await web3.eth.get_block(tx_receipt_3["blockNumber"])
        assert _delivery.abort_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.abort_transaction_hash == tx_hash_3
        assert _delivery.confirmed is True
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_ABORTED

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).limit(1)
        ).first()
        assert (
            _idx_delivery_block_number.exchange_address
            == ibet_security_token_dvp_contract.address
        )
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_3>
    # Multi Exchange
    @pytest.mark.asyncio
    async def test_normal_3(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_escrow_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        agent_address = user_3["address"]
        agent_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = user_1["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token
        token_contract_2 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_2 = token_contract_2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract_2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 0
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        # Transfer
        tx = token_contract_2.functions.transferFrom(
            issuer_address, ibet_security_token_dvp_contract.address, 40
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # CreateDelivery
        tx = ibet_security_token_dvp_contract.functions.createDelivery(
            token_address_2, user_address_1, 30, agent_address, "." * 1000
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_1, tx_receipt_1 = ContractUtils.send_transaction(tx, issuer_private_key)

        # ConfirmDelivery
        tx = ibet_security_token_dvp_contract.functions.confirmDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_2, tx_receipt_2 = ContractUtils.send_transaction(tx, user_private_key_1)

        # FinishDelivery
        tx = ibet_security_token_dvp_contract.functions.abortDelivery(
            1
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": agent_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        tx_hash_3, tx_receipt_3 = ContractUtils.send_transaction(tx, agent_private_key)

        # Run target process
        block_number = await web3.eth.block_number
        await processor.sync_new_logs()

        # Assertion
        _delivery_list = db.scalars(select(IDXDelivery)).all()
        assert len(_delivery_list) == 1
        _delivery = _delivery_list[0]
        assert _delivery.id == 1
        assert _delivery.exchange_address == ibet_security_token_dvp_contract.address
        assert _delivery.token_address == token_address_2
        assert _delivery.buyer_address == user_address_1
        assert _delivery.seller_address == issuer_address
        assert _delivery.amount == 30
        assert _delivery.agent_address == agent_address
        assert _delivery.data == "." * 1000
        block = await web3.eth.get_block(tx_receipt_1["blockNumber"])
        assert _delivery.create_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.create_transaction_hash == tx_hash_1
        assert _delivery.cancel_blocktimestamp is None
        assert _delivery.cancel_transaction_hash is None
        block = await web3.eth.get_block(tx_receipt_2["blockNumber"])
        assert _delivery.confirm_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.confirm_transaction_hash == tx_hash_2
        assert _delivery.finish_blocktimestamp is None
        assert _delivery.finish_transaction_hash is None
        block = await web3.eth.get_block(tx_receipt_3["blockNumber"])
        assert _delivery.abort_blocktimestamp == datetime.fromtimestamp(
            block["timestamp"], UTC
        ).replace(tzinfo=None)
        assert _delivery.abort_transaction_hash == tx_hash_3
        assert _delivery.confirmed is True
        assert _delivery.valid is False
        assert _delivery.status == DeliveryStatus.DELIVERY_ABORTED

        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).where(
                IDXDeliveryBlockNumber.exchange_address
                == ibet_security_token_escrow_contract.address
            )
        ).first()
        assert _idx_delivery_block_number.latest_block_number == block_number
        _idx_delivery_block_number = db.scalars(
            select(IDXDeliveryBlockNumber).where(
                IDXDeliveryBlockNumber.exchange_address
                == ibet_security_token_dvp_contract.address
            )
        ).first()
        assert _idx_delivery_block_number.latest_block_number == block_number

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_escrow_contract.address}",
                )
            )
            == 1
        )

        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.INFO,
                    f"Syncing from=1, to={block_number}, exchange={ibet_security_token_dvp_contract.address}",
                )
            )
            == 1
        )

    # <Normal_4>
    # If block number processed in batch is equal or greater than current block number,
    # batch will output a log "skip process".
    @mock.patch("web3.eth.Eth.block_number", 100)
    @pytest.mark.asyncio
    async def test_normal_4(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        caplog: pytest.LogCaptureFixture,
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
        db.add(account)

        # Prepare data : Token
        token_contract_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        # Prepare data : Token(processing token)
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = "test1"
        token_2.issuer_address = issuer_address
        token_2.abi = "abi"
        token_2.tx_hash = "tx_hash"
        token_2.token_status = 0
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        # Prepare data : BlockNumber
        _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = 100
        _idx_delivery_block_number.exchange_address = (
            ibet_security_token_dvp_contract.address
        )
        db.add(_idx_delivery_block_number)

        db.commit()

        await processor.sync_new_logs()
        assert (
            caplog.record_tuples.count((LOG.name, logging.DEBUG, "skip process")) == 1
        )

    # <Normal_5>
    # Newly tokens added
    @pytest.mark.asyncio
    async def test_normal_6(
        self,
        processor: Processor,
        db: Session,
        personal_info_contract,
        ibet_security_token_dvp_contract,
        ibet_security_token_escrow_contract,
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

        # Issuer issues bond token.
        token_contract1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_24_09
        db.add(token_1)

        db.commit()

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        assert len(processor.token_list) == 1
        assert len(processor.exchange_list) == 1

        # Prepare additional token
        token_contract2 = await deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_dvp_contract.address,
            transfer_approval_required=False,
        )
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address
        token_2.abi = token_contract2.abi
        token_2.tx_hash = "tx_hash"
        token_2.version = TokenVersion.V_24_09
        db.add(token_2)

        db.commit()

        # Run target process
        await processor.sync_new_logs()

        # Assertion
        # newly issued token is loaded properly
        assert len(processor.token_list) == 2
        assert len(processor.exchange_list) == 2

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
        token_contract = await deploy_bond_token_contract(
            issuer_address, issuer_private_key, personal_info_contract.address
        )
        token_address = token_contract.address
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.token_address = token_address
        token.issuer_address = issuer_address
        token.abi = token_contract.abi
        token.tx_hash = "tx_hash"
        token.version = TokenVersion.V_24_09
        db.add(token)

        db.commit()

        # Run mainloop once and fail with web3 utils error
        with patch("batch.indexer_delivery.INDEXER_SYNC_INTERVAL", None), patch.object(
            AsyncWeb3Wrapper().eth, "contract", side_effect=ServiceUnavailableError()
        ), pytest.raises(TypeError):
            await main_func()
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.WARNING, "An external service was unavailable")
        )
        caplog.clear()

        # Run mainloop once and fail with sqlalchemy Error
        with patch("batch.indexer_delivery.INDEXER_SYNC_INTERVAL", None), patch.object(
            AsyncSession, "commit", side_effect=SQLAlchemyError(code="dbapi")
        ), pytest.raises(TypeError):
            await main_func()
        assert "A database error has occurred: code=dbapi" in caplog.text
        caplog.clear()
