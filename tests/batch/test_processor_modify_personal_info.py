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
from typing import Any, Sequence, TypedDict

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch.processor_modify_personal_info import Processor
from config import ZERO_ADDRESS
from tests.account_config import default_eth_account
from tests.types import UnitTestAccount


class FakeContract:
    def __init__(self, address: str):
        self.address = address


_TOKEN_PERSONAL_INFO: dict[str, str] = {}
_PERSONAL_INFO_REGISTERED: set[tuple[str, str, str]] = set()
_PERSONAL_INFO_VALUES: dict[
    tuple[str, str, str], tuple[dict[str, Any], str | None]
] = {}
_personal_info_counter = 0
_token_counter = 0


def _default_personal_info(default_value: Any | None = None) -> dict[str, Any]:
    return {
        "key_manager": default_value,
        "name": default_value,
        "postal_code": default_value,
        "address": default_value,
        "email": default_value,
        "birth": default_value,
        "is_corporate": default_value,
        "tax_category": default_value,
    }


def _normalize_personal_info(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "key_manager": data.get("key_manager"),
        "name": data.get("name"),
        "postal_code": data.get("postal_code"),
        "address": data.get("address"),
        "email": data.get("email"),
        "birth": data.get("birth"),
        "is_corporate": data.get("is_corporate"),
        "tax_category": data.get("tax_category"),
    }


@pytest.fixture(scope="function", autouse=True)
def blockchain_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    global _personal_info_counter, _token_counter
    _TOKEN_PERSONAL_INFO.clear()
    _PERSONAL_INFO_REGISTERED.clear()
    _PERSONAL_INFO_VALUES.clear()
    _personal_info_counter = 0
    _token_counter = 0

    async def get_token(self: Any):
        self.personal_info_contract_address = _TOKEN_PERSONAL_INFO.get(
            self.token_address, ZERO_ADDRESS
        )
        return self

    async def call_function(
        contract: FakeContract,
        function_name: str,
        args: tuple[Any, ...],
        default_returns: Any = None,
    ) -> Any:
        if function_name == "isRegistered":
            account_address, issuer_address = args
            return (
                contract.address,
                account_address,
                issuer_address,
            ) in _PERSONAL_INFO_REGISTERED
        if function_name == "personal_info":
            account_address, issuer_address = args
            state = _PERSONAL_INFO_VALUES.get(
                (contract.address, account_address, issuer_address)
            )
            encrypted_info = "encrypted" if state is not None else ""
            return [ZERO_ADDRESS, ZERO_ADDRESS, encrypted_info]
        return default_returns

    async def get_info(
        self: PersonalInfoContract,
        account_address: str,
        default_value: Any | None = None,
    ) -> dict[str, Any]:
        key = (
            self.personal_info_contract.address,
            account_address,
            self.issuer.issuer_address,
        )
        state = _PERSONAL_INFO_VALUES.get(key)
        if state is None or state[1] != self.issuer.rsa_private_key:
            return _default_personal_info(default_value)
        return dict(state[0])

    async def modify_info(
        self: PersonalInfoContract,
        account_address: str,
        data: dict[str, Any],
        default_value: Any | None = None,
    ) -> None:
        key = (
            self.personal_info_contract.address,
            account_address,
            self.issuer.issuer_address,
        )
        _PERSONAL_INFO_VALUES[key] = (
            _normalize_personal_info(data),
            self.issuer.rsa_private_key,
        )

    def get_contract(contract_name: str, contract_address: str) -> FakeContract:
        return FakeContract(contract_address)

    monkeypatch.setattr(AsyncContractUtils, "call_function", call_function)
    monkeypatch.setattr(AsyncContractUtils, "get_contract", get_contract)
    monkeypatch.setattr(IbetShareContract, "get", get_token)
    monkeypatch.setattr(IbetStraightBondContract, "get", get_token)
    monkeypatch.setattr(PersonalInfoContract, "get_info", get_info)
    monkeypatch.setattr(PersonalInfoContract, "modify_info", modify_info)


@pytest.fixture(scope="function")
def processor(async_db: AsyncSession):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor(asyncio.Event())
    LOG.propagate = False
    LOG.setLevel(default_log_level)


def create_fake_personal_info_contract(issuer_user: UnitTestAccount) -> str:
    global _personal_info_counter
    _personal_info_counter += 1
    return f"0x{0x900 + _personal_info_counter:040x}"


class PersonalInfoSender(TypedDict):
    user: UnitTestAccount
    data: dict[str, Any] | str


async def set_personal_info_contract(
    contract_address: str,
    issuer_account: Account,
    sender_list: Sequence[PersonalInfoSender],
) -> None:
    for sender in sender_list:
        sender_address = sender["user"]["address"]
        key = (contract_address, sender_address, issuer_account.issuer_address)
        _PERSONAL_INFO_REGISTERED.add(key)
        if isinstance(sender["data"], dict):
            _PERSONAL_INFO_VALUES[key] = (
                _normalize_personal_info(sender["data"]),
                issuer_account.rsa_private_key,
            )


