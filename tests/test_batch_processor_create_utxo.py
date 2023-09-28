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
import json
import time
from unittest import mock
from unittest.mock import ANY, MagicMock, call

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    AdditionalIssueParams as IbetShareAdditionalIssueParams,
    ForceUnlockPrams as IbetShareForceUnlockParams,
    LockParams as IbetShareLockParams,
    RedeemParams as IbetShareRedeemParams,
    TransferParams as IbetShareTransferParams,
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    AdditionalIssueParams as IbetStraightBondAdditionalIssueParams,
    LockParams as IbetStraightBondLockParams,
    RedeemParams as IbetStraightBondRedeemParams,
    TransferParams as IbetStraightBondTransferParams,
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import UTXO, Token, TokenType, UTXOBlockNumber
from app.utils.contract_utils import ContractUtils
from batch.processor_create_utxo import Processor
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import config_eth_account
from tests.utils.contract_utils import (
    IbetExchangeContractTestUtils,
    IbetSecurityTokenContractTestUtils as STContractUtils,
    PersonalInfoContractTestUtils,
)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def processor(db):
    return Processor()


def deploy_bond_token_contract(
    address,
    private_key,
    personal_info_contract_address=None,
    tradable_exchange_contract_address=None,
):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        "token.redemption_date",
        30,
        "token.return_date",
        "token.return_amount",
        "token.purpose",
    ]
    bond_contrat = IbetStraightBondContract()
    contract_address, _, _ = bond_contrat.create(arguments, address, private_key)
    bond_contrat.update(
        IbetStraightBondUpdateParams(
            transferable=True,
            personal_info_contract_address=personal_info_contract_address,
            tradable_exchange_contract_address=tradable_exchange_contract_address,
        ),
        address,
        private_key,
    )

    return contract_address


