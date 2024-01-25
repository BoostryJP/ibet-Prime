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
import time
from datetime import datetime

import pytest
from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select

import batch.indexer_e2e_messaging as indexer_e2e_messaging
from app.model.blockchain import E2EMessaging
from app.model.db import (
    E2EMessagingAccount,
    E2EMessagingAccountRsaKey,
    IDXE2EMessaging,
    IDXE2EMessagingBlockNumber,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import Web3Wrapper
from batch.indexer_e2e_messaging import Processor
from tests.account_config import config_eth_account

web3 = Web3Wrapper()


@pytest.fixture(scope="function")
def processor(db, e2e_messaging_contract):
    indexer_e2e_messaging.E2E_MESSAGING_CONTRACT_ADDRESS = (
        e2e_messaging_contract.address
    )
    return Processor()


class TestProcessor:
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
    # No event logs
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, db):
        # Prepare data : BlockNumber
        _idx_e2e_messaging_block_number = IDXE2EMessagingBlockNumber()
        _idx_e2e_messaging_block_number.latest_block_number = 0
        db.add(_idx_e2e_messaging_block_number)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Normal_2_1>
    # Single event logs
    # not generated RSA key after send
    @pytest.mark.asyncio
    async def test_normal_2_1(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        _type = "test_type"
        message = {
            "name": "テスト太郎1",
            "address": "東京都1",
        }
        message_message_str = json.dumps(message)
        sending_tx_hash, sending_tx_receipt = await E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            user_address_1,
            _type,
            message_message_str,
            self.rsa_public_key,
            user_address_2,
            user_private_key_2,
        )
        sending_block = web3.eth.get_block(sending_tx_receipt["blockNumber"])
        sending_block_timestamp = datetime.utcfromtimestamp(sending_block["timestamp"])

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 1
        _e2e_messaging = _e2e_messaging_list[0]
        assert _e2e_messaging.id == 1
        assert _e2e_messaging.transaction_hash == sending_tx_hash
        assert _e2e_messaging.from_address == user_address_2
        assert _e2e_messaging.to_address == user_address_1
        assert _e2e_messaging.type == _type
        assert _e2e_messaging.message == message_message_str
        assert _e2e_messaging.send_timestamp == sending_block_timestamp
        assert _e2e_messaging.block_timestamp == sending_block_timestamp
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Normal_2_2>
    # Single event logs
    # generated RSA key after send
    @pytest.mark.asyncio
    async def test_normal_2_2(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = "test1"
        _e2e_account_rsa_key.rsa_public_key = "test1"
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = "test2"
        _e2e_account_rsa_key.rsa_public_key = "test2"
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        # Send Message
        _type = "test_type"
        message = {
            "name": "テスト太郎1",
            "address": "東京都1",
        }
        message_message_str = json.dumps(message)
        sending_tx_hash, sending_tx_receipt = await E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            user_address_1,
            _type,
            message_message_str,
            self.rsa_public_key,
            user_address_2,
            user_private_key_2,
        )
        sending_block = web3.eth.get_block(sending_tx_receipt["blockNumber"])
        sending_block_timestamp = datetime.utcfromtimestamp(sending_block["timestamp"])

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = "test3"
        _e2e_account_rsa_key.rsa_public_key = "test3"
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = "test4"
        _e2e_account_rsa_key.rsa_public_key = "test4"
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 1
        _e2e_messaging = _e2e_messaging_list[0]
        assert _e2e_messaging.id == 1
        assert _e2e_messaging.transaction_hash == sending_tx_hash
        assert _e2e_messaging.from_address == user_address_2
        assert _e2e_messaging.to_address == user_address_1
        assert _e2e_messaging.type == _type
        assert _e2e_messaging.message == message_message_str
        assert _e2e_messaging.send_timestamp == sending_block_timestamp
        assert _e2e_messaging.block_timestamp == sending_block_timestamp
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Normal_3>
    # Multi event logs
    @pytest.mark.asyncio
    async def test_normal_3(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_3 = user_3["address"]
        user_private_key_3 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_2
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_2
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message(user3 -> user1)
        _type_1 = "test_type1"
        message = {
            "name": "テスト太郎1",
            "address": "東京都1",
        }
        message_message_str_1 = json.dumps(message)
        sending_tx_hash_1, sending_tx_receipt = await E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            user_address_1,
            _type_1,
            message_message_str_1,
            self.rsa_public_key,
            user_address_3,
            user_private_key_3,
        )
        sending_block = web3.eth.get_block(sending_tx_receipt["blockNumber"])
        sending_block_timestamp_1 = datetime.utcfromtimestamp(
            sending_block["timestamp"]
        )

        # Send Message(user3 -> user2)
        _type_2 = "test_type2"
        message = ["テスト太郎2", "東京都2"]
        message_message_str_2 = json.dumps(message)
        sending_tx_hash_2, sending_tx_receipt = await E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            user_address_2,
            _type_2,
            message_message_str_2,
            self.rsa_public_key,
            user_address_3,
            user_private_key_3,
        )
        sending_block = web3.eth.get_block(sending_tx_receipt["blockNumber"])
        sending_block_timestamp_2 = datetime.utcfromtimestamp(
            sending_block["timestamp"]
        )

        # Send Message(user3 -> user1)
        _type_3 = "test_type3"
        message_message_str_3 = "テスト太郎1,東京都1"
        sending_tx_hash_3, sending_tx_receipt = await E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            user_address_1,
            _type_3,
            message_message_str_3,
            self.rsa_public_key,
            user_address_3,
            user_private_key_3,
        )
        sending_block = web3.eth.get_block(sending_tx_receipt["blockNumber"])
        sending_block_timestamp_3 = datetime.utcfromtimestamp(
            sending_block["timestamp"]
        )

        # Send Message(user3 -> user2)
        _type_4 = "a" * 50
        message_message_str_4 = "a" * 5000
        sending_tx_hash_4, sending_tx_receipt = await E2EMessaging(
            e2e_messaging_contract.address
        ).send_message_external(
            user_address_2,
            _type_4,
            message_message_str_4,
            self.rsa_public_key,
            user_address_3,
            user_private_key_3,
        )
        sending_block = web3.eth.get_block(sending_tx_receipt["blockNumber"])
        sending_block_timestamp_4 = datetime.utcfromtimestamp(
            sending_block["timestamp"]
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 4
        _e2e_messaging = _e2e_messaging_list[0]
        assert _e2e_messaging.id == 1
        assert _e2e_messaging.transaction_hash == sending_tx_hash_1
        assert _e2e_messaging.from_address == user_address_3
        assert _e2e_messaging.to_address == user_address_1
        assert _e2e_messaging.type == _type_1
        assert _e2e_messaging.message == message_message_str_1
        assert _e2e_messaging.send_timestamp == sending_block_timestamp_1
        assert _e2e_messaging.block_timestamp == sending_block_timestamp_1
        _e2e_messaging = _e2e_messaging_list[1]
        assert _e2e_messaging.id == 2
        assert _e2e_messaging.transaction_hash == sending_tx_hash_2
        assert _e2e_messaging.from_address == user_address_3
        assert _e2e_messaging.to_address == user_address_2
        assert _e2e_messaging.type == _type_2
        assert _e2e_messaging.message == message_message_str_2
        assert _e2e_messaging.send_timestamp == sending_block_timestamp_2
        assert _e2e_messaging.block_timestamp == sending_block_timestamp_2
        _e2e_messaging = _e2e_messaging_list[2]
        assert _e2e_messaging.id == 3
        assert _e2e_messaging.transaction_hash == sending_tx_hash_3
        assert _e2e_messaging.from_address == user_address_3
        assert _e2e_messaging.to_address == user_address_1
        assert _e2e_messaging.type == _type_3
        assert _e2e_messaging.message == message_message_str_3
        assert _e2e_messaging.send_timestamp == sending_block_timestamp_3
        assert _e2e_messaging.block_timestamp == sending_block_timestamp_3
        _e2e_messaging = _e2e_messaging_list[3]
        assert _e2e_messaging.id == 4
        assert _e2e_messaging.transaction_hash == sending_tx_hash_4
        assert _e2e_messaging.from_address == user_address_3
        assert _e2e_messaging.to_address == user_address_2
        assert _e2e_messaging.type == _type_4
        assert _e2e_messaging.message == message_message_str_4
        assert _e2e_messaging.send_timestamp == sending_block_timestamp_4
        assert _e2e_messaging.block_timestamp == sending_block_timestamp_4
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Normal_4>
    # Not target message
    @pytest.mark.asyncio
    async def test_normal_4(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_3 = user_3["address"]

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        _type = "test_type"
        message = {
            "name": "テスト太郎1",
            "address": "東京都1",
        }
        message_message_str = json.dumps(message)
        await E2EMessaging(e2e_messaging_contract.address).send_message_external(
            user_address_3,  # not target
            _type,
            message_message_str,
            self.rsa_public_key,
            user_address_2,
            user_private_key_2,
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # format error
    # not json
    @pytest.mark.asyncio
    async def test_error_1_1(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        message = "test"
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_1_2>
    # format error
    # `type` does not exists
    @pytest.mark.asyncio
    async def test_error_1_2(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad("test_message".encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        rsa_key = RSA.import_key(self.rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode()
        message = json.dumps(
            {
                "text": {
                    "cipher_key": cipher_key,
                    "message": encrypted_message,
                }
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_1_3>
    # format error
    # `text` does not exists
    @pytest.mark.asyncio
    async def test_error_1_3(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        message = json.dumps(
            {
                "type": "test_type",
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_1_4>
    # format error
    # `text` max length over
    @pytest.mark.asyncio
    async def test_error_1_4(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad("test_message".encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        rsa_key = RSA.import_key(self.rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode()
        message = json.dumps(
            {
                "type": "a" * 51,
                "text": {"cipher_key": cipher_key, "message": encrypted_message},
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_1_5>
    # format error
    # `text.cipher_key` does not exists
    @pytest.mark.asyncio
    async def test_error_1_5(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad("test_message".encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {
                    "message": encrypted_message,
                },
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_1_6>
    # format error
    # `text.message` does not exists
    @pytest.mark.asyncio
    async def test_error_1_6(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        rsa_key = RSA.import_key(self.rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {
                    "cipher_key": cipher_key,
                },
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_1_7>
    # format error
    # decoded `text.message` max length over
    @pytest.mark.asyncio
    async def test_error_1_7(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad(("a" * 5001).encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        rsa_key = RSA.import_key(self.rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {"cipher_key": cipher_key, "message": encrypted_message},
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_2>
    # RSA key does not exists
    @pytest.mark.asyncio
    async def test_error_2(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Send Message
        _type = "test_type"
        message = {
            "name": "テスト太郎1",
            "address": "東京都1",
        }
        message_message_str = json.dumps(message)
        await E2EMessaging(e2e_messaging_contract.address).send_message_external(
            user_address_1,
            _type,
            message_message_str,
            self.rsa_public_key,
            user_address_2,
            user_private_key_2,
        )
        time.sleep(1)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = (
            datetime.utcnow()
        )  # Registry after send message
        db.add(_e2e_account_rsa_key)

        db.commit()

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_3_1>
    # message decode error
    # `text.cipher_key` is not AES key
    @pytest.mark.asyncio
    async def test_error_3_1(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad("test_message".encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {"cipher_key": "cipher_key", "message": encrypted_message},
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_3_2>
    # message decode error
    # `text.cipher_key` does not encrypt with RSA key
    @pytest.mark.asyncio
    async def test_error_3_2(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad("test_message".encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        cipher_key = base64.b64encode(aes_key).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {"cipher_key": cipher_key, "message": encrypted_message},
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_3_3>
    # message decode error
    # `text.cipher_key` encrypted other RSA key
    @pytest.mark.asyncio
    async def test_error_3_3(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        random_func = Random.new().read
        rsa = RSA.generate(4096, random_func)
        other_rsa_public_key = rsa.publickey().exportKey().decode()
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad("test_message".encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        rsa_key = RSA.import_key(other_rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {"cipher_key": cipher_key, "message": encrypted_message},
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_3_4>
    # message decode error
    # `text.message` does not encrypt
    @pytest.mark.asyncio
    async def test_error_3_4(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        rsa_key = RSA.import_key(self.rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {"cipher_key": cipher_key, "message": "test_message"},
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number

    # <Error_3_5>
    # message decode error
    # `text.message` encrypted other AES key
    @pytest.mark.asyncio
    async def test_error_3_5(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _e2e_account = E2EMessagingAccount()
        _e2e_account.account_address = user_address_1
        _e2e_account.is_deleted = False
        db.add(_e2e_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _e2e_account_rsa_key = E2EMessagingAccountRsaKey()
        _e2e_account_rsa_key.account_address = user_address_1
        _e2e_account_rsa_key.rsa_private_key = self.rsa_private_key
        _e2e_account_rsa_key.rsa_public_key = self.rsa_public_key
        _e2e_account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(self.rsa_passphrase)
        _e2e_account_rsa_key.block_timestamp = datetime.utcnow()
        db.add(_e2e_account_rsa_key)
        time.sleep(1)

        db.commit()

        # Send Message
        aes_key = os.urandom(32)
        aes_iv = os.urandom(16)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad("test_message".encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(
            aes_iv + aes_cipher.encrypt(pad_message)
        ).decode()
        rsa_key = RSA.import_key(self.rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        other_aes_key = os.urandom(32)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(other_aes_key)).decode()
        message = json.dumps(
            {
                "type": "test_type",
                "text": {"cipher_key": cipher_key, "message": encrypted_message},
            }
        )
        await E2EMessaging(e2e_messaging_contract.address).send_message(
            user_address_1, message, user_address_2, user_private_key_2
        )

        # Run target process
        block_number = web3.eth.block_number
        await processor.process()

        # Assertion
        _e2e_messaging_list = db.scalars(
            select(IDXE2EMessaging).order_by(IDXE2EMessaging.block_timestamp)
        ).all()
        assert len(_e2e_messaging_list) == 0
        _idx_e2e_messaging_block_number = db.scalars(
            select(IDXE2EMessagingBlockNumber).limit(1)
        ).first()
        assert _idx_e2e_messaging_block_number.id == 1
        assert _idx_e2e_messaging_block_number.latest_block_number == block_number
