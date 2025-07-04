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
from unittest import mock
from unittest.mock import ANY

import pytest
from eth_keyfile import decode_keyfile_json
from httpx import AsyncClient
from pytz import timezone
from web3 import Web3
from web3.contract import Contract
from web3.middleware import ExtraDataToPOAMiddleware

import config
from app.model.db import (
    Account,
    Token,
    TokenType,
    TokenUpdateOperationCategory,
    TokenUpdateOperationLog,
    TokenVersion,
)
from app.model.ibet import IbetShareContract
from app.model.schema import IbetShareCreate
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import ContractUtils
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


async def deploy_share_token_contract(
    session,
    address,
    private_key,
    personal_info_contract_address,
    tradable_exchange_contract_address=config.ZERO_ADDRESS,
    transfer_approval_required=True,
    created: datetime | None = None,
) -> (Contract, dict):
    arguments = [
        "token.name",
        "token.symbol",
        20,
        100,
        3 * 10000000000000,
        "20230501",
        "20230501",
        "20230501",
        30,
    ]
    share_contract = IbetShareContract()
    token_address, _, _ = await share_contract.create(arguments, address, private_key)

    contract = ContractUtils.get_contract("IbetShare", token_address)
    token_create_param = IbetShareCreate(
        name="token.name",
        symbol="token.symbol",
        issue_price=20,
        total_supply=100,
        dividends=3,
        dividend_record_date="20230501",
        dividend_payment_date="20230501",
        cancellation_date="20230501",
        principal_value=30,
        transferable=False,  # update
        status=True,  # update
        is_offering=True,  # update
        tradable_exchange_contract_address=tradable_exchange_contract_address,  # update
        personal_info_contract_address=personal_info_contract_address,  # update
        require_personal_info_registered=False,  # update
        contact_information="contact info test",  # update
        privacy_policy="privacy policy test",  # update
        transfer_approval_required=transfer_approval_required,  # update
        is_canceled=True,  # update
    ).__dict__

    token_create_param.pop("activate_ibet_wst")

    token_update_operation_log = TokenUpdateOperationLog()
    token_update_operation_log.issuer_address = address
    token_update_operation_log.token_address = token_address
    token_update_operation_log.type = TokenType.IBET_SHARE
    token_update_operation_log.issuer_address = address
    token_update_operation_log.arguments = token_create_param
    token_update_operation_log.original_contents = None
    token_update_operation_log.operation_category = TokenUpdateOperationCategory.ISSUE
    if created:
        token_update_operation_log.created = created.replace(tzinfo=None)
    session.add(token_update_operation_log)

    await session.commit()

    build_tx_param = {
        "chainId": config.CHAIN_ID,
        "from": address,
        "gas": config.TX_GAS_LIMIT,
        "gasPrice": 0,
    }
    tx = contract.functions.setTransferable(
        token_create_param["transferable"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setStatus(token_create_param["status"]).build_transaction(
        build_tx_param
    )
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.changeOfferingStatus(
        token_create_param["is_offering"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setTradableExchange(
        token_create_param["tradable_exchange_contract_address"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setPersonalInfoAddress(
        token_create_param["personal_info_contract_address"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setRequirePersonalInfoRegistered(
        token_create_param["require_personal_info_registered"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setContactInformation(
        token_create_param["contact_information"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setPrivacyPolicy(
        token_create_param["privacy_policy"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setTransferApprovalRequired(
        token_create_param["transfer_approval_required"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.changeToCanceled().build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    return contract, token_create_param


@mock.patch("app.model.ibet.token.TX_GAS_LIMIT", 8000000)
class TestAppRoutersShareTokensTokenAddressHistoryGET:
    # target API endpoint
    base_url = "/share/tokens/{}/history"

    @staticmethod
    async def create_history_by_api(
        async_client: AsyncClient, token_address: str, issuer_address: str
    ):
        await async_client.post(
            f"/share/tokens/{token_address}",
            json={
                "dividends": 1,
                "dividend_record_date": "20230502",
                "dividend_payment_date": "20230502",
                "memo": None,
            },
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )
        await async_client.post(
            f"/share/tokens/{token_address}",
            json={"memo": "." * 10000},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )
        await async_client.post(
            f"/share/tokens/{token_address}",
            json={"is_offering": False, "memo": None},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

    @staticmethod
    def expected_original_after_issue(
        create_token_param: dict, issuer_address: str, token_address: str
    ):
        return {
            **create_token_param,
            "contract_name": "IbetShare",
            "issuer_address": issuer_address,
            "memo": "",
            "token_address": token_address,
        }

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db, ibet_personal_info_contract):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]

        # prepare data: Token
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = "no_record_address"
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
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
    async def test_normal_2(self, async_client, async_db, ibet_personal_info_contract):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
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
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                        **{"memo": "." * 10000},
                    },
                    "modified_contents": {"is_offering": False},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                    },
                    "modified_contents": {"memo": "." * 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {
                        "dividends": 1.0,
                        "dividend_record_date": "20230502",
                        "dividend_payment_date": "20230502",
                    },
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
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
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
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                        **{"memo": "." * 10000},
                    },
                    "modified_contents": {"is_offering": False},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                    },
                    "modified_contents": {"memo": "." * 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {
                        "dividends": 1.0,
                        "dividend_record_date": "20230502",
                        "dividend_payment_date": "20230502",
                    },
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_2>
    # Search filter: modified_contents
    @pytest.mark.asyncio
    async def test_normal_3_2(
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # create history
        await self.create_history_by_api(async_client, _token_address, _issuer_address)

        # request target API
        resp = await async_client.get(
            self.base_url.format(_token_address),
            params={
                "modified_contents": "is_offering",
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
                    "original_contents": {
                        **original_after_issue,
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                        **{"memo": "." * 10000},
                    },
                    "modified_contents": {"is_offering": False},
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
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, _ = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
            created=datetime(2023, 5, 1, tzinfo=timezone("UTC")),
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _operation_log_1 = TokenUpdateOperationLog()
        _operation_log_1.created = datetime(2023, 5, 2, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_1.issuer_address = _issuer_address
        _operation_log_1.token_address = _token_address
        _operation_log_1.type = TokenType.IBET_SHARE
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
        _operation_log_2.type = TokenType.IBET_SHARE
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
        _operation_log_3.type = TokenType.IBET_SHARE
        _operation_log_3.arguments = {"memo": "20230504"}
        _operation_log_3.original_contents = {}
        _operation_log_3.status = 1
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
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
            created=datetime(2023, 5, 1, tzinfo=timezone("UTC")),
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        _operation_log_1 = TokenUpdateOperationLog()
        _operation_log_1.created = datetime(2023, 5, 2, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_1.issuer_address = _issuer_address
        _operation_log_1.token_address = _token_address
        _operation_log_1.type = TokenType.IBET_SHARE
        _operation_log_1.arguments = {"memo": "20230502"}
        _operation_log_1.original_contents = {}
        _operation_log_1.status = 1
        _operation_log_1.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_1)

        _operation_log_2 = TokenUpdateOperationLog()
        _operation_log_2.created = datetime(2023, 5, 3, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_2.issuer_address = _issuer_address
        _operation_log_2.token_address = _token_address
        _operation_log_2.type = TokenType.IBET_SHARE
        _operation_log_2.arguments = {"memo": "20230503"}
        _operation_log_2.original_contents = {}
        _operation_log_2.status = 1
        _operation_log_2.operation_category = TokenUpdateOperationCategory.UPDATE
        async_db.add(_operation_log_2)

        _operation_log_3 = TokenUpdateOperationLog()
        _operation_log_3.created = datetime(2023, 5, 4, tzinfo=timezone("UTC")).replace(
            tzinfo=None
        )
        _operation_log_3.issuer_address = _issuer_address
        _operation_log_3.token_address = _token_address
        _operation_log_3.type = TokenType.IBET_SHARE
        _operation_log_3.arguments = {"memo": "20230504"}
        _operation_log_3.original_contents = {}
        _operation_log_3.status = 1
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
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
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
                    "modified_contents": {
                        "dividends": 1.0,
                        "dividend_record_date": "20230502",
                        "dividend_payment_date": "20230502",
                    },
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                    },
                    "modified_contents": {"memo": "." * 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                        **{"memo": "." * 10000},
                    },
                    "modified_contents": {"is_offering": False},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_4_2>
    # Sort Item
    @pytest.mark.asyncio
    async def test_normal_4_2(
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
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
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                        **{"memo": "." * 10000},
                    },
                    "modified_contents": {"is_offering": False},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                    },
                    "modified_contents": {"memo": "." * 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {
                        "dividends": 1.0,
                        "dividend_record_date": "20230502",
                        "dividend_payment_date": "20230502",
                    },
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_5_1>
    # Pagination
    @pytest.mark.asyncio
    async def test_normal_5_1(
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
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
                        **{
                            "dividends": 1.0,
                            "dividend_record_date": "20230502",
                            "dividend_payment_date": "20230502",
                        },
                    },
                    "modified_contents": {"memo": "." * 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {
                        "dividends": 1.0,
                        "dividend_record_date": "20230502",
                        "dividend_payment_date": "20230502",
                    },
                    "operation_category": TokenUpdateOperationCategory.UPDATE,
                    "created": ANY,
                },
            ],
        }

    # <Normal_5_2>
    # Pagination (over offset)
    @pytest.mark.asyncio
    async def test_normal_5_2(
        self, async_client, async_db, ibet_personal_info_contract
    ):
        test_account = default_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, _ = await deploy_share_token_contract(
            async_db,
            _issuer_address,
            issuer_private_key,
            ibet_personal_info_contract.address,
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        async_db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = ""
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
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
    async def test_error_1(self, async_client, async_db):
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