def deploy_share_token_contract(address, private_key):
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
    contract_address, _, _ = share_contract.create(arguments, address, private_key)
    share_contract.update(
        IbetShareUpdateParams(transferable=True), address, private_key
    )

    return contract_address


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Execute Batch Run 1st: No Event
    # Execute Batch Run 2nd: Executed Transfer Event
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_1(self, mock_func, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        token_address_2 = deploy_share_token_contract(
            issuer_address, issuer_private_key
        )
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE.value
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        db.commit()

        # Execute batch(Run 1st)
        # Assume: Skip processing
        latest_block = web3.eth.block_number
        processor.process()

        # assertion
        _utox_list = db.scalars(select(UTXO)).all()
        assert len(_utox_list) == 0
        _utox_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utox_block_number.latest_block_number == latest_block

        # Execute Transfer Event
        # Share:issuer -> user1
        _transfer_1 = IbetShareTransferParams(
            from_address=issuer_address, to_address=user_address_1, amount=70
        )
        IbetShareContract(token_address_2).transfer(
            _transfer_1, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond:issuer -> user1
        _transfer_2 = IbetStraightBondTransferParams(
            from_address=issuer_address, to_address=user_address_1, amount=40
        )
        IbetStraightBondContract(token_address_1).transfer(
            _transfer_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond:issuer -> user2
        _transfer_3 = IbetStraightBondTransferParams(
            from_address=issuer_address, to_address=user_address_2, amount=20
        )
        IbetStraightBondContract(token_address_1).transfer(
            _transfer_3, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Share:user1 -> user2
        _transfer_4 = IbetShareTransferParams(
            from_address=user_address_1, to_address=user_address_2, amount=10
        )
        IbetShareContract(token_address_2).transfer(
            _transfer_4, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Execute batch(Run 2nd)
        # Assume: Create UTXO
        processor.process()

        # assertion
        db.rollback()
        _utox_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
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
        _utox_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utox_block_number.latest_block_number == _utox_list[3].block_number

        mock_func.assert_has_calls(
            [
                call(token_address=token_address_1, db=ANY),
                call(token_address=token_address_2, db=ANY),
            ]
        )

    # <Normal_2>
    # Over max block lot
    @mock.patch("batch.processor_create_utxo.create_ledger")
    @mock.patch("batch.processor_create_utxo.CREATE_UTXO_BLOCK_LOT_MAX_SIZE", 5)
    def test_normal_2(self, mock_func, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        latest_block_number = web3.eth.block_number
        _utxo_block_number = UTXOBlockNumber()
        _utxo_block_number.latest_block_number = latest_block_number
        db.add(_utxo_block_number)

        db.commit()

        # Transfer event 6 times
        _transfer = IbetStraightBondTransferParams(
            from_address=issuer_address, to_address=user_address_1, amount=60
        )
        IbetStraightBondContract(token_address_1).transfer(
            _transfer, issuer_address, issuer_private_key
        )
        time.sleep(1)
        _transfer = IbetStraightBondTransferParams(
            from_address=user_address_1, to_address=user_address_2, amount=10
        )
        IbetStraightBondContract(token_address_1).transfer(
            _transfer, issuer_address, issuer_private_key
        )
        time.sleep(1)
        IbetStraightBondContract(token_address_1).transfer(
            _transfer, issuer_address, issuer_private_key
        )
        time.sleep(1)
        IbetStraightBondContract(token_address_1).transfer(
            _transfer, issuer_address, issuer_private_key
        )
        time.sleep(1)
        IbetStraightBondContract(token_address_1).transfer(
            _transfer, issuer_address, issuer_private_key
        )
        time.sleep(1)
        IbetStraightBondContract(token_address_1).transfer(
            _transfer, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Execute batch
        processor.process()

        # Assertion
        _utxo_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utxo_block_number.latest_block_number == latest_block_number + 5
        _utox_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utox_list) == 5
        _utox = _utox_list[0]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 20
        assert _utox.block_number == latest_block_number + 1
        _utox = _utox_list[1]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10
        assert _utox.block_number == latest_block_number + 2
        _utox = _utox_list[2]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10
        assert _utox.block_number == latest_block_number + 3
        _utox = _utox_list[3]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10
        assert _utox.block_number == latest_block_number + 4
        _utox = _utox_list[4]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10
        assert _utox.block_number == latest_block_number + 5

    # <Normal_3>
    # bulk transfer(same transaction-hash)
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_3(self, mock_func, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_1_private_key = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_2_private_key = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        db.commit()

        token_contract = ContractUtils.get_contract("IbetStraightBond", token_address_1)

        # set personal info
        personal_contract_address, _, _ = ContractUtils.deploy_contract(
            "PersonalInfo", [], issuer_address, issuer_private_key
        )
        IbetStraightBondContract(token_address_1).update(
            IbetStraightBondUpdateParams(
                personal_info_contract_address=personal_contract_address
            ),
            issuer_address,
            issuer_private_key,
        )
        personal_contract = ContractUtils.get_contract(
            "PersonalInfo", personal_contract_address
        )
        tx = personal_contract.functions.register(issuer_address, "").build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_1,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_1_private_key)
        tx = personal_contract.functions.register(issuer_address, "").build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user_address_2,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, user_2_private_key)

        # bulk transfer
        tx = token_contract.functions.bulkTransfer(
            [user_address_1, user_address_2, user_address_1], [10, 20, 40]
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Execute batch
        processor.process()

        # Assertion
        _utox_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utox_list) == 2
        _utox = _utox_list[0]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 50
        _utox = _utox_list[1]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 20

    # <Normal_4>
    # to Exchange transfer only
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_4(self, mock_func, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        db.commit()

        # set exchange address
        storage_address, _, _ = ContractUtils.deploy_contract(
            "EscrowStorage", [], issuer_address, issuer_private_key
        )
        exchange_address, _, _ = ContractUtils.deploy_contract(
            "IbetEscrow", [storage_address], issuer_address, issuer_private_key
        )
        storage_contract = ContractUtils.get_contract("EscrowStorage", storage_address)
        tx = storage_contract.functions.upgradeVersion(
            exchange_address
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": issuer_address,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(tx, issuer_private_key)
        update_data = IbetStraightBondUpdateParams(
            tradable_exchange_contract_address=exchange_address
        )
        IbetStraightBondContract(token_address_1).update(
            update_data, issuer_address, issuer_private_key
        )

        # Execute Transfer Event
        # Bond:issuer -> Exchange
        _transfer_1 = IbetStraightBondTransferParams(
            from_address=issuer_address, to_address=exchange_address, amount=100
        )
        IbetStraightBondContract(token_address_1).transfer(
            _transfer_1, issuer_address, issuer_private_key
        )

        # Execute batch
        # Assume: Not Create UTXO and Ledger
        processor.process()

        # assertion
        _utox_list = db.scalars(select(UTXO)).all()
        assert len(_utox_list) == 0
        mock_func.assert_not_called()

    # <Normal_5>
    # Holder Changed
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_5(
        self, mock_func, processor, db, personal_info_contract, ibet_exchange_contract
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

        # prepare data
        token_address_1 = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
            tradable_exchange_contract_address=ibet_exchange_contract.address,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

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
            token_address_1, issuer_address, issuer_private_key, [user_address_1, 10]
        )
        STContractUtils.transfer(
            token_address_1, issuer_address, issuer_private_key, [user_address_2, 10]
        )
        STContractUtils.transfer(
            token_address_1,
            user_address_1,
            user_pk_1,
            [ibet_exchange_contract.address, 10],
        )
        STContractUtils.transfer(
            token_address_1,
            issuer_address,
            issuer_private_key,
            [ibet_exchange_contract.address, 10],
        )

        IbetExchangeContractTestUtils.create_order(
            ibet_exchange_contract.address,
            user_address_1,
            user_pk_1,
            [token_address_1, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            ibet_exchange_contract.address
        )
        IbetExchangeContractTestUtils.execute_order(
            ibet_exchange_contract.address,
            user_address_2,
            user_pk_2,
            [latest_order_id, 10, True],
        )
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(
            ibet_exchange_contract.address, latest_order_id
        )
        IbetExchangeContractTestUtils.confirm_agreement(
            ibet_exchange_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_order_id, latest_agreement_id],
        )

        # prepare other data
        other_token_address = deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
            personal_info_contract_address=personal_info_contract.address,
            tradable_exchange_contract_address=ibet_exchange_contract.address,
        )
        STContractUtils.transfer(
            other_token_address,
            issuer_address,
            issuer_private_key,
            [user_address_1, 10],
        )
        STContractUtils.transfer(
            other_token_address,
            user_address_1,
            user_pk_1,
            [ibet_exchange_contract.address, 10],
        )
        STContractUtils.transfer(
            other_token_address,
            issuer_address,
            issuer_private_key,
            [ibet_exchange_contract.address, 10],
        )

        IbetExchangeContractTestUtils.create_order(
            ibet_exchange_contract.address,
            user_address_1,
            user_pk_1,
            [other_token_address, 10, 100, False, issuer_address],
        )
        latest_order_id = IbetExchangeContractTestUtils.get_latest_order_id(
            ibet_exchange_contract.address
        )
        IbetExchangeContractTestUtils.execute_order(
            ibet_exchange_contract.address,
            user_address_2,
            user_pk_2,
            [latest_order_id, 10, True],
        )
        latest_agreement_id = IbetExchangeContractTestUtils.get_latest_agreementid(
            ibet_exchange_contract.address, latest_order_id
        )
        IbetExchangeContractTestUtils.confirm_agreement(
            ibet_exchange_contract.address,
            issuer_address,
            issuer_private_key,
            [latest_order_id, latest_agreement_id],
        )

        db.commit()

        # Execute batch
        # Assume: Not Create UTXO and Ledger
        processor.process()

        # assertion
        db.rollback()
        _utox_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()

        assert len(_utox_list) == 3
        _utox = _utox_list[0]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 0
        assert _utox.block_number < _utox_list[1].block_number
        assert _utox.block_timestamp <= _utox_list[1].block_timestamp
        _utox = _utox_list[1]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10
        assert _utox.block_number < _utox_list[2].block_number
        assert _utox.block_timestamp <= _utox_list[2].block_timestamp
        _utox = _utox_list[2]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10

        _utox_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utox_block_number.latest_block_number >= _utox_list[1].block_number

        mock_func.assert_has_calls([call(token_address=token_address_1, db=ANY)])

    # <Normal_6>
    # Additional Issue
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_6(self, mock_func, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        token_address_2 = deploy_share_token_contract(
            issuer_address, issuer_private_key
        )
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE.value
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        db.commit()

        # Execute Issue Event
        # Share
        _additional_issue_1 = IbetShareAdditionalIssueParams(
            account_address=user_address_1, amount=70
        )
        IbetShareContract(token_address_1).additional_issue(
            _additional_issue_1, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond
        _additional_issue_2 = IbetStraightBondAdditionalIssueParams(
            account_address=user_address_2, amount=80
        )
        IbetStraightBondContract(token_address_2).additional_issue(
            _additional_issue_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Execute batch
        latest_block = web3.eth.block_number
        processor.process()

        # assertion
        _utox_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utox_list) == 2
        _utox = _utox_list[0]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 70
        _utox = _utox_list[1]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_2
        assert _utox.amount == 80

        _utox_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utox_block_number.latest_block_number == latest_block

    # <Normal_7>
    # Redeem
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_7(self, mock_func, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        token_address_2 = deploy_share_token_contract(
            issuer_address, issuer_private_key
        )
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE.value
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        db.commit()

        # Execute Issue Event
        # Share
        _additional_issue_1 = IbetShareAdditionalIssueParams(
            account_address=user_address_1, amount=10
        )
        IbetShareContract(token_address_1).additional_issue(
            _additional_issue_1, issuer_address, issuer_private_key
        )
        time.sleep(1)
        _additional_issue_2 = IbetShareAdditionalIssueParams(
            account_address=user_address_1, amount=20
        )
        IbetShareContract(token_address_1).additional_issue(
            _additional_issue_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond
        _additional_issue_3 = IbetStraightBondAdditionalIssueParams(
            account_address=user_address_2, amount=30
        )
        IbetStraightBondContract(token_address_2).additional_issue(
            _additional_issue_3, issuer_address, issuer_private_key
        )
        time.sleep(1)
        _additional_issue_4 = IbetStraightBondAdditionalIssueParams(
            account_address=user_address_2, amount=40
        )
        IbetStraightBondContract(token_address_2).additional_issue(
            _additional_issue_4, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Before execute
        processor.process()
        _utox_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utox_list) == 4
        _utox = _utox_list[0]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10
        _utox = _utox_list[1]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 20
        _utox = _utox_list[2]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_2
        assert _utox.amount == 30
        _utox = _utox_list[3]
        assert _utox.transaction_hash is not None
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_2
        assert _utox.amount == 40

        # Execute Redeem Event
        # Share
        _redeem_1 = IbetShareRedeemParams(account_address=user_address_1, amount=20)
        IbetShareContract(token_address_1).redeem(
            _redeem_1, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond
        _redeem_2 = IbetStraightBondRedeemParams(
            account_address=user_address_2, amount=40
        )
        IbetStraightBondContract(token_address_2).redeem(
            _redeem_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Execute batch
        latest_block = web3.eth.block_number
        processor.process()

        # assertion
        db.rollback()
        _utox_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utox_list) == 4
        _utox = _utox_list[0]
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 0
        _utox = _utox_list[1]
        assert _utox.account_address == user_address_1
        assert _utox.token_address == token_address_1
        assert _utox.amount == 10
        _utox = _utox_list[2]
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_2
        assert _utox.amount == 0
        _utox = _utox_list[3]
        assert _utox.account_address == user_address_2
        assert _utox.token_address == token_address_2
        assert _utox.amount == 30

        _utox_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utox_block_number.latest_block_number == latest_block

    # <Normal_8_1>
    # Unlock(account_address!=recipient_address)
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_8_1(self, mock_func, processor, db):
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
        lock_address = user_4["address"]

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        token_address_2 = deploy_share_token_contract(
            issuer_address, issuer_private_key
        )
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE.value
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        db.commit()

        # Execute Issue Event
        # Share
        _additional_issue_1 = IbetShareAdditionalIssueParams(
            account_address=user_address_1, amount=10
        )
        IbetShareContract(token_address_1).additional_issue(
            _additional_issue_1, issuer_address, issuer_private_key
        )
        time.sleep(1)
        _additional_issue_2 = IbetShareAdditionalIssueParams(
            account_address=user_address_1, amount=20
        )
        IbetShareContract(token_address_1).additional_issue(
            _additional_issue_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond
        _additional_issue_3 = IbetStraightBondAdditionalIssueParams(
            account_address=user_address_2, amount=30
        )
        IbetStraightBondContract(token_address_2).additional_issue(
            _additional_issue_3, issuer_address, issuer_private_key
        )
        time.sleep(1)
        _additional_issue_4 = IbetStraightBondAdditionalIssueParams(
            account_address=user_address_2, amount=40
        )
        IbetStraightBondContract(token_address_2).additional_issue(
            _additional_issue_4, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Before execute
        processor.process()
        _utxo_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        # Execute Lock/Unlock Event
        # Share
        _lock_1 = IbetShareLockParams(
            lock_address=lock_address, value=5, data=json.dumps({})
        )
        IbetShareContract(token_address_1).lock(_lock_1, user_address_1, user_pk_1)
        time.sleep(1)

        _unlock_1 = IbetShareForceUnlockParams(
            lock_address=lock_address,
            account_address=user_address_1,
            recipient_address=issuer_address,
            value=5,
            data=json.dumps({}),
        )
        IbetShareContract(token_address_1).force_unlock(
            _unlock_1, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond
        _lock_2 = IbetStraightBondLockParams(
            lock_address=lock_address, value=10, data=json.dumps({})
        )
        IbetStraightBondContract(token_address_2).lock(
            _lock_2, user_address_2, user_pk_2
        )
        time.sleep(1)

        _unlock_2 = IbetShareForceUnlockParams(
            lock_address=lock_address,
            account_address=user_address_2,
            recipient_address=issuer_address,
            value=10,
            data=json.dumps({}),
        )
        IbetStraightBondContract(token_address_2).force_unlock(
            _unlock_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Execute batch
        latest_block = web3.eth.block_number
        processor.process()

        # assertion
        db.rollback()
        _utxo_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utxo_list) == 6
        _utxo = _utxo_list[0]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 5
        _utxo = _utxo_list[1]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 20
        _utxo = _utxo_list[3]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40
        _utxo = _utxo_list[4]
        assert _utxo.account_address == issuer_address
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 5
        _utxo = _utxo_list[5]
        assert _utxo.account_address == issuer_address
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 10

        _utxo_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utxo_block_number.latest_block_number == latest_block

    # <Normal_8_2>
    # Unlock(account_address==recipient_address)
    @mock.patch("batch.processor_create_utxo.create_ledger")
    def test_normal_8_2(self, mock_func, processor, db):
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
        lock_address = user_4["address"]

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        token_address_2 = deploy_share_token_contract(
            issuer_address, issuer_private_key
        )
        _token_2 = Token()
        _token_2.type = TokenType.IBET_SHARE.value
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        db.commit()

        # Execute Issue Event
        # Share
        _additional_issue_1 = IbetShareAdditionalIssueParams(
            account_address=user_address_1, amount=10
        )
        IbetShareContract(token_address_1).additional_issue(
            _additional_issue_1, issuer_address, issuer_private_key
        )
        time.sleep(1)
        _additional_issue_2 = IbetShareAdditionalIssueParams(
            account_address=user_address_1, amount=20
        )
        IbetShareContract(token_address_1).additional_issue(
            _additional_issue_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond
        _additional_issue_3 = IbetStraightBondAdditionalIssueParams(
            account_address=user_address_2, amount=30
        )
        IbetStraightBondContract(token_address_2).additional_issue(
            _additional_issue_3, issuer_address, issuer_private_key
        )
        time.sleep(1)
        _additional_issue_4 = IbetStraightBondAdditionalIssueParams(
            account_address=user_address_2, amount=40
        )
        IbetStraightBondContract(token_address_2).additional_issue(
            _additional_issue_4, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Before execute
        processor.process()
        _utxo_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.transaction_hash is not None
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        # Execute Lock/Unlock Event
        # Share
        _lock_1 = IbetShareLockParams(
            lock_address=lock_address, value=5, data=json.dumps({})
        )
        IbetShareContract(token_address_1).lock(_lock_1, user_address_1, user_pk_1)
        time.sleep(1)

        _unlock_1 = IbetShareForceUnlockParams(
            lock_address=lock_address,
            account_address=user_address_1,
            recipient_address=user_address_1,
            value=5,
            data=json.dumps({}),
        )
        IbetShareContract(token_address_1).force_unlock(
            _unlock_1, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Bond
        _lock_2 = IbetStraightBondLockParams(
            lock_address=lock_address, value=10, data=json.dumps({})
        )
        IbetStraightBondContract(token_address_2).lock(
            _lock_2, user_address_2, user_pk_2
        )
        time.sleep(1)

        _unlock_2 = IbetShareForceUnlockParams(
            lock_address=lock_address,
            account_address=user_address_2,
            recipient_address=user_address_2,
            value=10,
            data=json.dumps({}),
        )
        IbetStraightBondContract(token_address_2).force_unlock(
            _unlock_2, issuer_address, issuer_private_key
        )
        time.sleep(1)

        # Execute batch
        latest_block = web3.eth.block_number
        processor.process()

        # assertion
        db.rollback()
        _utxo_list = db.scalars(select(UTXO).order_by(UTXO.created)).all()
        assert len(_utxo_list) == 4
        _utxo = _utxo_list[0]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 10
        _utxo = _utxo_list[1]
        assert _utxo.account_address == user_address_1
        assert _utxo.token_address == token_address_1
        assert _utxo.amount == 20
        _utxo = _utxo_list[2]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 30
        _utxo = _utxo_list[3]
        assert _utxo.account_address == user_address_2
        assert _utxo.token_address == token_address_2
        assert _utxo.amount == 40

        _utxo_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utxo_block_number.latest_block_number == latest_block

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Web3 Error
    def test_error_1(self, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # prepare data
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        db.commit()

        # Execute batch
        latest_block = web3.eth.block_number
        with mock.patch(
            "web3.eth.Eth.uninstall_filter",
            MagicMock(side_effect=Exception("mock test")),
        ) as web3_mock:
            processor.process()

        _utox_list = db.scalars(select(UTXO)).all()
        assert len(_utox_list) == 0
        _utox_block_number = db.scalars(select(UTXOBlockNumber).limit(1)).first()
        assert _utox_block_number.latest_block_number == latest_block
