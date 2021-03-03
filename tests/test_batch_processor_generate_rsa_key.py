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

from app.model.db import Account, AccountRsaStatus
from app.model.utils import E2EEUtils
from batch.processor_generate_rsa_key import Sinks, DBSink, Processor
from tests.account_config import config_eth_account


@pytest.fixture(scope='function')
def processor(db):
    _sink = Sinks()
    _sink.register(DBSink(db))
    return Processor(sink=_sink, db=db)


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address_1 = user_1["address"]
        keyfile_1 = user_1["keyfile_json"]
        eoa_password_1 = E2EEUtils.encrypt("password_user1")
        rsa_passphrase_1 = E2EEUtils.encrypt("passphrase_user1")

        user_2 = config_eth_account("user2")
        issuer_address_2 = user_2["address"]
        keyfile_2 = user_2["keyfile_json"]
        eoa_password_2 = E2EEUtils.encrypt("password_user2")
        rsa_private_key_2 = user_2["rsa_private_key"]
        rsa_public_key_2 = user_2["rsa_public_key"]
        rsa_passphrase_2 = E2EEUtils.encrypt("passphrase_user2")

        user_3 = config_eth_account("user3")
        issuer_address_3 = user_3["address"]
        keyfile_3 = user_3["keyfile_json"]
        eoa_password_3 = E2EEUtils.encrypt("password_user3")

        user_4 = config_eth_account("user4")
        issuer_address_4 = user_4["address"]
        keyfile_4 = user_4["keyfile_json"]
        eoa_password_4 = E2EEUtils.encrypt("password_user4")
        rsa_private_key_4 = user_4["rsa_private_key"]
        rsa_public_key_4 = user_4["rsa_public_key"]
        rsa_passphrase_4 = E2EEUtils.encrypt("passphrase_user4")

        # prepare data
        # data:CREATING
        account_1 = Account()
        account_1.issuer_address = issuer_address_1
        account_1.keyfile = keyfile_1
        account_1.eoa_password = eoa_password_1
        account_1.rsa_passphrase = rsa_passphrase_1
        account_1.rsa_status = AccountRsaStatus.CREATING.value
        db.add(account_1)

        # data:CHANGING
        account_2 = Account()
        account_2.issuer_address = issuer_address_2
        account_2.keyfile = keyfile_2
        account_2.eoa_password = eoa_password_2
        account_2.rsa_private_key = rsa_private_key_2
        account_2.rsa_public_key = rsa_public_key_2
        account_2.rsa_passphrase = rsa_passphrase_2
        account_2.rsa_status = AccountRsaStatus.CHANGING.value
        db.add(account_2)

        # data:UNSET(Non-Target)
        account_3 = Account()
        account_3.issuer_address = issuer_address_3
        account_3.keyfile = keyfile_3
        account_3.eoa_password = eoa_password_3
        account_3.rsa_status = AccountRsaStatus.UNSET.value
        db.add(account_3)

        # data:SET(Non-Target)
        account_4 = Account()
        account_4.issuer_address = issuer_address_4
        account_4.keyfile = keyfile_4
        account_4.eoa_password = eoa_password_4
        account_4.rsa_private_key = rsa_private_key_4
        account_4.rsa_public_key = rsa_public_key_4
        account_4.rsa_passphrase = rsa_passphrase_4
        account_4.rsa_status = AccountRsaStatus.SET.value
        db.add(account_4)

        # Execute batch
        processor.process()

        # assertion
        account_after = db.query(Account).order_by(Account.created).all()
        assert len(account_after) == 4
        _account = account_after[0]
        assert _account.issuer_address == issuer_address_1
        assert _account.keyfile == keyfile_1
        assert _account.eoa_password == eoa_password_1
        assert _account.rsa_private_key is not None
        assert _account.rsa_public_key is not None
        assert _account.rsa_passphrase == rsa_passphrase_1
        assert _account.rsa_status == AccountRsaStatus.SET.value
        _account = account_after[1]
        assert _account.issuer_address == issuer_address_2
        assert _account.keyfile == keyfile_2
        assert _account.eoa_password == eoa_password_2
        assert _account.rsa_private_key is not None and _account.rsa_private_key != rsa_private_key_2
        assert _account.rsa_public_key is not None and _account.rsa_private_key != rsa_public_key_2
        assert _account.rsa_passphrase == rsa_passphrase_2
        assert _account.rsa_status == AccountRsaStatus.CHANGING.value  # don't change
        _account = account_after[2]
        assert _account.issuer_address == issuer_address_3
        assert _account.keyfile == keyfile_3
        assert _account.eoa_password == eoa_password_3
        assert _account.rsa_private_key is None
        assert _account.rsa_public_key is None
        assert _account.rsa_passphrase is None
        assert _account.rsa_status == AccountRsaStatus.UNSET.value
        _account = account_after[3]
        assert _account.issuer_address == issuer_address_4
        assert _account.keyfile == keyfile_4
        assert _account.eoa_password == eoa_password_4
        assert _account.rsa_private_key == rsa_private_key_4
        assert _account.rsa_public_key == rsa_public_key_4
        assert _account.rsa_passphrase == rsa_passphrase_4
        assert _account.rsa_status == AccountRsaStatus.SET.value

    ###########################################################################
    # Error Case
    ###########################################################################
