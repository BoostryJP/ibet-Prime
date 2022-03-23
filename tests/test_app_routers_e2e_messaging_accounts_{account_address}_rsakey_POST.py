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
from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import ANY
import time
from datetime import (
    datetime,
    timezone
)

from eth_keyfile import decode_keyfile_json

from config import (
    E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG,
    E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE
)
from app.model.blockchain import E2EMessaging
from app.model.db import (
    E2EMessagingAccount,
    E2EMessagingAccountRsaKey,
    AccountRsaStatus
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.exceptions import SendTransactionError
from tests.account_config import config_eth_account


class TestAppRoutersE2EMessagingAccountsAccountAddressRsakeyPOST:
    # target API endpoint
    base_url = "/e2e_messaging_accounts/{account_address}/rsakey"

    valid_password = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \*\+\.\\\(\)\?\[\]\^\$\-\|!#%&\"',/:;<=>@_`{}~"
    invalid_password = "password🚀"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # specify rsa_passphrase
    def test_normal_1(self, client, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_public_key = "rsa_public_key_1_1"
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        # mock
        mock_E2EMessaging_set_public_key = mock.patch(
            target="app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
            side_effect=[("tx_1", {"blockNumber": 12345})]
        )
        mock_ContractUtils_get_block_by_transaction_hash = mock.patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            side_effect=[
                {
                    "number": 12345,
                    "timestamp": datetime(2099, 4, 27, 12, 34, 56, tzinfo=timezone.utc).timestamp()
                },
            ]
        )

        # request target api
        with mock.patch("app.routers.e2e_messaging_account.E2E_MESSAGING_CONTRACT_ADDRESS",
                        e2e_messaging_contract.address), \
             mock_E2EMessaging_set_public_key, mock_ContractUtils_get_block_by_transaction_hash:
            req_param = {
                "rsa_passphrase": E2EEUtils.encrypt(self.valid_password)
            }
            resp = client.post(
                self.base_url.format(account_address=user_address_1),
                json=req_param
            )

            # assertion
            E2EMessaging.set_public_key.assert_called_with(
                contract_address=e2e_messaging_contract.address,
                public_key=ANY,
                key_type="RSA4096",
                tx_from=user_address_1,
                private_key=user_private_key_1
            )
            ContractUtils.get_block_by_transaction_hash.assert_called_with(
                tx_hash="tx_1",
            )

        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": user_address_1,
            "rsa_key_generate_interval": None,
            "rsa_generation": None,
            "rsa_public_key": ANY,
            "rsa_status": AccountRsaStatus.SET.value,
            "is_deleted": False,
        }
        _rsa_key_list = db.query(E2EMessagingAccountRsaKey).order_by(E2EMessagingAccountRsaKey.block_timestamp).all()
        assert len(_rsa_key_list) == 2
        _rsa_key = _rsa_key_list[1]
        assert _rsa_key.id == 2
        assert _rsa_key.transaction_hash == "tx_1"
        assert _rsa_key.account_address == user_address_1
        assert _rsa_key.rsa_private_key == ANY
        assert _rsa_key.rsa_public_key == resp.json()["rsa_public_key"]
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == self.valid_password
        assert _rsa_key.block_timestamp == datetime(2099, 4, 27, 12, 34, 56)

    # <Normal_2>
    # not specify rsa_passphrase(use default)
    def test_normal_2(self, client, db, e2e_messaging_contract):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        _rsa_key = E2EMessagingAccountRsaKey()
        _rsa_key.account_address = user_address_1
        _rsa_key.rsa_public_key = "rsa_public_key_1_1"
        _rsa_key.block_timestamp = datetime.utcnow()
        db.add(_rsa_key)
        time.sleep(1)

        # mock
        mock_E2EMessaging_set_public_key = mock.patch(
            target="app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
            side_effect=[("tx_1", {"blockNumber": 12345})]
        )
        mock_ContractUtils_get_block_by_transaction_hash = mock.patch(
            target="app.utils.contract_utils.ContractUtils.get_block_by_transaction_hash",
            side_effect=[
                {
                    "number": 12345,
                    "timestamp": datetime(2099, 4, 27, 12, 34, 56, tzinfo=timezone.utc).timestamp()
                },
            ]
        )

        # request target api
        with mock.patch("app.routers.e2e_messaging_account.E2E_MESSAGING_CONTRACT_ADDRESS",
                        e2e_messaging_contract.address), \
             mock_E2EMessaging_set_public_key, mock_ContractUtils_get_block_by_transaction_hash:
            req_param = {}
            resp = client.post(
                self.base_url.format(account_address=user_address_1),
                json=req_param
            )

            # assertion
            E2EMessaging.set_public_key.assert_called_with(
                contract_address=e2e_messaging_contract.address,
                public_key=ANY,
                key_type="RSA4096",
                tx_from=user_address_1,
                private_key=user_private_key_1
            )
            ContractUtils.get_block_by_transaction_hash.assert_called_with(
                tx_hash="tx_1",
            )

        assert resp.status_code == 200
        assert resp.json() == {
            "account_address": user_address_1,
            "rsa_key_generate_interval": None,
            "rsa_generation": None,
            "rsa_public_key": ANY,
            "rsa_status": AccountRsaStatus.SET.value,
            "is_deleted": False,
        }
        _rsa_key_list = db.query(E2EMessagingAccountRsaKey).order_by(E2EMessagingAccountRsaKey.block_timestamp).all()
        assert len(_rsa_key_list) == 2
        _rsa_key = _rsa_key_list[1]
        assert _rsa_key.id == 2
        assert _rsa_key.transaction_hash == "tx_1"
        assert _rsa_key.account_address == user_address_1
        assert _rsa_key.rsa_private_key == ANY
        assert _rsa_key.rsa_public_key == resp.json()["rsa_public_key"]
        assert E2EEUtils.decrypt(_rsa_key.rsa_passphrase) == E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE
        assert _rsa_key.block_timestamp == datetime(2099, 4, 27, 12, 34, 56)

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Parameter Error
    # no body
    def test_error_1_1(self, client, db):
        resp = client.post(self.base_url.format(account_address="0x1234567890123456789012345678900000000000"))

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_1_2>
    # Parameter Error: rsa_passphrase
    def test_error_1_2(self, client, db):
        req_param = {
            "rsa_passphrase": "test"
        }
        resp = client.post(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["body", "rsa_passphrase"],
                    "msg": "rsa_passphrase is not a Base64-encoded encrypted data",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2>
    # Not Exists E2E Messaging Account
    def test_error_2(self, client, db):
        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt(self.valid_password)
        }
        resp = client.post(
            self.base_url.format(account_address="0x1234567890123456789012345678900000000000"),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "e2e messaging account is not exists"
        }

    # <Error_3>
    # Passphrase Policy Violation
    def test_error_3(self, client, db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt(self.invalid_password)
        }
        resp = client.post(
            self.base_url.format(account_address=user_address_1),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG
        }

    # <Error_4>
    # Send Transaction Error
    @mock.patch("app.model.blockchain.e2e_messaging.E2EMessaging.set_public_key",
                MagicMock(side_effect=SendTransactionError))
    def test_error_4(self, client, db):
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_keyfile_1 = user_1["keyfile_json"]

        # prepare data
        _account = E2EMessagingAccount()
        _account.account_address = user_address_1
        _account.keyfile = user_keyfile_1
        _account.eoa_password = E2EEUtils.encrypt("password")
        db.add(_account)

        req_param = {
            "rsa_passphrase": E2EEUtils.encrypt(self.valid_password)
        }
        resp = client.post(
            self.base_url.format(account_address=user_address_1),
            json=req_param,
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 2,
                "title": "SendTransactionError"
            },
            "detail": "failed to send transaction"
        }
