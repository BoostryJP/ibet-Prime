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

from datetime import datetime
from typing import Any
from unittest.mock import ANY, patch

import pytest
from httpx import AsyncClient
from pytz import timezone
from sqlalchemy.ext.asyncio import AsyncSession

import config
from app.model.db import (
    Account,
    AccountRsaStatus,
    Token,
    TokenType,
    TokenUpdateOperationCategory,
    TokenUpdateOperationLog,
    TokenVersion,
)
from app.model.ibet import IbetStraightBondContract
from app.model.schema import IbetStraightBondCreate
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import default_eth_account

TEST_TOKEN_ADDRESS = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
TEST_PERSONAL_INFO_CONTRACT_ADDRESS = "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"


def build_mock_bond_contract(
    address: str,
    token_address: str,
    token_create_param: dict[str, Any],
    include_address: bool = False,
) -> IbetStraightBondContract:
    contract = IbetStraightBondContract(token_address)
    if include_address:
        setattr(contract, "address", token_address)
    contract.issuer_address = address
    contract.name = token_create_param["name"]
    contract.symbol = token_create_param["symbol"]
    contract.total_supply = token_create_param["total_supply"]
    contract.tradable_exchange_contract_address = token_create_param[
        "tradable_exchange_contract_address"
    ]
    contract.contact_information = token_create_param["contact_information"]
    contract.privacy_policy = token_create_param["privacy_policy"]
    contract.status = token_create_param["status"]
    contract.personal_info_contract_address = token_create_param[
        "personal_info_contract_address"
    ]
    contract.require_personal_info_registered = token_create_param[
        "require_personal_info_registered"
    ]
    contract.transferable = token_create_param["transferable"]
    contract.is_offering = token_create_param["is_offering"]
    contract.transfer_approval_required = token_create_param[
        "transfer_approval_required"
    ]
    contract.face_value = token_create_param["face_value"]
    contract.face_value_currency = token_create_param["face_value_currency"]
    contract.interest_rate = token_create_param["interest_rate"]
    contract.interest_payment_currency = token_create_param["interest_payment_currency"]
    contract.interest_payment_date = [
        *token_create_param["interest_payment_date"],
        *([""] * (12 - len(token_create_param["interest_payment_date"]))),
    ]
    contract.redemption_date = token_create_param["redemption_date"]
    contract.redemption_value = token_create_param["redemption_value"]
    contract.redemption_value_currency = token_create_param["redemption_value_currency"]
    contract.return_date = token_create_param["return_date"]
    contract.return_amount = token_create_param["return_amount"]
    contract.base_fx_rate = token_create_param["base_fx_rate"]
    contract.purpose = token_create_param["purpose"]
    contract.memo = ""
    contract.is_redeemed = token_create_param["is_redeemed"]
    return contract


async def prepare_bond_token_history_fixture(
    session: AsyncSession,
    address: str,
    personal_info_contract_address: str,
    tradable_exchange_contract_address: str = config.ZERO_ADDRESS,
    transfer_approval_required: bool = True,
    created: datetime | None = None,
) -> tuple[Any, dict[str, Any]]:
    token_address = TEST_TOKEN_ADDRESS
    token_create_param: dict[str, Any] = IbetStraightBondCreate(
        name="token.name",
        total_supply=100,
        face_value=20,
        face_value_currency="JPY",
        purpose="token.purpose",
        symbol="token.symbol",
        redemption_date="20230501",
        redemption_value=30,
        redemption_value_currency="JPY",
        return_date="20230501",
        return_amount="token.return_amount",
        interest_rate=0.0001,
        interest_payment_date=["0331", "0930"],
        transferable=True,
        is_redeemed=False,
        status=False,
        is_offering=True,
        tradable_exchange_contract_address=tradable_exchange_contract_address,
        personal_info_contract_address=personal_info_contract_address,
        require_personal_info_registered=False,
        image_url=None,
        contact_information="contact info test",
        privacy_policy="privacy policy test",
        transfer_approval_required=transfer_approval_required,
        interest_payment_currency="JPY",
        base_fx_rate=123.456789,
    ).model_dump(exclude={"image_url", "activate_ibet_wst", "ibet_wst_name"})

    token_update_operation_log = TokenUpdateOperationLog()
    token_update_operation_log.issuer_address = address
    token_update_operation_log.token_address = token_address
    token_update_operation_log.type = TokenType.IBET_STRAIGHT_BOND
    token_update_operation_log.issuer_address = address
    token_update_operation_log.arguments = token_create_param
    token_update_operation_log.original_contents = None
    token_update_operation_log.operation_category = TokenUpdateOperationCategory.ISSUE
    if created:
        token_update_operation_log.created = created
    session.add(token_update_operation_log)

    await session.commit()

    return (
        build_mock_bond_contract(
            address, token_address, token_create_param, include_address=True
        ),
        token_create_param,
    )


