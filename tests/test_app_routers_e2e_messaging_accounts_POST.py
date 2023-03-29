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
from datetime import datetime, timezone
from unittest import mock
from unittest.mock import ANY, MagicMock

from app.exceptions import SendTransactionError
from app.model.blockchain import E2EMessaging
from app.model.db import E2EMessagingAccount, E2EMessagingAccountRsaKey, TransactionLock
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from config import (
    E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE,
    E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG,
    EOA_PASSWORD_PATTERN_MSG,
)


class TestAppRoutersE2EMessagingAccountsPOST:
    # target API endpoint
    base_url = "/e2e_messaging/accounts"

    valid_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"
    valid_password_rsa = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~rsa"
    invalid_password = "password🚀"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db, e2e_messaging_contract):
        _accounts_before = db.query(E2EMessagingAccount).all()
        _rsa_key_before = db.query(E2EMessagingAccountRsaKey).all()
        _transaction_before = db.query(TransactionLock).all()

        # mock
        mock_E2EMessaging_set_public_key = mock.patch(
            target="app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
            side_effect=[("tx_1", {"blockNumber": 12345})],
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
            ],
        )

        with mock.patch(
            "app.routers.e2e_messaging.E2E_MESSAGING_CONTRACT_ADDRESS",
            e2e_messaging_contract.address,
        ), (
            mock_E2EMessaging_set_public_key
        ), mock_ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {"eoa_password": E2EEUtils.encrypt(self.valid_password)}
            resp = client.post(self.base_url, json=req_param)

            # assertion
            E2EMessaging.set_public_key.assert_called_with(
                public_key=ANY,
                key_type="RSA4096",
                tx_from=resp.json()["account_address"],
                private_key=ANY,
            )
            ContractUtils.get_block_by_transaction_hash.assert_called_with(
                tx_hash="tx_1",
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": ANY,
            "rsa_key_generate_interval": 24,
            "rsa_generation": 7,
            "rsa_public_key": ANY,
            "is_deleted": False,
        }

        _accounts_after = db.query(E2EMessagingAccount).all()
        _rsa_key_after = db.query(E2EMessagingAccountRsaKey).all()
        _transaction_after = db.query(TransactionLock).all()

        assert 0 == len(_accounts_before)
        assert 1 == len(_accounts_after)
        _account = _accounts_after[0]
        assert _account.account_address == resp.json()["account_address"]
        assert _account.keyfile is not None
        assert E2EEUtils.decrypt(_account.eoa_password) == self.valid_password
        assert _account.rsa_key_generate_interval == 24
        assert _account.rsa_generation == 7
        assert _account.is_deleted is False
        assert 0 == len(_rsa_key_before)
        assert 1 == len(_rsa_key_after)
        _rsa_key = _rsa_key_after[0]
        assert _rsa_key.id == 1
        assert _rsa_key.transaction_hash == "tx_1"
        assert _rsa_key.account_address == resp.json()["account_address"]
        assert _rsa_key.rsa_private_key == ANY
        assert _rsa_key.rsa_public_key == resp.json()["rsa_public_key"]
        assert (
            E2EEUtils.decrypt(_rsa_key.rsa_passphrase)
            == E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE
        )
        assert _rsa_key.block_timestamp == datetime(2099, 4, 27, 12, 34, 56)
        assert 0 == len(_transaction_before)
        assert 1 == len(_transaction_after)
        _transaction = _transaction_after[0]
        assert _transaction.tx_from == resp.json()["account_address"]

    # <Normal_2>
    # use AWS KMS
    def test_normal_2(self, client, db, e2e_messaging_contract):
        _accounts_before = db.query(E2EMessagingAccount).all()
        _rsa_key_before = db.query(E2EMessagingAccountRsaKey).all()
        _transaction_before = db.query(TransactionLock).all()

        # mock
        class KMSClientMock:
            def generate_random(self, NumberOfBytes):
                assert NumberOfBytes == 32
                return {"Plaintext": b"12345678901234567890123456789012"}

        mock_boto3_client = mock.patch(
            target="boto3.client", side_effect=[KMSClientMock()]
        )
        mock_E2EMessaging_set_public_key = mock.patch(
            target="app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
            side_effect=[("tx_1", {"blockNumber": 12345})],
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
            ],
        )

        with mock.patch(
            "app.routers.e2e_messaging.AWS_KMS_GENERATE_RANDOM_ENABLED", True
        ), mock.patch(
            "app.routers.e2e_messaging.E2E_MESSAGING_CONTRACT_ADDRESS",
            e2e_messaging_contract.address,
        ), (
            mock_boto3_client
        ), (
            mock_E2EMessaging_set_public_key
        ), mock_ContractUtils_get_block_by_transaction_hash:
            # request target api
            req_param = {
                "eoa_password": E2EEUtils.encrypt(self.valid_password),
                "rsa_passphrase": E2EEUtils.encrypt(self.valid_password_rsa),
                "rsa_key_generate_interval": 1,
                "rsa_generation": 2,
            }
            resp = client.post(self.base_url, json=req_param)

            # assertion
            E2EMessaging.set_public_key.assert_called_with(
                public_key=ANY,
                key_type="RSA4096",
                tx_from=resp.json()["account_address"],
                private_key=ANY,
            )
            ContractUtils.get_block_by_transaction_hash.assert_called_with(
                tx_hash="tx_1",
            )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": ANY,
            "rsa_key_generate_interval": 1,
            "rsa_generation": 2,
            "rsa_public_key": ANY,
            "is_deleted": False,
        }

        _accounts_after = db.query(E2EMessagingAccount).all()
        _rsa_key_after = db.query(E2EMessagingAccountRsaKey).all()
        _transaction_after = db.query(TransactionLock).all()

        assert 0 == len(_accounts_before)
        assert 1 == len(_accounts_after)
        _account = _accounts_after[0]
        assert _account.account_address == resp.json()["account_address"]
        assert _account.keyfile is not None
        assert E2EEUtils.decrypt(_account.eoa_password) == self.valid_password
        assert _account.rsa_key_generate_interval == 1
        assert _account.rsa_generation == 2
        assert _account.is_deleted is False
        assert 0 == len(_rsa_key_before)
        assert 1 == len(_rsa_key_after)
        _rsa_key = _rsa_key_after[0]
        assert _rsa_key.id == 1
        assert _rsa_key.transaction_hash == "tx_1"
        assert _rsa_key.account_address == resp.json()["account_address"]
        assert _rsa_key.rsa_private_key == ANY
        assert _rsa_key.rsa_public_key == resp.json()["rsa_public_key"]
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == self.valid_password_rsa
        assert _rsa_key.block_timestamp == datetime(2099, 4, 27, 12, 34, 56)
        assert 0 == len(_transaction_before)
        assert 1 == len(_transaction_after)
        _transaction = _transaction_after[0]
        assert _transaction.tx_from == resp.json()["account_address"]

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Parameter Error
    # no body
    def test_error_1_1(self, client, db):
        resp = client.post(self.base_url)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ],
        }

    # <Error_1_2>
    # Parameter Error
    # required field
    def test_error_1_2(self, client, db):
        req_param = {}
        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body", "eoa_password"],
                    "msg": "field required",
                    "type": "value_error.missing",
                },
            ],
        }

    # <Error_1_3>
    # Parameter Error
    # not encrypted, min
    def test_error_1_3(self, client, db):
        req_param = {
            "eoa_password": base64.encodebytes("password".encode("utf-8")).decode(),
            "rsa_passphrase": base64.encodebytes(
                "password_rsa".encode("utf-8")
            ).decode(),
            "rsa_key_generate_interval": -1,
            "rsa_generation": -1,
        }

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body", "eoa_password"],
                    "msg": "eoa_password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                },
                {
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "rsa_passphrase is not a Base64-encoded encrypted data",
                    "type": "value_error",
                },
                {
                    "loc": ["body", "rsa_key_generate_interval"],
                    "ctx": {"limit_value": 0},
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge",
                },
                {
                    "loc": ["body", "rsa_generation"],
                    "ctx": {"limit_value": 0},
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge",
                },
            ],
        }

    # <Error_1_4>
    # Parameter Error
    # max
    def test_error_1_4(self, client, db):
        password = self.valid_password
        req_param = {
            "eoa_password": E2EEUtils.encrypt(password),
            "rsa_key_generate_interval": 10_001,
            "rsa_generation": 101,
        }

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "loc": ["body", "rsa_key_generate_interval"],
                    "ctx": {"limit_value": 10_000},
                    "msg": "ensure this value is less than or equal to 10000",
                    "type": "value_error.number.not_le",
                },
                {
                    "loc": ["body", "rsa_generation"],
                    "ctx": {"limit_value": 100},
                    "msg": "ensure this value is less than or equal to 100",
                    "type": "value_error.number.not_le",
                },
            ],
        }

    # <Error_2_1>
    # Passphrase Policy Violation
    # eoa_password
    def test_error_2_1(self, client, db):
        req_param = {"eoa_password": E2EEUtils.encrypt(self.invalid_password)}

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": EOA_PASSWORD_PATTERN_MSG,
        }

    # <Error_2_2>
    # Passphrase Policy Violation
    # rsa_passphrase
    def test_error_2_2(self, client, db):
        req_param = {
            "eoa_password": E2EEUtils.encrypt(self.valid_password),
            "rsa_passphrase": E2EEUtils.encrypt(self.invalid_password),
        }

        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG,
        }

    # <Error_3>
    # Send Transaction Error
    @mock.patch(
        "app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
        MagicMock(side_effect=SendTransactionError),
    )
    def test_error_3(self, client, db, e2e_messaging_contract):
        # request target api
        req_param = {"eoa_password": E2EEUtils.encrypt(self.valid_password)}
        resp = client.post(self.base_url, json=req_param)

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }
