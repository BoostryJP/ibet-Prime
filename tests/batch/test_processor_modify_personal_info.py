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

import asyncio
import logging

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import func, select
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.model.db import (
    Account,
    AccountRsaKeyTemporary,
    AccountRsaStatus,
    IDXPersonalInfo,
    PersonalInfoDataSource,
    Token,
    TokenType,
    TokenVersion,
)
from app.model.ibet import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract,
)
from app.model.ibet.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.ibet.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import ContractUtils
from batch.processor_modify_personal_info import Processor
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture(scope="function")
def processor(async_db):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor(asyncio.Event())
    LOG.propagate = False
    LOG.setLevel(default_log_level)


def deploy_personal_info_contract(issuer_user):
    address = issuer_user["address"]
    keyfile = issuer_user["keyfile_json"]
    eoa_password = "password"

    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile, password=eoa_password.encode("utf-8")
    )
    contract_address, _, _ = ContractUtils.deploy_contract(
        "PersonalInfo", [], address, private_key
    )
    return contract_address


async def set_personal_info_contract(
    contract_address, issuer_account: Account, sender_list
):
    contract = ContractUtils.get_contract("PersonalInfo", contract_address)

    for sender in sender_list:
        tx = contract.functions.register(
            issuer_account.issuer_address, ""
        ).build_transaction(
            {
                "nonce": web3.eth.get_transaction_count(sender["user"]["address"]),
                "chainId": CHAIN_ID,
                "from": sender["user"]["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        private_key = decode_keyfile_json(
            raw_keyfile_json=sender["user"]["keyfile_json"],
            password="password".encode("utf-8"),
        )
        ContractUtils.send_transaction(tx, private_key)

        if sender["data"]:
            personal_info = PersonalInfoContract(
                logging.getLogger("unittest"), issuer_account, contract_address
            )
            await personal_info.modify_info(sender["user"]["address"], sender["data"])


async def deploy_bond_token_contract(issuer_user, personal_info_contract_address):
    address = issuer_user["address"]
    keyfile = issuer_user["keyfile_json"]
    eoa_password = "password"

    arguments = [
        "token.name",
        "token.symbol",
        10,
        20,
        "JPY",
        "token.redemption_date",
        30,
        "JPY",
        "token.return_date",
        "token.return_amount",
        "token.purpose",
    ]

    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile, password=eoa_password.encode("utf-8")
    )

    bond_contract = IbetStraightBondContract()
    contract_address, _, _ = await bond_contract.create(arguments, address, private_key)

    if personal_info_contract_address:
        data = IbetStraightBondUpdateParams()
        data.personal_info_contract_address = personal_info_contract_address
        await bond_contract.update(data, address, private_key)

    return contract_address


async def deploy_share_token_contract(issuer_user, personal_info_contract_address):
    address = issuer_user["address"]
    keyfile = issuer_user["keyfile_json"]
    eoa_password = "password"

    arguments = [
        "token.name",
        "token.symbol",
        10,
        20,
        3,
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        10,
    ]

    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile, password=eoa_password.encode("utf-8")
    )

    share_contract = IbetShareContract()
    contract_address, _, _ = await share_contract.create(
        arguments, address, private_key
    )

    if personal_info_contract_address:
        data = IbetShareUpdateParams()
        data.personal_info_contract_address = personal_info_contract_address
        await share_contract.update(data, address, private_key)

    return contract_address


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Execute Batch Run 1st: yet change RSA
    # Execute Batch Run 2nd: changed RSA
    # Execute Batch Run 3rd: modified PersonalInfo
    @pytest.mark.asyncio
    async def test_normal_1(
        self, processor, async_db, caplog: pytest.LogCaptureFixture
    ):
        user_1 = default_eth_account("user1")
        issuer_address_1 = user_1["address"]

        # prepare data
        # account
        account = Account()
        account.issuer_address = user_1["address"]
        account.keyfile = user_1["keyfile_json"]
        eoa_password = E2EEUtils.encrypt("password")
        account.eoa_password = eoa_password
        account.rsa_private_key = user_1["rsa_private_key"]
        account.rsa_public_key = user_1["rsa_public_key"]
        rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_passphrase = rsa_passphrase
        account.rsa_status = AccountRsaStatus.CHANGING.value
        async_db.add(account)

        temporary = AccountRsaKeyTemporary()
        temporary.issuer_address = user_1["address"]
        temporary.rsa_private_key = user_1["rsa_private_key"]
        temporary.rsa_public_key = user_1["rsa_public_key"]
        temporary.rsa_passphrase = rsa_passphrase
        async_db.add(temporary)

        # token
        personal_info_contract_address_1 = deploy_personal_info_contract(user_1)
        token_contract_address_1 = await deploy_bond_token_contract(
            user_1, personal_info_contract_address_1
        )
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = token_contract_address_1
        token_1.abi = {}
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        personal_info_contract_address_2 = deploy_personal_info_contract(user_1)
        token_contract_address_2 = await deploy_share_token_contract(
            user_1, personal_info_contract_address_2
        )
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash"
        token_2.issuer_address = issuer_address_1
        token_2.token_address = token_contract_address_2
        token_2.abi = {}
        token_2.version = TokenVersion.V_25_06
        async_db.add(token_2)

        token_contract_address_3 = await deploy_bond_token_contract(user_1, None)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.tx_hash = "tx_hash"
        token_3.issuer_address = issuer_address_1
        token_3.token_address = token_contract_address_3
        token_3.abi = {}
        token_3.version = TokenVersion.V_25_06
        async_db.add(token_3)

        token_contract_address_4 = await deploy_share_token_contract(user_1, None)
        token_4 = Token()
        token_4.type = TokenType.IBET_SHARE
        token_4.tx_hash = "tx_hash"
        token_4.issuer_address = issuer_address_1
        token_4.token_address = token_contract_address_4
        token_4.abi = {}
        token_4.version = TokenVersion.V_25_06
        async_db.add(token_4)

        # PersonalInfo
        personal_user_1 = default_eth_account("user2")
        personal_user_2 = default_eth_account("user3")
        personal_user_3 = default_eth_account("user4")
        personal_user_4 = default_eth_account("user5")

        idx_1 = IDXPersonalInfo()
        idx_1.issuer_address = user_1["address"]
        idx_1.account_address = personal_user_1["address"]
        idx_1.personal_info = {}
        idx_1.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(idx_1)

        idx_2 = IDXPersonalInfo()
        idx_2.issuer_address = user_1["address"]
        idx_2.account_address = personal_user_2["address"]
        idx_2.personal_info = {}
        idx_2.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(idx_2)

        await set_personal_info_contract(
            personal_info_contract_address_1,
            account,
            [
                {
                    "user": personal_user_1,
                    "data": {
                        "key_manager": "key_manager_user1",
                        "name": "name_user1",
                        "postal_code": "postal_code_user1",
                        "address": "address_user1",
                        "email": "email_user1",
                        "birth": "birth_user1",
                        "is_corporate": False,
                        "tax_category": 10,
                    },
                },
                {"user": personal_user_2, "data": ""},
            ],
        )

        idx_3 = IDXPersonalInfo()
        idx_3.issuer_address = user_1["address"]
        idx_3.account_address = personal_user_3["address"]
        idx_3.personal_info = {}
        idx_3.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(idx_3)

        idx_4 = IDXPersonalInfo()
        idx_4.issuer_address = user_1["address"]
        idx_4.account_address = personal_user_4["address"]
        idx_4.personal_info = {}
        idx_4.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(idx_4)

        await set_personal_info_contract(
            personal_info_contract_address_2,
            account,
            [
                {"user": personal_user_3, "data": ""},
                {
                    "user": personal_user_4,
                    "data": {
                        "key_manager": "key_manager_user4",
                        "name": "name_user4",
                        "postal_code": "postal_code_user4",
                        "address": "address_user4",
                        "email": "email_user4",
                        "birth": "birth_user4",
                        "is_corporate": True,
                        "tax_category": 20,
                    },
                },
            ],
        )

        await async_db.commit()

        # Execute batch(Run 1st)
        # Assume: Skip processing
        await processor.process()
        async_db.expire_all()

        # assertion(Run 1st)
        _account = (await async_db.scalars(select(Account).limit(1))).first()
        assert _account.issuer_address == user_1["address"]
        assert _account.keyfile == user_1["keyfile_json"]
        assert _account.eoa_password == eoa_password
        assert _account.rsa_private_key == user_1["rsa_private_key"]
        assert _account.rsa_public_key == user_1["rsa_public_key"]
        assert _account.rsa_passphrase == rsa_passphrase
        assert _account.rsa_status == AccountRsaStatus.CHANGING.value

        _temporary = (
            await async_db.scalars(select(AccountRsaKeyTemporary).limit(1))
        ).first()
        assert temporary.issuer_address == user_1["address"]
        assert temporary.rsa_private_key == user_1["rsa_private_key"]
        assert temporary.rsa_public_key == user_1["rsa_public_key"]
        assert temporary.rsa_passphrase == rsa_passphrase

        _personal_info_1 = PersonalInfoContract(
            logging.getLogger("unittest"), account, personal_info_contract_address_1
        )
        assert (
            await _personal_info_1.get_info(personal_user_1["address"])
        ) == {  # Previous RSA Decrypt
            "key_manager": "key_manager_user1",
            "name": "name_user1",
            "postal_code": "postal_code_user1",
            "address": "address_user1",
            "email": "email_user1",
            "birth": "birth_user1",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert (await _personal_info_1.get_info(personal_user_2["address"])) == {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        _personal_info_2 = PersonalInfoContract(
            logging.getLogger("unittest"), account, personal_info_contract_address_2
        )
        assert (await _personal_info_2.get_info(personal_user_3["address"])) == {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        assert (
            await _personal_info_2.get_info(personal_user_4["address"])
        ) == {  # Previous RSA Decrypt
            "key_manager": "key_manager_user4",
            "name": "name_user4",
            "postal_code": "postal_code_user4",
            "address": "address_user4",
            "email": "email_user4",
            "birth": "birth_user4",
            "is_corporate": True,
            "tax_category": 20,
        }

        # RSA Key Change Completed
        account = (await async_db.scalars(select(Account).limit(1))).first()
        account.rsa_private_key = personal_user_1["rsa_private_key"]
        account.rsa_public_key = personal_user_1["rsa_public_key"]
        await async_db.merge(account)

        await async_db.commit()

        # Execute batch(Run 2nd)
        # Assume: modified PersonalInfo, but DB not update
        await processor.process()
        await async_db.rollback()
        async_db.expire_all()

        # assertion(Run 2nd)
        _account = (await async_db.scalars(select(Account).limit(1))).first()
        assert _account.issuer_address == user_1["address"]
        assert _account.keyfile == user_1["keyfile_json"]
        assert _account.eoa_password == eoa_password
        assert _account.rsa_private_key == personal_user_1["rsa_private_key"]
        assert _account.rsa_public_key == personal_user_1["rsa_public_key"]
        assert _account.rsa_passphrase == rsa_passphrase
        assert _account.rsa_status == AccountRsaStatus.CHANGING.value

        _temporary = (
            await async_db.scalars(select(AccountRsaKeyTemporary).limit(1))
        ).first()
        assert temporary.issuer_address == user_1["address"]
        assert temporary.rsa_private_key == user_1["rsa_private_key"]
        assert temporary.rsa_public_key == user_1["rsa_public_key"]
        assert temporary.rsa_passphrase == rsa_passphrase

        _personal_info_1 = PersonalInfoContract(
            logging.getLogger("unittest"), account, personal_info_contract_address_1
        )
        assert (await _personal_info_1.get_info(personal_user_1["address"])) == {
            "key_manager": "key_manager_user1",
            "name": "name_user1",
            "postal_code": "postal_code_user1",
            "address": "address_user1",
            "email": "email_user1",
            "birth": "birth_user1",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert (await _personal_info_1.get_info(personal_user_2["address"])) == {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        _personal_info_2 = PersonalInfoContract(
            logging.getLogger("unittest"), account, personal_info_contract_address_2
        )
        assert (await _personal_info_2.get_info(personal_user_3["address"])) == {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        assert (await _personal_info_2.get_info(personal_user_4["address"])) == {
            "key_manager": "key_manager_user4",
            "name": "name_user4",
            "postal_code": "postal_code_user4",
            "address": "address_user4",
            "email": "email_user4",
            "birth": "birth_user4",
            "is_corporate": True,
            "tax_category": 20,
        }

        # Execute batch(Run 3rd)
        # Assume: DB update
        await processor.process()
        await async_db.rollback()
        async_db.expire_all()

        # assertion(Run 3rd)
        assert "Failed to decrypt" not in caplog.text
        assert (
            "background",
            logging.INFO,
            f"Modify personal info process is completed: issuer={user_1['address']}",
        ) in caplog.record_tuples

        _account = (await async_db.scalars(select(Account).limit(1))).first()
        assert _account.issuer_address == user_1["address"]
        assert _account.keyfile == user_1["keyfile_json"]
        assert _account.eoa_password == eoa_password
        assert _account.rsa_private_key == personal_user_1["rsa_private_key"]
        assert _account.rsa_public_key == personal_user_1["rsa_public_key"]
        assert _account.rsa_passphrase == rsa_passphrase
        assert _account.rsa_status == AccountRsaStatus.SET.value

        _temporary_count = await async_db.scalar(
            select(func.count()).select_from(select(AccountRsaKeyTemporary).subquery())
        )
        assert _temporary_count == 0

        _personal_info_1 = PersonalInfoContract(
            logging.getLogger("unittest"), account, personal_info_contract_address_1
        )
        assert (await _personal_info_1.get_info(personal_user_1["address"])) == {
            "key_manager": "key_manager_user1",
            "name": "name_user1",
            "postal_code": "postal_code_user1",
            "address": "address_user1",
            "email": "email_user1",
            "birth": "birth_user1",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert (await _personal_info_1.get_info(personal_user_2["address"])) == {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        _personal_info_2 = PersonalInfoContract(
            logging.getLogger("unittest"), account, personal_info_contract_address_2
        )
        assert (await _personal_info_2.get_info(personal_user_3["address"])) == {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        assert (await _personal_info_2.get_info(personal_user_4["address"])) == {
            "key_manager": "key_manager_user4",
            "name": "name_user4",
            "postal_code": "postal_code_user4",
            "address": "address_user4",
            "email": "email_user4",
            "birth": "birth_user4",
            "is_corporate": True,
            "tax_category": 20,
        }

    ###########################################################################
    # Error Case
    ###########################################################################