class TestListBondOperationLogHistory:
    # target API endpoint
    base_url = "/bond/tokens/{}/history"

    @staticmethod
    async def create_history_by_api(
        async_client: AsyncClient, token_address: str, issuer_address: str
    ) -> None:
        create_param = dict(
            IbetStraightBondCreate(
                name="token.name",
                total_supply=100,
                face_value=20,
                face_value_currency="JPY",
                purpose="token.purpose",
                symbol="token.symbol",
                redemption_date="20230501",
                redemption_value=30,
                redemption_value_currency="JPY",
                return_date="20230501",
                return_amount="token.return_amount",
                interest_rate=0.0001,
                interest_payment_date=["0331", "0930"],
                transferable=True,
                is_redeemed=False,
                status=False,
                is_offering=True,
                tradable_exchange_contract_address=config.ZERO_ADDRESS,
                personal_info_contract_address=TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
                require_personal_info_registered=False,
                image_url=None,
                contact_information="contact info test",
                privacy_policy="privacy policy test",
                transfer_approval_required=True,
                interest_payment_currency="JPY",
                base_fx_rate=123.456789,
            ).model_dump(exclude={"image_url", "activate_ibet_wst", "ibet_wst_name"})
        )
        base_contract = build_mock_bond_contract(
            issuer_address, token_address, create_param
        )
        face_value_contract = build_mock_bond_contract(
            issuer_address, token_address, create_param
        )
        face_value_contract.face_value = 10000
        interest_rate_contract = build_mock_bond_contract(
            issuer_address, token_address, create_param
        )
        interest_rate_contract.face_value = 10000
        interest_rate_contract.interest_rate = 0.5

        with (
            patch(
                "app.model.ibet.token.IbetStraightBondContract.get",
                side_effect=[
                    base_contract,
                    face_value_contract,
                    interest_rate_contract,
                ],
            ),
            patch(
                "app.model.ibet.token.IbetStraightBondContract.update",
                return_value=None,
            ),
        ):
            await async_client.post(
                f"/bond/tokens/{token_address}",
                json={"face_value": 10000, "memo": None},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )
            await async_client.post(
                f"/bond/tokens/{token_address}",
                json={"interest_rate": 0.5, "memo": None},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )
            await async_client.post(
                f"/bond/tokens/{token_address}",
                json={"interest_payment_date": ["0101", "0701"], "memo": None},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

    @staticmethod
    def expected_original_after_issue(
        create_token_param: dict[str, Any], issuer_address: str, token_address: str
    ) -> dict[str, Any]:
        interest_payment_date: list[str] = [
            (
                create_token_param["interest_payment_date"][i]
                if len(create_token_param["interest_payment_date"]) > i
                else ""
            )
            for i in range(12)
        ]

        expected_original: dict[str, Any] = {
            **create_token_param,
            "contract_name": "IbetStraightBond",
            "interest_payment_date": interest_payment_date,
            "issuer_address": issuer_address,
            "memo": "",
            "token_address": token_address,
        }
        expected_original.pop("ibet_wst_blockchains", None)
        return expected_original

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # prepare data: Token
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = "no_record_address"
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(_token.token_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0,
            },
            "history": [],
        }

    # <Normal_2>
    # Multiple record
    @pytest.mark.asyncio
    async def test_normal_2(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
        )
        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_1>
    # Search filter: trigger
    @pytest.mark.asyncio
    async def test_normal_3_1(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "operation_category": "Update",
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_2>
    # Search filter: modified_contents
    @pytest.mark.asyncio
    async def test_normal_3_2(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "modified_contents": "face_value",
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_3>
    # Search filter: created_from
    @pytest.mark.asyncio
    async def test_normal_3_3(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, _ = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
            created=datetime(2023, 5, 1, tzinfo=timezone("UTC")).replace(tzinfo=None),
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        _operation_log_1 = TokenUpdateOperationLog()
        _operation_log_1.created = datetime(2023, 5, 2, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_1.issuer_address = _issuer_address
        _operation_log_1.token_address = _token_address
        _operation_log_1.type = TokenType.IBET_STRAIGHT_BOND
        _operation_log_1.arguments = {"memo": "20230502"}
        _operation_log_1.original_contents = {}
        _operation_log_1.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_1)

        _operation_log_2 = TokenUpdateOperationLog()
        _operation_log_2.created = datetime(2023, 5, 3, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_2.issuer_address = _issuer_address
        _operation_log_2.token_address = _token_address
        _operation_log_2.type = TokenType.IBET_STRAIGHT_BOND
        _operation_log_2.arguments = {"memo": "20230503"}
        _operation_log_2.original_contents = {}
        _operation_log_2.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_2)

        _operation_log_3 = TokenUpdateOperationLog()
        _operation_log_3.created = datetime(2023, 5, 4, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_3.issuer_address = _issuer_address
        _operation_log_3.token_address = _token_address
        _operation_log_3.type = TokenType.IBET_STRAIGHT_BOND
        _operation_log_3.arguments = {"memo": "20230504"}
        _operation_log_3.original_contents = {}
        _operation_log_3.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_3)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "created_from": "2023-05-03 08:00:00",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {},
                    "modified_contents": {"memo": "20230504"},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": "2023-05-04T09:00:00+09:00",
                },
                {
                    "original_contents": {},
                    "modified_contents": {"memo": "20230503"},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": "2023-05-03T09:00:00+09:00",
                },
            ],
        }

    # <Normal_3_4>
    # Search filter: created_to
    @pytest.mark.asyncio
    async def test_normal_3_4(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
            created=datetime(2023, 5, 1, tzinfo=timezone("UTC")).replace(tzinfo=None),
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        _operation_log_1 = TokenUpdateOperationLog()
        _operation_log_1.created = datetime(2023, 5, 2, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_1.issuer_address = _issuer_address
        _operation_log_1.token_address = _token_address
        _operation_log_1.type = TokenType.IBET_STRAIGHT_BOND
        _operation_log_1.arguments = {"memo": "20230502"}
        _operation_log_1.original_contents = {}
        _operation_log_1.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_1)

        _operation_log_2 = TokenUpdateOperationLog()
        _operation_log_2.created = datetime(2023, 5, 3, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_2.issuer_address = _issuer_address
        _operation_log_2.token_address = _token_address
        _operation_log_2.type = TokenType.IBET_STRAIGHT_BOND
        _operation_log_2.arguments = {"memo": "20230503"}
        _operation_log_2.original_contents = {}
        _operation_log_2.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_2)

        _operation_log_3 = TokenUpdateOperationLog()
        _operation_log_3.created = datetime(2023, 5, 4, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_3.issuer_address = _issuer_address
        _operation_log_3.token_address = _token_address
        _operation_log_3.type = TokenType.IBET_STRAIGHT_BOND
        _operation_log_3.arguments = {"memo": "20230504"}
        _operation_log_3.original_contents = {}
        _operation_log_3.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_3)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "created_to": "2023-05-02 00:00:00",
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE,
                    "created": "2023-05-01T09:00:00+09:00",
                },
            ],
        }

    # <Normal_4_1>
    # Sort Order
    @pytest.mark.asyncio
    async def test_normal_4_1(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "sort_order": 0,
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_4_2>
    # Sort Item
    @pytest.mark.asyncio
    async def test_normal_4_2(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "sort_order": 0,
                "sort_item": "operation_category",
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_5_1>
    # Pagination
    @pytest.mark.asyncio
    async def test_normal_5_1(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "limit": 2,
                "offset": 1,
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": 1,
                "limit": 2,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_5_2>
    # Pagination (over offset)
    @pytest.mark.asyncio
    async def test_normal_5_2(
        self,
        async_client: AsyncClient,
        async_db: AsyncSession,
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, _ = await prepare_bond_token_history_fixture(
            async_db,
            _issuer_address,
            TEST_PERSONAL_INFO_CONTRACT_ADDRESS,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.rsa_status = AccountRsaStatus.UNSET.value
        account.is_deleted = False
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_09
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "limit": 1,
                "offset": 4,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": 4,
                "limit": 1,
                "total": 4,
            },
            "history": [],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # query(invalid value)
    @pytest.mark.asyncio
    async def test_error_1(self, async_client: AsyncClient, async_db: AsyncSession):
        token_address = "0x0123456789012345678901234567890123456789"

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address),
            params={
                "operation_category": "test",
                "sort_order": "test",
                "sort_item": "test",
                "offset": "test",
                "limit": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "test",
                },
                {
                    "type": "int_parsing",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "test",
                },
                {
                    "type": "enum",
                    "loc": ["query", "operation_category"],
                    "msg": "Input should be 'Issue' or 'Update'",
                    "input": "test",
                    "ctx": {"expected": "'Issue' or 'Update'"},
                },
                {
                    "type": "enum",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'created' or 'operation_category'",
                    "input": "test",
                    "ctx": {"expected": "'created' or 'operation_category'"},
                },
                {
                    "type": "enum",
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be 0 or 1",
                    "input": "test",
                    "ctx": {"expected": "0 or 1"},
                },
            ],
        }
