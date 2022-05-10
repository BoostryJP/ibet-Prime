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
import base64
import json

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from eth_keyfile import decode_keyfile_json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted
from unittest.mock import MagicMock
from unittest import mock

from config import WEB3_HTTP_PROVIDER, TX_GAS_LIMIT, CHAIN_ID
from app.model.blockchain import PersonalInfoContract
from app.utils.contract_utils import ContractUtils
from app.exceptions import SendTransactionError
from app.model.db import Account
from app.utils.e2ee_utils import E2EEUtils

from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def initialize(issuer, db):
    _account = Account()
    _account.issuer_address = issuer["address"]
    _account.keyfile = issuer["keyfile_json"]
    eoa_password = "password"
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    _account.rsa_private_key = issuer["rsa_private_key"]
    _account.rsa_public_key = issuer["rsa_public_key"]
    rsa_password = "password"
    _account.rsa_passphrase = E2EEUtils.encrypt(rsa_password)
    db.add(_account)
    db.commit()

    private_key = decode_keyfile_json(
        raw_keyfile_json=issuer["keyfile_json"],
        password=eoa_password.encode("utf-8")
    )
    contract_address, _, _ = ContractUtils.deploy_contract("PersonalInfo", [], issuer["address"], private_key)

    personal_info_contract = PersonalInfoContract(db, issuer["address"], contract_address)
    return personal_info_contract


class TestGetInfo:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Run Test
        get_info = personal_info_contract.get_info(setting_user["address"])

        assert get_info == data

    # <Normal_2>
    # Unset Information
    def test_normal_2(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], "").buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Run Test
        get_info = personal_info_contract.get_info(setting_user["address"], default_value="test")

        assert get_info == {
            "key_manager": "test",
            "name": "test",
            "postal_code": "test",
            "address": "test",
            "email": "test",
            "birth": "test",
            "is_corporate": "test",
            "tax_category": "test"
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Invalid RSA Private Key
    def test_error_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Invalid RSA Private Key
        personal_info_contract.issuer.rsa_private_key = "testtest"

        # Run Test
        get_info = personal_info_contract.get_info(setting_user["address"], default_value="test")

        assert get_info == {
            "key_manager": "test",
            "name": "test",
            "postal_code": "test",
            "address": "test",
            "email": "test",
            "birth": "test",
            "is_corporate": False,
            "tax_category": 10
        }

    # <Error_2>
    # Decrypt Fail
    def test_error_2(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], "testtest").buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID

        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Run Test
        get_info = personal_info_contract.get_info(setting_user["address"], default_value="test")

        assert get_info == {
            "key_manager": "test",
            "name": "test",
            "postal_code": "test",
            "address": "test",
            "email": "test",
            "birth": "test",
            "is_corporate": False,
            "tax_category": 10
        }


class TestRegisterInfo:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # not register
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Run Test
        setting_user = config_eth_account("user2")
        register_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        personal_info_contract.register_info(setting_user["address"], register_data)

        get_info = personal_info_contract.get_info(setting_user["address"])

        assert get_info == register_data

    # <Normal_2>
    # registered
    def test_normal_2(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Run Test
        update_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        personal_info_contract.register_info(setting_user["address"], update_data)

        get_info = personal_info_contract.get_info(setting_user["address"])

        assert get_info == update_data

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # SendTransactionError(Timeout)
    def test_error_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Run Test
        setting_user = config_eth_account("user2")
        register_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=TimeExhausted())):
            with pytest.raises(SendTransactionError):
                personal_info_contract.register_info(setting_user["address"], register_data)

    # <Error_1>
    # SendTransactionError(Other Error)
    def test_error_2(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Run Test
        setting_user = config_eth_account("user2")
        register_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=TypeError())):
            with pytest.raises(SendTransactionError):
                personal_info_contract.modify_info(setting_user["address"], register_data)


class TestModifyInfo:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Run Test
        update_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        personal_info_contract.modify_info(setting_user["address"], update_data)

        get_info = personal_info_contract.get_info(setting_user["address"])

        assert get_info == update_data

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # SendTransactionError(Timeout)
    def test_error_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Run Test
        update_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=TimeExhausted())):
            with pytest.raises(SendTransactionError):
                personal_info_contract.modify_info(setting_user["address"], update_data)

    # <Error_1>
    # SendTransactionError(Other Error)
    def test_error_2(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        # Run Test
        update_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=TypeError())):
            with pytest.raises(SendTransactionError):
                personal_info_contract.modify_info(setting_user["address"], update_data)


class TestGetRegisterEvent:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        block_number_before = web3.eth.blockNumber

        # Set personal information data(Register)
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        block_number_after = web3.eth.blockNumber

        events = personal_info_contract.get_register_event(block_number_before, block_number_after)

        args = events[0]["args"]
        assert args["account_address"] == setting_user["address"]
        assert args["link_address"] == issuer["address"]


class TestGetModifyEvent:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db):
        issuer = config_eth_account("user1")
        personal_info_contract = initialize(issuer, db)

        # Set personal information data
        setting_user = config_eth_account("user2")
        rsa_password = "password"
        rsa = RSA.importKey(personal_info_contract.issuer.rsa_public_key, passphrase=rsa_password)
        cipher = PKCS1_OAEP.new(rsa)
        data = {
            "key_manager": "1234567890",
            "name": "name_test1",
            "postal_code": "1001000",
            "address": "テスト住所",
            "email": "sample@test.test",
            "birth": "19801231",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.register(issuer["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(setting_user["address"]),
            "from": setting_user["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        eoa_password = "password"
        private_key = decode_keyfile_json(
            raw_keyfile_json=setting_user["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        block_number_before = web3.eth.blockNumber

        # Modify
        update_data = {
            "key_manager": "0987654321",
            "name": "name_test2",
            "postal_code": "2002000",
            "address": "テスト住所2",
            "email": "sample@test.test2",
            "birth": "19800101",
            "is_corporate": False,
            "tax_category": 10
        }
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(update_data).encode('utf-8')))
        contract = personal_info_contract.personal_info_contract
        tx = contract.functions.modify(setting_user["address"], ciphertext).buildTransaction({
            "nonce": web3.eth.getTransactionCount(issuer["address"]),
            "from": issuer["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
            "chainId": CHAIN_ID
        })
        private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"],
            password=eoa_password.encode("utf-8")
        )
        ContractUtils.send_transaction(tx, private_key)

        block_number_after = web3.eth.blockNumber

        events = personal_info_contract.get_modify_event(block_number_before, block_number_after)

        args = events[0]["args"]
        assert args["account_address"] == setting_user["address"]
        assert args["link_address"] == issuer["address"]
