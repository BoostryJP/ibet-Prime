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
from eth_keyfile import decode_keyfile_json
import logging
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List
from unittest.mock import patch, MagicMock
import uuid

from app.model.db import Token, TokenType, TokenHoldersList, TokenHolderBatchStatus, TokenHolder
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract,
)
from app.model.schema import IbetStraightBondUpdate, IbetShareUpdate
from app.utils.web3_utils import Web3Wrapper
from app.utils.contract_utils import ContractUtils
from batch.indexer_token_holders import Processor, LOG, main
from config import ZERO_ADDRESS
from tests.account_config import config_eth_account
from tests.utils.contract_utils import (
    IbetSecurityTokenContractTestUtils as STContractUtils,
    IbetExchangeContractTestUtils,
    PersonalInfoContractTestUtils,
    IbetSecurityTokenEscrowContractTestUtils as STEscrowContractUtils,
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
def processor(db):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor()
    LOG.propagate = False
    LOG.setLevel(default_log_level)


def deploy_personal_info_contract(issuer_user):
    address = issuer_user["address"]
    keyfile = issuer_user["keyfile_json"]
    eoa_password = "password"

    private_key = decode_keyfile_json(raw_keyfile_json=keyfile, password=eoa_password.encode("utf-8"))
    contract_address, _, _ = ContractUtils.deploy_contract("PersonalInfo", [], address, private_key)
    return contract_address


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
        100000000,
        20,
        "token.redemption_date",
        30,
        "token.return_date",
        "token.return_amount",
        "token.purpose",
    ]

    token_address, _, _ = IbetStraightBondContract.create(arguments, address, private_key)
    IbetStraightBondContract.update(
        contract_address=token_address,
        data=IbetStraightBondUpdate(
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
        100000000,
        int(0.03 * 100),
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        30,
    ]

    token_address, _, _ = IbetShareContract.create(arguments, address, private_key)
    IbetShareContract.update(
        contract_address=token_address,
        data=IbetShareUpdate(
            transferable=True,
            personal_info_contract_address=personal_info_contract_address,
            tradable_exchange_contract_address=tradable_exchange_contract_address,
            transfer_approval_required=transfer_approval_required,
        ),
        tx_from=address,
        private_key=private_key,
    )

    return ContractUtils.get_contract("IbetShare", token_address)


def token_holders_list(token_address: str, block_number: str, list_id: str) -> TokenHoldersList:
    target_token_holders_list = TokenHoldersList()
    target_token_holders_list.list_id = list_id
    target_token_holders_list.token_address = token_address
    target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
    target_token_holders_list.block_number = block_number
    return target_token_holders_list


class TestProcessor:
    account_list = [
        {
            "address": config_eth_account("user1")["address"],
            "keyfile": config_eth_account("user1")["keyfile_json"],
        },
        {
            "address": config_eth_account("user2")["address"],
            "keyfile": config_eth_account("user2")["keyfile_json"],
        },
        {
            "address": config_eth_account("user3")["address"],
            "keyfile": config_eth_account("user3")["keyfile_json"],
        },
        {
            "address": config_eth_account("user4")["address"],
            "keyfile": config_eth_account("user4")["keyfile_json"],
        },
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # StraightBond
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    def test_normal_1(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_exchange_contract
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues bond token.
        token_contract = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 30000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [exchange_contract.address, 10000])
        # user1: 30000 user2: 10000

        STContractUtils.authorize_lock_address(token_contract.address, issuer_address, issuer_private_key, [user_address_1, True])
        STContractUtils.authorize_lock_address(token_contract.address, issuer_address, issuer_private_key, [user_address_2, True])

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 10000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_1, user_pk_1, [token_contract.address, 10000, 100, False, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.cancel_order(exchange_contract.address, user_address_1, user_pk_1, [latest_order_id])
        # user1: 30000 user2: 10000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 10000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_1, user_pk_1, [token_contract.address, 10000, 100, False, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.force_cancel_order(exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id])
        # user1: 30000 user2: 10000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 10000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_1, user_pk_1, [token_contract.address, 10000, 100, False, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.execute_order(exchange_contract.address, user_address_2, user_pk_2, [latest_order_id, 10000, True])
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(exchange_contract.address, latest_order_id)
        IbetExchangeContractTestUtils.confirm_agreement(
            exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id, latest_agreement_id]
        )
        # user1: 20000 user2: 20000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 4000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_2, user_pk_2, [token_contract.address, 4000, 100, True, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.execute_order(exchange_contract.address, user_address_1, user_pk_1, [latest_order_id, 4000, False])
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(exchange_contract.address, latest_order_id)
        IbetExchangeContractTestUtils.cancel_agreement(
            exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id, latest_agreement_id]
        )
        # user1: 20000 user2: 20000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 4000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_2, user_pk_2, [token_contract.address, 4000, 100, True, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.execute_order(exchange_contract.address, user_address_1, user_pk_1, [latest_order_id, 4000, False])
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(exchange_contract.address, latest_order_id)
        IbetExchangeContractTestUtils.confirm_agreement(
            exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id, latest_agreement_id]
        )
        # user1: 16000 user2: 24000

        STContractUtils.issue_from(token_contract.address, issuer_address, issuer_private_key, [issuer_address, ZERO_ADDRESS, 40000])
        STContractUtils.redeem_from(token_contract.address, issuer_address, issuer_private_key, [user_address_2, ZERO_ADDRESS, 10000])
        # user1: 16000 user2: 14000

        STContractUtils.issue_from(token_contract.address, issuer_address, issuer_private_key, [user_address_2, ZERO_ADDRESS, 30000])
        STContractUtils.redeem_from(token_contract.address, issuer_address, issuer_private_key, [issuer_address, ZERO_ADDRESS, 10000])
        # user1: 16000 user2: 44000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_1)
            .first()
        )
        user2_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_2)
            .first()
        )

        assert user1_record.hold_balance == 16000
        assert user2_record.hold_balance == 44000

        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list.id))) == 2

    # <Normal_2>
    # StraightBond
    # Events
    # - ApplyForTransfer
    # - CancelForTransfer
    # - ApproveTransfer
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    #   - ApproveTransfer
    def test_normal_2(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_escrow_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues bond token.
        token_contract = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [ibet_security_token_escrow_contract.address, 10000])
        # user1: 20000 user2: 0

        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [True])
        STContractUtils.apply_for_transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 10000, "to user1#1"])
        STContractUtils.apply_for_transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000, "to user2#1"])

        STContractUtils.cancel_transfer(token_contract.address, issuer_address, issuer_private_key, [0, "to user1#1"])
        STContractUtils.approve_transfer(token_contract.address, issuer_address, issuer_private_key, [1, "to user2#1"])
        # user1: 20000 user2: 10000

        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 7000, issuer_address, "", ""],
        )
        latest_security_escrow_id = STEscrowContractUtils.get_latest_escrow_id(ibet_security_token_escrow_contract.address)
        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id]
        )
        STEscrowContractUtils.approve_transfer(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id, ""]
        )
        # user1: 13000 user2: 17000

        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 2000, issuer_address, "", ""],
        )
        latest_security_escrow_id = STEscrowContractUtils.get_latest_escrow_id(ibet_security_token_escrow_contract.address)
        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id]
        )
        # user1: 13000 user2: 17000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [False])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_1)
            .first()
        )
        user2_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_2)
            .first()
        )

        assert user1_record.hold_balance == 13000
        assert user2_record.hold_balance == 17000

        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list.id))) == 2

    # <Normal_3>
    # StraightBond
    # Events
    # - ApplyForTransfer - pending
    # - Escrow - pending
    def test_normal_3(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_escrow_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues bond token.
        token_contract = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000])
        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [ibet_security_token_escrow_contract.address, 10000])
        # user1: 20000 user2: 10000

        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [True])
        STContractUtils.apply_for_transfer(token_contract.address, user_address_1, user_pk_1, [user_address_2, 10000, "to user2#1"])
        # user1: 20000 user2: 10000

        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 7000, issuer_address, "", ""],
        )
        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 3000, issuer_address, "", ""],
        )
        latest_security_escrow_id = STEscrowContractUtils.get_latest_escrow_id(ibet_security_token_escrow_contract.address)

        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id]
        )
        STEscrowContractUtils.approve_transfer(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id, ""]
        )
        # user1: 17000 user2: 13000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [False])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_1)
            .first()
        )
        user2_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_2)
            .first()
        )

        assert user1_record.hold_balance == 17000
        assert user2_record.hold_balance == 13000

        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list.id))) == 2

    # <Normal_4>
    # Share
    # Events
    # - Transfer
    # - Exchange
    #   - MakeOrder/CancelOrder/ForceCancelOrder/TakeOrder
    #   - CancelAgreement/ConfirmAgreement
    # - IssueFrom
    # - RedeemFrom
    def test_normal_4(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_exchange_contract
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

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

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [exchange_contract.address, 10000])
        # user1: 20000 user2: 10000

        STContractUtils.authorize_lock_address(token_contract.address, issuer_address, issuer_private_key, [user_address_1, True])
        STContractUtils.authorize_lock_address(token_contract.address, issuer_address, issuer_private_key, [user_address_2, True])

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 10000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_1, user_pk_1, [token_contract.address, 10000, 100, False, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.cancel_order(exchange_contract.address, user_address_1, user_pk_1, [latest_order_id])
        # user1: 20000 user2: 10000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 10000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_1, user_pk_1, [token_contract.address, 10000, 100, False, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.force_cancel_order(exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id])
        # user1: 20000 user2: 10000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 10000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_1, user_pk_1, [token_contract.address, 10000, 100, False, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.execute_order(exchange_contract.address, user_address_2, user_pk_2, [latest_order_id, 10000, True])
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(exchange_contract.address, latest_order_id)
        IbetExchangeContractTestUtils.confirm_agreement(
            exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id, latest_agreement_id]
        )
        # user1: 10000 user2: 20000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 4000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_2, user_pk_2, [token_contract.address, 4000, 100, True, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.execute_order(exchange_contract.address, user_address_1, user_pk_1, [latest_order_id, 4000, False])
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(exchange_contract.address, latest_order_id)
        IbetExchangeContractTestUtils.cancel_agreement(
            exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id, latest_agreement_id]
        )
        # user1: 10000 user2: 20000

        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [exchange_contract.address, 4000])
        IbetExchangeContractTestUtils.create_order(
            exchange_contract.address, user_address_2, user_pk_2, [token_contract.address, 4000, 100, True, issuer_address]
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(exchange_contract.address)
        IbetExchangeContractTestUtils.execute_order(exchange_contract.address, user_address_1, user_pk_1, [latest_order_id, 4000, False])
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(exchange_contract.address, latest_order_id)
        IbetExchangeContractTestUtils.confirm_agreement(
            exchange_contract.address, issuer_address, issuer_private_key, [latest_order_id, latest_agreement_id]
        )
        # user1: 6000 user2: 24000

        STContractUtils.issue_from(token_contract.address, issuer_address, issuer_private_key, [issuer_address, ZERO_ADDRESS, 40000])
        STContractUtils.redeem_from(token_contract.address, issuer_address, issuer_private_key, [user_address_2, ZERO_ADDRESS, 10000])
        # user1: 6000 user2: 14000

        STContractUtils.issue_from(token_contract.address, issuer_address, issuer_private_key, [user_address_2, ZERO_ADDRESS, 30000])
        STContractUtils.redeem_from(token_contract.address, issuer_address, issuer_private_key, [issuer_address, ZERO_ADDRESS, 10000])
        # user1: 6000 user2: 44000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_1)
            .first()
        )
        user2_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_2)
            .first()
        )

        assert user1_record.hold_balance == 6000
        assert user2_record.hold_balance == 44000

        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list.id))) == 2

    # <Normal_5>
    # Share
    # Events
    # - ApplyForTransfer
    # - CancelForTransfer
    # - ApproveTransfer
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    #   - ApproveTransfer
    def test_normal_5(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_escrow_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
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

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [ibet_security_token_escrow_contract.address, 10000])
        # user1: 20000 user2: 0

        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [True])
        STContractUtils.apply_for_transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 10000, "to user1#1"])
        STContractUtils.apply_for_transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000, "to user2#1"])

        STContractUtils.cancel_transfer(token_contract.address, issuer_address, issuer_private_key, [0, "to user1#1"])
        STContractUtils.approve_transfer(token_contract.address, issuer_address, issuer_private_key, [1, "to user2#1"])
        # user1: 20000 user2: 10000

        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 7000, issuer_address, "", ""],
        )
        latest_security_escrow_id = STEscrowContractUtils.get_latest_escrow_id(ibet_security_token_escrow_contract.address)
        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id]
        )
        STEscrowContractUtils.approve_transfer(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id, ""]
        )
        # user1: 13000 user2: 17000

        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 2000, issuer_address, "", ""],
        )
        latest_security_escrow_id = STEscrowContractUtils.get_latest_escrow_id(ibet_security_token_escrow_contract.address)
        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id]
        )
        # user1: 13000 user2: 17000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [False])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_1)
            .first()
        )
        user2_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_2)
            .first()
        )

        assert user1_record.hold_balance == 13000
        assert user2_record.hold_balance == 17000

        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list.id))) == 2

    # <Normal_6>
    # Share
    # Events
    # - ApplyForTransfer - pending
    # - Escrow - pending
    def test_normal_6(
        self,
        processor,
        db,
        personal_info_contract,
        ibet_security_token_escrow_contract
    ):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
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

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000])
        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [ibet_security_token_escrow_contract.address, 10000])
        # user1: 20000 user2: 10000

        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [True])
        STContractUtils.apply_for_transfer(token_contract.address, user_address_1, user_pk_1, [user_address_2, 10000, "to user2#1"])
        # user1: 20000 user2: 10000

        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 7000, issuer_address, "", ""],
        )
        # user1: 20000 user2: 10000
        STEscrowContractUtils.create_escrow(
            ibet_security_token_escrow_contract.address,
            user_address_1,
            user_pk_1,
            [token_contract.address, user_address_2, 3000, issuer_address, "", ""],
        )
        latest_security_escrow_id = STEscrowContractUtils.get_latest_escrow_id(ibet_security_token_escrow_contract.address)

        STEscrowContractUtils.finish_escrow(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id]
        )
        STEscrowContractUtils.approve_transfer(
            ibet_security_token_escrow_contract.address, issuer_address, issuer_private_key, [latest_security_escrow_id, ""]
        )
        # user1: 17000 user2: 13000

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        # Issuer transfers issued token to user1 again to proceed block_number on chain.
        STContractUtils.set_transfer_approve_required(token_contract.address, issuer_address, issuer_private_key, [False])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])

        # Then execute processor.
        processor.collect()

        user1_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_1)
            .first()
        )
        user2_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list.id)
            .filter(TokenHolder.account_address == user_address_2)
            .first()
        )

        assert user1_record.hold_balance == 17000
        assert user2_record.hold_balance == 13000

        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list.id))) == 2

    # <Normal_7>
    # StraightBond
    # Jobs are queued and pending jobs are to be processed one by one.
    def test_normal_7(
        self,
        processor: Processor,
        db,
        personal_info_contract,
        ibet_exchange_contract,
        caplog: pytest.LogCaptureFixture
    ):
        exchange_contract = ibet_exchange_contract
        processor.collect()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, "There are no pending collect batch"))

        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues bond token.
        token_contract = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list1 = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list1)
        db.commit()

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [exchange_contract.address, 10000])

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list2 = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list2)
        db.commit()

        processor.collect()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"Token holder list({_token_holders_list1.list_id}) status changes to be done."))
        assert 2 == caplog.record_tuples.count((LOG.name, logging.INFO, f"<INDEXER-Token-Holders> Collect job has been completed"))

    # <Normal_8>
    # StraightBond
    # Indexer uses checkpoint if there is stored data.
    def test_normal_8(
        self,
        processor: Processor,
        db,
        personal_info_contract,
        ibet_exchange_contract,
        caplog: pytest.LogCaptureFixture
    ):
        exchange_contract = ibet_exchange_contract

        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues bond token.
        token_contract = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [exchange_contract.address, 10000])

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list1 = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list1)
        db.commit()
        processor.collect()

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_2, 10000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [exchange_contract.address, 10000])

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list2 = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list2)
        db.commit()
        processor.collect()

        user1_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list2.id)
            .filter(TokenHolder.account_address == user_address_1)
            .first()
        )
        user2_record: TokenHolder = (
            db.query(TokenHolder)
            .filter(TokenHolder.holder_list_id == _token_holders_list2.id)
            .filter(TokenHolder.account_address == user_address_2)
            .first()
        )

        assert user1_record.hold_balance == 40000
        assert user2_record.hold_balance == 20000

        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list1.id))) == 2
        assert len(list(db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list2.id))) == 2

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # There is no target token holders list id with batch_status PENDING.
    def test_error_1(
        self,
        processor: Processor,
        db,
        personal_info_contract,
        ibet_exchange_contract,
        caplog: pytest.LogCaptureFixture
    ):

        processor.collect()

        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, "There are no pending collect batch"))
        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"<INDEXER-Token-Holders> Collect job has been completed"))

    # <Error_2>
    # There is target token holders list id with batch_status PENDING.
    # And target token is not contained in "TokenList" contract.
    def test_error_2(
        self,
        processor: Processor,
        db,
        personal_info_contract,
        ibet_exchange_contract,
        caplog: pytest.LogCaptureFixture
    ):
        # Insert collection definition with token address Zero
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = ZERO_ADDRESS
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
        target_token_holders_list.block_number = 1000
        db.add(target_token_holders_list)
        db.commit()

        # Debug message should be shown that points out token contract must be listed.
        processor.collect()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, "Token contract must be listed to TokenList contract."))
        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"Token holder list({target_token_holders_list.list_id}) status changes to be failed."))
        assert 1 == caplog.record_tuples.count((LOG.name, logging.INFO, f"<INDEXER-Token-Holders> Collect job has been completed"))

        # Batch status of token holders list expects to be "ERROR"
        error_record_num = len(list(db.query(TokenHoldersList).filter(TokenHoldersList.batch_status == TokenHolderBatchStatus.FAILED.value)))
        assert error_record_num == 1

    # <Error_3>
    # Failed to get Logs from blockchain.
    def test_error_3(
        self,
        processor: Processor,
        db,
        personal_info_contract,
        ibet_exchange_contract,
        caplog: pytest.LogCaptureFixture
    ):
        exchange_contract = ibet_exchange_contract
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues bond token.
        token_contract = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=exchange_contract.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [exchange_contract.address, 10000])

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        mock_lib = MagicMock()
        with patch.object(Processor, "_Processor__process_all", return_value=mock_lib) as __sync_all_mock:
            # Then execute processor.
            __sync_all_mock.return_value = None
            processor.collect()
            _records: List[TokenHolder] = db.query(TokenHolder).filter(TokenHolder.holder_list_id == _token_holders_list.id).all()
            assert len(_records) == 0

    # <Error_4>
    # If DB session fails in phase sinking events, batch logs exception message.
    def test_error_4(self, main_func, db: Session, ibet_security_token_escrow_contract, personal_info_contract, caplog: pytest.LogCaptureFixture):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8"))
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_pk_1 = decode_keyfile_json(raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8"))
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_pk_2 = decode_keyfile_json(raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8"))

        # Issuer issues share token.
        token_contract = deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            tradable_exchange_contract_address=ibet_security_token_escrow_contract.address,
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

        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_1, user_pk_1, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, user_address_2, user_pk_2, [issuer_address, ""])
        PersonalInfoContractTestUtils.register(personal_info_contract.address, issuer_address, issuer_private_key, [issuer_address, ""])

        STContractUtils.transfer(token_contract.address, issuer_address, issuer_private_key, [user_address_1, 20000])
        STContractUtils.transfer(token_contract.address, user_address_1, user_pk_1, [ibet_security_token_escrow_contract.address, 10000])

        # Insert collection record with above token and current block number
        list_id = str(uuid.uuid4())
        block_number = web3.eth.blockNumber
        _token_holders_list = token_holders_list(token_contract.address, block_number, list_id)
        db.add(_token_holders_list)
        db.commit()

        with patch("batch.indexer_token_holders.INDEXER_SYNC_INTERVAL", None),\
            patch.object(Processor, "collect", return_value=True),\
                pytest.raises(TypeError):
            main_func()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, "Processed"))
        caplog.clear()

        with patch("batch.indexer_token_holders.INDEXER_SYNC_INTERVAL", None),\
            patch.object(Session, "close", side_effect=SQLAlchemyError()), \
                pytest.raises(TypeError):
            main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()