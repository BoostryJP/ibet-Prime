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
import base64
import json
import os
from unittest import mock
from unittest.mock import MagicMock

import pytest
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import unpad
from eth_keyfile import decode_keyfile_json
from web3 import Web3
from web3.exceptions import TimeExhausted
from web3.middleware import geth_poa_middleware

from app.exceptions import SendTransactionError
from app.model.blockchain import E2EMessaging
from app.utils.contract_utils import ContractUtils
from config import WEB3_HTTP_PROVIDER
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestSendMessage:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        message = "test message"

        # Run Test
        tx_hash, tx_receipt = E2EMessaging(e2e_messaging_contract.address).send_message(
            to_address=user_address_2,
            message=message,
            tx_from=user_address_1,
            private_key=user_private_key_1,
        )

        # Assertion
        assert isinstance(tx_hash, str)
        assert tx_receipt["status"] == 1
        last_message = e2e_messaging_contract.functions.getLastMessage(
            user_address_2
        ).call()
        block = ContractUtils.get_block_by_transaction_hash(tx_hash)
        assert last_message[0] == user_address_1
        assert last_message[1] == message
        assert last_message[2] == block["timestamp"]

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Transaction Error
    def test_error_1(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        message = "test message"

        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.ContractUtils.send_transaction",
                MagicMock(side_effect=Exception("tx error")),
            ):
                # Run Test
                E2EMessaging(e2e_messaging_contract.address).send_message(
                    to_address=user_address_2,
                    message=message,
                    tx_from=user_address_1,
                    private_key=user_private_key_1,
                )

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, Exception)
        assert "tx error" in str(cause)

    # <Error_2>
    # Transaction Timeout
    def test_error_2(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        message = "test message"

        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.ContractUtils.send_transaction",
                MagicMock(side_effect=TimeExhausted("Timeout Error test")),
            ):
                # Run Test
                E2EMessaging(e2e_messaging_contract.address).send_message(
                    to_address=user_address_2,
                    message=message,
                    tx_from=user_address_1,
                    private_key=user_private_key_1,
                )

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, TimeExhausted)
        assert "Timeout Error test" in str(cause)


class TestSendMessageExternal:
    rsa_private_key = """-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: DES-EDE3-CBC,7A0E9E7404771106

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
-----END RSA PRIVATE KEY-----"""
    rsa_public_key = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvOlb0wLo/vw/FwFys8IX
/DE4pMNLGA/mJoZ6jz0DdQG4JqGnIitzdaPreZK9H75Cfs5yfNJmP7kJixqSNjyz
WFyZ+0Jf+hwaZ6CxIyTp4zm7A0OLdqzsFIdXXHWFF10g3iwd2KkvKeuocD5c/TT8
tuI2MzhLPwCUn/umBlVPswsRucAC67U5gig5KdeKkR6JdfwVO7OpeMX3gJT6A/Ns
YE/ce4vvF/aH7mNmirnCpkfeqEk5ANpw6bdpEGwYXAdxdD3DhIabMxUvrRZp5LEh
E7pl6K6sCvVKAPl5HPtZ5/AL/Kj7iLU88qY+TYE9bSTtWqhGabSlON7bo132EkZn
Y8BnCy4c8ni00hRkxQ8ZdH468DjzaXOtiNlBLGV7BXiMf7zIE3YJD7Xd22g/XKMs
FsL7F45sgez6SBxiVQrk5WuFtLLD08+3ZAYKqaxFmesw1Niqg6mBB1E+ipYOeBlD
xtUxBqY1kHdua48rjTwEBJz6M+X6YUzIaDS/j/GcFehSyBthj099whK629i1OY3A
PhrKAc+Fywn8tNTkjicPHdzDYzUL2STwAzhrbSfIIc2HlZJSks0Fqs+tQ4Iugep6
fdDfFGjZcF3BwH6NA0frWvUW5AhhkJyJZ8IJ4C0UqakBrRLn2rvThvdCPNPWJ/tx
EK7Y4zFFnfKP3WIA3atUbbcCAwEAAQ==
-----END PUBLIC KEY-----"""
    rsa_passphrase = "password"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        message_org = "test message"
        _type = "test_type"

        # Run Test
        tx_hash, tx_receipt = E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            to_address=user_address_2,
            _type=_type,
            message_org=message_org,
            to_rsa_public_key=self.rsa_public_key,
            tx_from=user_address_1,
            private_key=user_private_key_1,
        )

        # Assertion
        assert isinstance(tx_hash, str)
        assert tx_receipt["status"] == 1
        last_message = e2e_messaging_contract.functions.getLastMessage(
            user_address_2
        ).call()
        block = ContractUtils.get_block_by_transaction_hash(tx_hash)
        assert last_message[0] == user_address_1
        message_dict = json.loads(last_message[1])
        assert message_dict["type"] == _type
        cipher_key = message_dict["text"]["cipher_key"]
        rsa_key = RSA.importKey(self.rsa_private_key, passphrase=self.rsa_passphrase)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        aes_key = rsa_cipher.decrypt(base64.decodebytes(cipher_key.encode("utf-8")))
        assert len(aes_key) == AES.block_size * 2
        encrypt_message = base64.b64decode(message_dict["text"]["message"])
        aes_iv = encrypt_message[: AES.block_size]
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = aes_cipher.decrypt(encrypt_message[AES.block_size :])
        decrypt_message = unpad(pad_message, AES.block_size).decode()
        assert decrypt_message == message_org
        assert last_message[2] == block["timestamp"]

    # <Normal_2>
    # use AWS KMS
    @mock.patch(
        "app.model.blockchain.e2e_messaging.AWS_KMS_GENERATE_RANDOM_ENABLED", True
    )
    @mock.patch("boto3.client")
    def test_normal_2(self, boto3_mock, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        message_org = "test message"
        _type = "test_type"

        # mock
        class KMSClientMock:
            def __init__(self):
                self.call_cnt = 0

            def generate_random(self, NumberOfBytes):
                if self.call_cnt == 0:
                    assert NumberOfBytes == 32
                else:
                    assert NumberOfBytes == 16
                random_byte = os.urandom(NumberOfBytes)
                self.call_cnt += 1
                return {"Plaintext": random_byte}

        boto3_mock.side_effect = [KMSClientMock()]

        # Run Test
        tx_hash, tx_receipt = E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            to_address=user_address_2,
            _type=_type,
            message_org=message_org,
            to_rsa_public_key=self.rsa_public_key,
            tx_from=user_address_1,
            private_key=user_private_key_1,
        )

        # Assertion
        assert isinstance(tx_hash, str)
        assert tx_receipt["status"] == 1
        last_message = e2e_messaging_contract.functions.getLastMessage(
            user_address_2
        ).call()
        block = ContractUtils.get_block_by_transaction_hash(tx_hash)
        assert last_message[0] == user_address_1
        message_dict = json.loads(last_message[1])
        assert message_dict["type"] == _type
        cipher_key = message_dict["text"]["cipher_key"]
        rsa_key = RSA.importKey(self.rsa_private_key, passphrase=self.rsa_passphrase)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        aes_key = rsa_cipher.decrypt(base64.decodebytes(cipher_key.encode("utf-8")))
        assert len(aes_key) == AES.block_size * 2
        encrypt_message = base64.b64decode(message_dict["text"]["message"])
        aes_iv = encrypt_message[: AES.block_size]
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = aes_cipher.decrypt(encrypt_message[AES.block_size :])
        decrypt_message = unpad(pad_message, AES.block_size).decode()
        assert decrypt_message == message_org
        assert last_message[2] == block["timestamp"]

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Transaction Error
    def test_error_1(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        message_org = "test message"
        _type = "test_type"

        # Run Test
        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.ContractUtils.send_transaction",
                MagicMock(side_effect=Exception("tx error")),
            ):
                # Run Test
                E2EMessaging(e2e_messaging_contract.address).send_message_external(
                    to_address=user_address_2,
                    _type=_type,
                    message_org=message_org,
                    to_rsa_public_key=self.rsa_public_key,
                    tx_from=user_address_1,
                    private_key=user_private_key_1,
                )

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, Exception)
        assert "tx error" in str(cause)

    # <Error_2>
    # Transaction Timeout
    def test_error_2(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        message_org = "test message"
        _type = "test_type"

        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.ContractUtils.send_transaction",
                MagicMock(side_effect=TimeExhausted("Timeout Error test")),
            ):
                # Run Test
                E2EMessaging(e2e_messaging_contract.address).send_message_external(
                    to_address=user_address_2,
                    _type=_type,
                    message_org=message_org,
                    to_rsa_public_key=self.rsa_public_key,
                    tx_from=user_address_1,
                    private_key=user_private_key_1,
                )

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, TimeExhausted)
        assert "Timeout Error test" in str(cause)


class TestSetPublicKey:
    rsa_public_key = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvOlb0wLo/vw/FwFys8IX
/DE4pMNLGA/mJoZ6jz0DdQG4JqGnIitzdaPreZK9H75Cfs5yfNJmP7kJixqSNjyz
WFyZ+0Jf+hwaZ6CxIyTp4zm7A0OLdqzsFIdXXHWFF10g3iwd2KkvKeuocD5c/TT8
tuI2MzhLPwCUn/umBlVPswsRucAC67U5gig5KdeKkR6JdfwVO7OpeMX3gJT6A/Ns
YE/ce4vvF/aH7mNmirnCpkfeqEk5ANpw6bdpEGwYXAdxdD3DhIabMxUvrRZp5LEh
E7pl6K6sCvVKAPl5HPtZ5/AL/Kj7iLU88qY+TYE9bSTtWqhGabSlON7bo132EkZn
Y8BnCy4c8ni00hRkxQ8ZdH468DjzaXOtiNlBLGV7BXiMf7zIE3YJD7Xd22g/XKMs
FsL7F45sgez6SBxiVQrk5WuFtLLD08+3ZAYKqaxFmesw1Niqg6mBB1E+ipYOeBlD
xtUxBqY1kHdua48rjTwEBJz6M+X6YUzIaDS/j/GcFehSyBthj099whK629i1OY3A
PhrKAc+Fywn8tNTkjicPHdzDYzUL2STwAzhrbSfIIc2HlZJSks0Fqs+tQ4Iugep6
fdDfFGjZcF3BwH6NA0frWvUW5AhhkJyJZ8IJ4C0UqakBrRLn2rvThvdCPNPWJ/tx
EK7Y4zFFnfKP3WIA3atUbbcCAwEAAQ==
-----END PUBLIC KEY-----"""
    rsa_passphrase = "password"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        key_type = "RSA4098"

        # Run Test
        tx_hash, tx_receipt = E2EMessaging(
            e2e_messaging_contract.address
        ).set_public_key(
            public_key=self.rsa_public_key,
            key_type=key_type,
            tx_from=user_address_1,
            private_key=user_private_key_1,
        )

        # Assertion
        assert isinstance(tx_hash, str)
        assert tx_receipt["status"] == 1
        public_key = e2e_messaging_contract.functions.getPublicKey(
            user_address_1
        ).call()
        assert public_key[0] == self.rsa_public_key
        assert public_key[1] == key_type

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Transaction Error
    def test_error_1(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        key_type = "RSA4098"

        # Run Test
        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.ContractUtils.send_transaction",
                MagicMock(side_effect=Exception("tx error")),
            ):
                # Run Test
                E2EMessaging(e2e_messaging_contract.address).set_public_key(
                    public_key=self.rsa_public_key,
                    key_type=key_type,
                    tx_from=user_address_1,
                    private_key=user_private_key_1,
                )

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, Exception)
        assert "tx error" in str(cause)

    # <Error_2>
    # Transaction Timeout
    def test_error_2(self, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        key_type = "RSA4098"

        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.contract_utils.ContractUtils.send_transaction",
                MagicMock(side_effect=TimeExhausted("Timeout Error test")),
            ):
                # Run Test
                E2EMessaging(e2e_messaging_contract.address).set_public_key(
                    public_key=self.rsa_public_key,
                    key_type=key_type,
                    tx_from=user_address_1,
                    private_key=user_private_key_1,
                )

        # Assertion
        cause = exc_info.value.args[0]
        assert isinstance(cause, TimeExhausted)
        assert "Timeout Error test" in str(cause)