async def create_fake_bond_token_contract(
    issuer_user: UnitTestAccount, personal_info_contract_address: str | None
) -> str:
    global _token_counter
    _token_counter += 1
    token_address = f"0x{0x700 + _token_counter:040x}"
    _TOKEN_PERSONAL_INFO[token_address] = personal_info_contract_address or ZERO_ADDRESS
    return token_address


async def create_fake_share_token_contract(
    issuer_user: UnitTestAccount, personal_info_contract_address: str | None
) -> str:
    global _token_counter
    _token_counter += 1
    token_address = f"0x{0x800 + _token_counter:040x}"
    _TOKEN_PERSONAL_INFO[token_address] = personal_info_contract_address or ZERO_ADDRESS
    return token_address


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
        self,
        processor: Processor,
        async_db: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        user_1 = default_eth_account("user1")
        issuer_address_1 = user_1["address"]

        # prepare data
        # account
        account = Account()
        account.is_deleted = False
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
        personal_info_contract_address_1 = create_fake_personal_info_contract(user_1)
        token_contract_address_1 = await create_fake_bond_token_contract(
            user_1, personal_info_contract_address_1
        )
        token_1 = Token()
        token_1.type = TokenType.IBET_STRAIGHT_BOND
        token_1.tx_hash = "tx_hash"
        token_1.issuer_address = issuer_address_1
        token_1.token_address = token_contract_address_1
        token_1.abi = {}
        token_1.version = TokenVersion.V_25_09
        async_db.add(token_1)

        personal_info_contract_address_2 = create_fake_personal_info_contract(user_1)
        token_contract_address_2 = await create_fake_share_token_contract(
            user_1, personal_info_contract_address_2
        )
        token_2 = Token()
        token_2.type = TokenType.IBET_SHARE
        token_2.tx_hash = "tx_hash"
        token_2.issuer_address = issuer_address_1
        token_2.token_address = token_contract_address_2
        token_2.abi = {}
        token_2.version = TokenVersion.V_25_09
        async_db.add(token_2)

        token_contract_address_3 = await create_fake_bond_token_contract(user_1, None)
        token_3 = Token()
        token_3.type = TokenType.IBET_STRAIGHT_BOND
        token_3.tx_hash = "tx_hash"
        token_3.issuer_address = issuer_address_1
        token_3.token_address = token_contract_address_3
        token_3.abi = {}
        token_3.version = TokenVersion.V_25_09
        async_db.add(token_3)

        token_contract_address_4 = await create_fake_share_token_contract(user_1, None)
        token_4 = Token()
        token_4.type = TokenType.IBET_SHARE
        token_4.tx_hash = "tx_hash"
        token_4.issuer_address = issuer_address_1
        token_4.token_address = token_contract_address_4
        token_4.abi = {}
        token_4.version = TokenVersion.V_25_09
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
        _account: Account | None = (
            await async_db.scalars(select(Account).limit(1))
        ).first()
        assert _account is not None
        assert _account.issuer_address == user_1["address"]
        assert _account.keyfile == user_1["keyfile_json"]
        assert _account.eoa_password == eoa_password
        assert _account.rsa_private_key == user_1["rsa_private_key"]
        assert _account.rsa_public_key == user_1["rsa_public_key"]
        assert _account.rsa_passphrase == rsa_passphrase
        assert _account.rsa_status == AccountRsaStatus.CHANGING.value

        _temporary: AccountRsaKeyTemporary | None = (
            await async_db.scalars(select(AccountRsaKeyTemporary).limit(1))
        ).first()
        assert _temporary is not None
        assert _temporary.issuer_address == user_1["address"]
        assert _temporary.rsa_private_key == user_1["rsa_private_key"]
        assert _temporary.rsa_public_key == user_1["rsa_public_key"]
        assert _temporary.rsa_passphrase == rsa_passphrase

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
        account: Account | None = (
            await async_db.scalars(select(Account).limit(1))
        ).first()
        assert account is not None
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
        _account: Account | None = (
            await async_db.scalars(select(Account).limit(1))
        ).first()
        assert _account is not None
        assert _account.issuer_address == user_1["address"]
        assert _account.keyfile == user_1["keyfile_json"]
        assert _account.eoa_password == eoa_password
        assert _account.rsa_private_key == personal_user_1["rsa_private_key"]
        assert _account.rsa_public_key == personal_user_1["rsa_public_key"]
        assert _account.rsa_passphrase == rsa_passphrase
        assert _account.rsa_status == AccountRsaStatus.CHANGING.value

        _temporary: AccountRsaKeyTemporary | None = (
            await async_db.scalars(select(AccountRsaKeyTemporary).limit(1))
        ).first()
        assert _temporary is not None
        assert _temporary.issuer_address == user_1["address"]
        assert _temporary.rsa_private_key == user_1["rsa_private_key"]
        assert _temporary.rsa_public_key == user_1["rsa_public_key"]
        assert _temporary.rsa_passphrase == rsa_passphrase

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

        _account: Account | None = (
            await async_db.scalars(select(Account).limit(1))
        ).first()
        assert _account is not None
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
