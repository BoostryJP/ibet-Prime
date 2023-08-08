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
import time
from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import ANY, call

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.orm import Session

import batch.processor_rotate_e2e_messaging_rsa_key as processor_rotate_e2e_messaging_rsa_key
from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain import E2EMessaging
from app.model.db import E2EMessagingAccount, E2EMessagingAccountRsaKey
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_rotate_e2e_messaging_rsa_key import LOG, Processor
from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
def processor(db, e2e_messaging_contract):
    processor_rotate_e2e_messaging_rsa_key.E2E_MESSAGING_CONTRACT_ADDRESS = (
        e2e_messaging_contract.address
    )
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield Processor()
    log.propagate = False
    log.setLevel(default_log_level)


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # E2E messaging account is not exists
    def test_normal_1_1(self, processor, db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.is_deleted = True  # deleted
        db.add(_account)

        db.commit()

        # Run target process
        processor.process()

        # Assertion
        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey).order_by(
                E2EMessagingAccountRsaKey.block_timestamp
            )
        ).all()
        assert len(_rsa_key_list) == 0

    # <Normal_1_2>
    # E2E messaging account is not auto generated
    def test_normal_1_2(self, processor, db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.rsa_key_generate_interval = None
        _account.rsa_generation = None
        db.add(_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key_1 = E2EMessagingAccountRsaKey()
        _rsa_key_1.transaction_hash = "tx_1"
        _rsa_key_1.account_address = user_address_1
        _rsa_key_1.rsa_private_key = "rsa_private_key_1"
        _rsa_key_1.rsa_public_key = "rsa_public_key_1"
        _rsa_key_1.rsa_passphrase = "rsa_passphrase_1"
        _rsa_key_1.block_timestamp = datetime.utcnow()
        db.add(_rsa_key_1)

        db.commit()

        # Run target process
        processor.process()

        # Assertion
        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey).order_by(
                E2EMessagingAccountRsaKey.block_timestamp
            )
        ).all()
        assert len(_rsa_key_list) == 1
        _rsa_key = _rsa_key_list[0]
        assert _rsa_key.id == 1
        assert _rsa_key.transaction_hash == "tx_1"
        assert _rsa_key.account_address == user_address_1
        assert _rsa_key.rsa_private_key == "rsa_private_key_1"
        assert _rsa_key.rsa_public_key == "rsa_public_key_1"
        assert _rsa_key.rsa_passphrase == "rsa_passphrase_1"
        assert _rsa_key.block_timestamp == _rsa_key_1.block_timestamp

    # <Normal_1_3>
    # Last generation is within the interval
    def test_normal_1_3(self, processor, db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.rsa_key_generate_interval = 99999
        _account.rsa_generation = None
        db.add(_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key_1 = E2EMessagingAccountRsaKey()
        _rsa_key_1.transaction_hash = "tx_1"
        _rsa_key_1.account_address = user_address_1
        _rsa_key_1.rsa_private_key = "rsa_private_key_1"
        _rsa_key_1.rsa_public_key = "rsa_public_key_1"
        _rsa_key_1.rsa_passphrase = "rsa_passphrase_1"
        _rsa_key_1.block_timestamp = datetime.utcnow()
        db.add(_rsa_key_1)

        db.commit()

        # Run target process
        processor.process()

        # Assertion
        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey).order_by(
                E2EMessagingAccountRsaKey.block_timestamp
            )
        ).all()
        assert len(_rsa_key_list) == 1
        _rsa_key = _rsa_key_list[0]
        assert _rsa_key.id == 1
        assert _rsa_key.transaction_hash == "tx_1"
        assert _rsa_key.account_address == user_address_1
        assert _rsa_key.rsa_private_key == "rsa_private_key_1"
        assert _rsa_key.rsa_public_key == "rsa_public_key_1"
        assert _rsa_key.rsa_passphrase == "rsa_passphrase_1"
        assert _rsa_key.block_timestamp == _rsa_key_1.block_timestamp

    # <Normal_2>
    # auto generate and rotate
    def test_normal_2(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_keyfile_2 = user_2["keyfile_json"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        datetime_now = datetime.utcnow()

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key_1_1 = E2EMessagingAccountRsaKey()
        _rsa_key_1_1.transaction_hash = "tx_1"
        _rsa_key_1_1.account_address = user_address_1
        _rsa_key_1_1.rsa_private_key = "rsa_private_key_1_1"
        _rsa_key_1_1.rsa_public_key = "rsa_public_key_1_1"
        _rsa_key_1_1.rsa_passphrase = "rsa_passphrase_1_1"
        _rsa_key_1_1.block_timestamp = datetime_now + timedelta(hours=-1, seconds=-3)
        db.add(_rsa_key_1_1)
        time.sleep(1)

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key_1_2 = E2EMessagingAccountRsaKey()
        _rsa_key_1_2.transaction_hash = "tx_2"
        _rsa_key_1_2.account_address = user_address_1
        _rsa_key_1_2.rsa_private_key = "rsa_private_key_1_2"
        _rsa_key_1_2.rsa_public_key = "rsa_public_key_1_2"
        _rsa_key_1_2.rsa_passphrase = "rsa_passphrase_1_2"
        _rsa_key_1_2.block_timestamp = datetime_now + timedelta(hours=-1, seconds=-2)
        db.add(_rsa_key_1_2)
        time.sleep(1)

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key_1_3 = E2EMessagingAccountRsaKey()
        _rsa_key_1_3.transaction_hash = "tx_3"
        _rsa_key_1_3.account_address = user_address_1
        _rsa_key_1_3.rsa_private_key = "rsa_private_key_1_3"
        _rsa_key_1_3.rsa_public_key = "rsa_public_key_1_3"
        _rsa_key_1_3.rsa_passphrase = E2EEUtils.encrypt("latest_passphrase_1")
        _rsa_key_1_3.block_timestamp = datetime_now + timedelta(hours=-1, seconds=-1)
        db.add(_rsa_key_1_3)
        time.sleep(1)

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_2
        _account.keyfile = user_keyfile_2
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key_2_1 = E2EMessagingAccountRsaKey()
        _rsa_key_2_1.transaction_hash = "tx_4"
        _rsa_key_2_1.account_address = user_address_2
        _rsa_key_2_1.rsa_private_key = "rsa_private_key_2_1"
        _rsa_key_2_1.rsa_public_key = "rsa_public_key_2_2"
        _rsa_key_2_1.rsa_passphrase = E2EEUtils.encrypt("latest_passphrase_2")
        _rsa_key_2_1.block_timestamp = datetime_now + timedelta(hours=-1, seconds=-1)
        db.add(_rsa_key_2_1)
        time.sleep(1)

        db.commit()

        # mock
        mock_E2EMessaging_set_public_key = mock.patch(
            target="app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
            side_effect=[
                ("tx_5", {"blockNumber": 12345}),
                ("tx_6", {"blockNumber": 12350}),
            ],
        )
        mock_ContractUtils_get_block_by_transaction_hash = mock.patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            side_effect=[
                {
                    "number": 12345,
                    "timestamp": datetime(
                        2099, 4, 27, 12, 34, 56, tzinfo=timezone.utc
                    ).timestamp(),
                },
                {
                    "number": 12350,
                    "timestamp": datetime(
                        2099, 4, 27, 12, 34, 59, tzinfo=timezone.utc
                    ).timestamp(),
                },
            ],
        )

        # Run target process
        with (
            mock_E2EMessaging_set_public_key
        ), mock_ContractUtils_get_block_by_transaction_hash:
            processor.process()

            # # Assertion
            assert user_address_2 < user_address_1
            E2EMessaging.set_public_key.assert_has_calls(
                [
                    call(
                        public_key=ANY,
                        key_type="RSA4096",
                        tx_from=user_address_2,
                        private_key=user_private_key_2,
                    ),
                    call(
                        public_key=ANY,
                        key_type="RSA4096",
                        tx_from=user_address_1,
                        private_key=user_private_key_1,
                    ),
                ]
            )
            ContractUtils.get_block_by_transaction_hash.assert_has_calls(
                [call(tx_hash="tx_5"), call(tx_hash="tx_6")]
            )

        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey)
            .where(E2EMessagingAccountRsaKey.account_address == user_address_1)
            .order_by(E2EMessagingAccountRsaKey.block_timestamp)
        ).all()
        assert len(_rsa_key_list) == 2
        _rsa_key = _rsa_key_list[0]
        assert _rsa_key.id == 3
        assert _rsa_key.transaction_hash == "tx_3"
        assert _rsa_key.account_address == user_address_1
        assert _rsa_key.rsa_private_key == "rsa_private_key_1_3"
        assert _rsa_key.rsa_public_key == "rsa_public_key_1_3"
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == "latest_passphrase_1"
        assert _rsa_key.block_timestamp == _rsa_key_1_3.block_timestamp
        _rsa_key = _rsa_key_list[1]
        assert _rsa_key.id == 6
        assert _rsa_key.transaction_hash == "tx_6"
        assert _rsa_key.account_address == user_address_1
        assert _rsa_key.rsa_private_key is not None
        assert _rsa_key.rsa_private_key == ANY
        assert _rsa_key.rsa_public_key is not None
        assert _rsa_key.rsa_public_key == ANY
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == "latest_passphrase_1"
        assert _rsa_key.block_timestamp == datetime(2099, 4, 27, 12, 34, 59)
        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey)
            .where(E2EMessagingAccountRsaKey.account_address == user_address_2)
            .order_by(E2EMessagingAccountRsaKey.block_timestamp)
        ).all()
        assert len(_rsa_key_list) == 2
        _rsa_key = _rsa_key_list[0]
        assert _rsa_key.id == 4
        assert _rsa_key.transaction_hash == "tx_4"
        assert _rsa_key.account_address == user_address_2
        assert _rsa_key.rsa_private_key == "rsa_private_key_2_1"
        assert _rsa_key.rsa_public_key == "rsa_public_key_2_2"
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == "latest_passphrase_2"
        assert _rsa_key.block_timestamp == _rsa_key_1_3.block_timestamp
        _rsa_key = _rsa_key_list[1]
        assert _rsa_key.id == 5
        assert _rsa_key.transaction_hash == "tx_5"
        assert _rsa_key.account_address == user_address_2
        assert _rsa_key.rsa_private_key is not None
        assert _rsa_key.rsa_private_key == ANY
        assert _rsa_key.rsa_public_key is not None
        assert _rsa_key.rsa_public_key == ANY
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == "latest_passphrase_2"
        assert _rsa_key.block_timestamp == datetime(2099, 4, 27, 12, 34, 56)

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Could not get the EOA private key
    def test_error_1(self, processor, db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password_invalid")
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        datetime_now = datetime.utcnow()

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.transaction_hash = "tx_3"
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = "rsa_private_key_1_3"
        _rsa_key.rsa_public_key = "rsa_public_key_1_3"
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt("latest_passphrase_1")
        _rsa_key.block_timestamp = datetime_now + timedelta(hours=-1, seconds=-1)
        db.add(_rsa_key)
        time.sleep(1)

        db.commit()

        # Run target process
        processor.process()

        # Assertion
        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey).order_by(
                E2EMessagingAccountRsaKey.block_timestamp
            )
        ).all()

    # <Error_2>
    # Failed to send transaction
    def test_error_2(self, processor, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        datetime_now = datetime.utcnow()

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.transaction_hash = "tx_3"
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = "rsa_private_key_1_3"
        _rsa_key.rsa_public_key = "rsa_public_key_1_3"
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt("latest_passphrase_1")
        _rsa_key.block_timestamp = datetime_now + timedelta(hours=-1, seconds=-1)
        db.add(_rsa_key)
        time.sleep(1)

        db.commit()

        # mock
        mock_E2EMessaging_set_public_key = mock.patch(
            target="app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
            side_effect=SendTransactionError(),
        )

        # Run target process
        with mock_E2EMessaging_set_public_key:
            processor.process()

            # Assertion
            E2EMessaging.set_public_key.assert_called_with(
                public_key=ANY,
                key_type="RSA4096",
                tx_from=user_address_1,
                private_key=user_private_key_1,
            )

        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey).order_by(
                E2EMessagingAccountRsaKey.block_timestamp
            )
        ).all()
        assert len(_rsa_key_list) == 1

    # <Error_3>
    # ContractRevertError
    def test_error_3(
        self,
        processor: Processor,
        db: Session,
        e2e_messaging_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data : E2EMessagingAccount
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_key_generate_interval = 1
        _account.rsa_generation = 2
        db.add(_account)

        datetime_now = datetime.utcnow()

        # Prepare data : E2EMessagingAccountRsaKey
        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.transaction_hash = "tx_3"
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_private_key = "rsa_private_key_1_3"
        _rsa_key.rsa_public_key = "rsa_public_key_1_3"
        _rsa_key.rsa_passphrase = E2EEUtils.encrypt("latest_passphrase_1")
        _rsa_key.block_timestamp = datetime_now + timedelta(hours=-1, seconds=-1)
        db.add(_rsa_key)
        time.sleep(1)

        db.commit()

        # mock
        mock_E2EMessaging_set_public_key = mock.patch(
            target="app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
            side_effect=ContractRevertError("999999"),
        )

        # Run target process
        with mock_E2EMessaging_set_public_key:
            processor.process()

            # Assertion
            E2EMessaging.set_public_key.assert_called_with(
                public_key=ANY,
                key_type="RSA4096",
                tx_from=user_address_1,
                private_key=user_private_key_1,
            )

        _rsa_key_list = db.scalars(
            select(E2EMessagingAccountRsaKey).order_by(
                E2EMessagingAccountRsaKey.block_timestamp
            )
        ).all()
        assert len(_rsa_key_list) == 1
        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARNING,
                    f"Transaction reverted: account_address=<{user_address_1}> error_code:<999999> error_msg:<>",
                )
            )
            == 1
        )
