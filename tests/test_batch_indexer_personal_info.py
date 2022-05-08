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
import base64
import json

from eth_keyfile import decode_keyfile_json
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session
from app.exceptions import ServiceUnavailableError

from config import (
    CHAIN_ID,
    TX_GAS_LIMIT
)
from app.model.db import (
    Token,
    TokenType,
    IDXPersonalInfo,
    IDXPersonalInfoBlockNumber,
    Account
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
from app.utils.e2ee_utils import E2EEUtils
from batch.indexer_personal_info import Processor, LOG, main
from tests.account_config import config_eth_account

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


def encrypt_personal_info(personal_info, rsa_public_key, passphrase):
    rsa_key = RSA.importKey(rsa_public_key, passphrase=passphrase)
    cipher = PKCS1_OAEP.new(rsa_key)
    ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(personal_info).encode('utf-8')))
    return ciphertext


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
        db.add(token_1)

        db.commit()

        # Run target process
        block_number = web3.eth.blockNumber
        processor.process()

        # Assertion
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 0
        _idx_personal_info_block_number = db.query(IDXPersonalInfoBlockNumber).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

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
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
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
        _idx_personal_info_block_number = IDXPersonalInfoBlockNumber()
        _idx_personal_info_block_number.latest_block_number = 0
        db.add(_idx_personal_info_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.blockNumber
        processor.process()

        # Assertion
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 0
        _idx_personal_info_block_number = db.query(IDXPersonalInfoBlockNumber).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Single Token
    # Single event logs
    # - Register
    def test_normal_2_1(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
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

        db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
        }
        ciphertext = encrypt_personal_info(personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.register(issuer_address, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.process()

        # Assertion
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.id == 1
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_1
        _idx_personal_info_block_number = db.query(IDXPersonalInfoBlockNumber).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_2_2>
    # Single Token
    # Single event logs
    # - Modify
    def test_normal_2_2(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
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

        db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
        }
        ciphertext = encrypt_personal_info(personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.register(issuer_address, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Before run(consume accumulated events)
        processor.process()
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.id == 1
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_1

        # Modify
        personal_info_2 = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2"
        }
        ciphertext = encrypt_personal_info(personal_info_2, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.modify(user_address_1, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.process()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.id == 1
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_2
        _idx_personal_info_block_number = db.query(IDXPersonalInfoBlockNumber).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_3>
    # Single Token
    # Multi event logs
    # - Modify(twice)
    def test_normal_3(self, processor, db, personal_info_contract):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
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

        db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
        }
        ciphertext = encrypt_personal_info(personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.register(issuer_address, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Before run(consume accumulated events)
        processor.process()
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.id == 1
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_1

        # Modify
        personal_info_2 = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2"
        }
        ciphertext = encrypt_personal_info(personal_info_2, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.modify(user_address_1, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.process()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.id == 1
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_2
        _idx_personal_info_block_number = db.query(IDXPersonalInfoBlockNumber).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

        # Modify
        personal_info_3 = {
            "key_manager": "key_manager_test3",
            "name": "name_test3",
            "postal_code": "postal_code_test3",
            "address": "address_test3",
            "email": "email_test3",
            "birth": "birth_test3"
        }
        ciphertext = encrypt_personal_info(personal_info_3, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.modify(user_address_1, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.process()

        # If we query in one session before and after update some record in another session,
        # SQLAlchemy will return same result twice. So Expiring all persistent instances within unittest db session.
        db.expire_all()

        # Assertion
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 1
        _personal_info = _personal_info_list[0]
        assert _personal_info.id == 1
        assert _personal_info.account_address == user_address_1
        assert _personal_info.issuer_address == issuer_address
        assert _personal_info.personal_info == personal_info_3
        _idx_personal_info_block_number = db.query(IDXPersonalInfoBlockNumber).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_4>
    # Multi Token
    def test_normal_4(self, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        issuer_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        issuer_rsa_private_key_1 = user_1["rsa_private_key"]
        issuer_rsa_public_key_1 = user_1["rsa_public_key"]
        issuer_rsa_passphrase_1 = "password"

        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]
        issuer_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )
        issuer_rsa_private_key_2 = user_2["rsa_private_key"]
        issuer_rsa_passphrase_2 = "password"
        issuer_rsa_public_key_2 = user_2["rsa_public_key"]

        # Prepare data : Account(Issuer1)
        account = Account()
        account.issuer_address = issuer_address_1
        account.rsa_private_key = issuer_rsa_private_key_1
        account.rsa_public_key = issuer_rsa_public_key_1
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase_1)
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Account(Issuer2)
        account = Account()
        account.issuer_address = issuer_address_2
        account.rsa_private_key = issuer_rsa_private_key_2
        account.rsa_public_key = issuer_rsa_public_key_2
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase_2)
        account.rsa_status = 3
        db.add(account)

        # Deploy personal info contract
        contract_address_1, _, _ = ContractUtils.deploy_contract("PersonalInfo", [], issuer_address_1, issuer_private_key_1)
        personal_info_contract_1 = ContractUtils.get_contract("PersonalInfo", contract_address_1)
        contract_address_2, _, _ = ContractUtils.deploy_contract("PersonalInfo", [], issuer_address_2, issuer_private_key_2)
        personal_info_contract_2 = ContractUtils.get_contract("PersonalInfo", contract_address_2)

        # Issuer1 issues bond token.
        token_contract1 = deploy_bond_token_contract(
            issuer_address_1,
            issuer_private_key_1,
            personal_info_contract_1.address,
            transfer_approval_required=False,
        )
        token_address_1 = token_contract1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address_1
        token_1.abi = token_contract1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        # Issuer2 issues bond token.
        token_contract2 = deploy_bond_token_contract(
            issuer_address_2,
            issuer_private_key_2,
            personal_info_contract_2.address,
            transfer_approval_required=False,
        )
        token_address_2 = token_contract2.address
        token_2 = Token()
        token_2.type = TokenType.IBET_STRAIGHT_BOND.value
        token_2.token_address = token_address_2
        token_2.issuer_address = issuer_address_2
        token_2.abi = token_contract2.abi
        token_2.tx_hash = "tx_hash"
        db.add(token_2)

        db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
        }
        ciphertext = encrypt_personal_info(personal_info_1, issuer_rsa_public_key_1, issuer_rsa_passphrase_1)
        tx = personal_info_contract_1.functions.register(issuer_address_1, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key_1)

        personal_info_2 = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2"
        }
        ciphertext = encrypt_personal_info(personal_info_2, issuer_rsa_public_key_2, issuer_rsa_passphrase_2)
        tx = personal_info_contract_2.functions.register(issuer_address_2, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address_2,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key_2)

        # Run target process
        block_number = web3.eth.blockNumber
        processor.process()

        # Prepare data for assertion
        tmp_list = [
            {"issuer_address": issuer_address_1, "personal_info_address": personal_info_contract_1.address},
            {"issuer_address": issuer_address_2, "personal_info_address": personal_info_contract_2.address}
        ]
        personal_info_dict = {
            issuer_address_1: personal_info_1,
            issuer_address_2: personal_info_2,
        }
        unique_list = list(map(json.loads, set(map(json.dumps, tmp_list))))
        stored_address_order = [line["issuer_address"] for line in unique_list]

        # Assertion
        _personal_info_list = db.query(IDXPersonalInfo).all()
        assert len(_personal_info_list) == 2

        for i in range(2):
            _personal_info = _personal_info_list[i]
            assert _personal_info.id == i+1
            assert _personal_info.account_address == stored_address_order[i]
            assert _personal_info.issuer_address == stored_address_order[i]
            assert _personal_info.personal_info == personal_info_dict[stored_address_order[i]]

        _idx_personal_info_block_number = db.query(IDXPersonalInfoBlockNumber).first()
        assert _idx_personal_info_block_number.id == 1
        assert _idx_personal_info_block_number.latest_block_number == block_number

    # <Normal_5>
    # If block number processed in batch is equal or greater than current block number,
    # batch logs "skip Process".
    @mock.patch("web3.eth.Eth.blockNumber", 100)
    def test_normal_5(self, processor: Processor, db: Session, caplog: pytest.LogCaptureFixture):
        _idx_personal_info_block_number = IDXPersonalInfoBlockNumber()
        _idx_personal_info_block_number.id = 1
        _idx_personal_info_block_number.latest_block_number = 1000
        db.add(_idx_personal_info_block_number)
        db.commit()

        processor.process()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, "skip Process"))

    # <Normal_6>
    # If DB session fails in phase sinking register/modify events, batch logs exception message.
    def test_normal_6(self, processor: Processor, db: Session, personal_info_contract, caplog: pytest.LogCaptureFixture):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
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

        db.commit()

        # Register
        personal_info_1 = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
        }
        ciphertext = encrypt_personal_info(personal_info_1, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.register(issuer_address, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": user_address_1,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, user_private_key_1)

        # Modify
        personal_info_2 = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2"
        }
        ciphertext = encrypt_personal_info(personal_info_2, issuer_rsa_public_key, issuer_rsa_passphrase)
        tx = personal_info_contract.functions.modify(user_address_1, ciphertext).buildTransaction({
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, issuer_private_key)

        with patch.object(Session, "add", side_effect=Exception()):
            # Then execute processor.
            processor.process()

        assert 2 == caplog.record_tuples.count((LOG.name, logging.ERROR, "An exception occurred during event synchronization"))

    # <Error_1>
    # If DB session fails in phase sinking register/modify events, batch logs exception message.
    def test_error_1(self, main_func, db:Session, personal_info_contract, caplog: pytest.LogCaptureFixture):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        issuer_rsa_private_key = user_1["rsa_private_key"]
        issuer_rsa_public_key = user_1["rsa_public_key"]
        issuer_rsa_passphrase = "password"

        # Prepare data : Account
        account = Account()
        account.issuer_address = issuer_address
        account.rsa_private_key = issuer_rsa_private_key
        account.rsa_public_key = issuer_rsa_public_key
        account.rsa_passphrase = E2EEUtils.encrypt(issuer_rsa_passphrase)
        account.rsa_status = 3
        db.add(account)

        # Prepare data : Token
        token_contract_1 = deploy_bond_token_contract(issuer_address,
                                                      issuer_private_key,
                                                      personal_info_contract.address)
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND.value
        token_1.token_address = token_address_1
        token_1.issuer_address = issuer_address
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        db.add(token_1)

        db.commit()

        # Run mainloop once successfully
        with patch("batch.indexer_personal_info.INDEXER_SYNC_INTERVAL", None),\
            patch.object(Processor, "process", return_value=True), \
                pytest.raises(TypeError):
            main_func()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.DEBUG, "Processed"))
        caplog.clear()

        # Run mainloop once and fail with web3 utils error
        with patch("batch.indexer_personal_info.INDEXER_SYNC_INTERVAL", None),\
            patch.object(web3.eth, "contract", side_effect=ServiceUnavailableError()), \
                pytest.raises(TypeError):
            main_func()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.WARNING, "An external service was unavailable"))
        caplog.clear()

        # Run mainloop once and fail with sqlalchemy InvalidRequestError
        with patch("batch.indexer_personal_info.INDEXER_SYNC_INTERVAL", None),\
            patch.object(Session, "query", side_effect=InvalidRequestError()), \
                pytest.raises(TypeError):
            main_func()
        assert 1 == caplog.text.count("A database error has occurred")
        caplog.clear()

        # Run mainloop once and fail with connection to blockchain
        with patch("batch.indexer_personal_info.INDEXER_SYNC_INTERVAL", None), \
            patch.object(ContractUtils, "call_function", ConnectionError()), \
                pytest.raises(TypeError):
            main_func()
        assert 1 == caplog.record_tuples.count((LOG.name, logging.ERROR, "An exception occurred during event synchronization"))
        caplog.clear()
