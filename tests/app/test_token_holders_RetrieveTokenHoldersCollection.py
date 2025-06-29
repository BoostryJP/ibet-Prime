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

import uuid
from unittest import mock

import pytest
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import config
from app.model.db import (
    IDXPersonalInfo,
    PersonalInfoDataSource,
    Token,
    TokenHolder,
    TokenHolderBatchStatus,
    TokenHoldersList,
    TokenType,
    TokenVersion,
)
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestAppRoutersHoldersTokenAddressCollectionIdGET:
    # target API endpoint
    base_url = "/token/holders/{token_address}/collection/{list_id}"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # Holders in response is empty.
    @pytest.mark.asyncio
    async def test_normal_1(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_collection = TokenHoldersList()
        _token_holders_collection.list_id = list_id
        _token_holders_collection.token_address = token_address
        _token_holders_collection.block_number = 100
        _token_holders_collection.batch_status = TokenHolderBatchStatus.DONE

        async_db.add(_token_holders_collection)

        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "status": TokenHolderBatchStatus.DONE,
            "holders": [],
        }

    # Normal_2
    # Holders in response is filled.
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": {
                        "key_manager": None,
                        "name": None,
                        "email": None,
                        "birth": None,
                        "address": None,
                        "is_corporate": None,
                        "postal_code": None,
                        "tax_category": None,
                    },
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_1_1
    # Search filter: hold balance & "="
    @pytest.mark.asyncio
    async def test_normal_3_1_1(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "hold_balance": 10000,
                "hold_balance_operator": 0,
            },
        )
        holders = [holders[0]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_1_2
    # Search filter: hold balance & ">="
    @pytest.mark.asyncio
    async def test_normal_3_1_2(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "hold_balance": 20000,
                "hold_balance_operator": 1,
            },
        )
        holders = [holders[1], holders[2]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_1_3
    # Search filter: hold balance & "<="
    @pytest.mark.asyncio
    async def test_normal_3_1_3(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "hold_balance": 10000,
                "hold_balance_operator": 2,
            },
        )
        holders = [holders[0]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_2_1
    # Search filter: locked balance & "="
    @pytest.mark.asyncio
    async def test_normal_3_2_1(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "locked_balance": 20000,
                "locked_balance_operator": 0,
            },
        )
        holders = [holders[0]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_2_2
    # Search filter: locked balance & ">="
    @pytest.mark.asyncio
    async def test_normal_3_2_2(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "locked_balance": 40000,
                "locked_balance_operator": 1,
            },
        )
        holders = [holders[1], holders[2]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_2_3
    # Search filter: locked balance & "<="
    @pytest.mark.asyncio
    async def test_normal_3_2_3(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "locked_balance": 20000,
                "locked_balance_operator": 2,
            },
        )
        holders = [holders[0]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_3
    # Search filter: key_manager
    @pytest.mark.asyncio
    async def test_normal_3_3(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "key_manager": "_1",
            },
        )
        holders = [holders[0]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_4
    # Search filter: tax_category
    @pytest.mark.asyncio
    async def test_normal_3_4(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={"tax_category": 1},
        )
        holders = [holders[0]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_3_5
    # Search filter: account_address
    @pytest.mark.asyncio
    async def test_normal_3_5(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={
                "account_address": default_eth_account("user2")["address"],
            },
        )
        holders = [holders[0]]
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_4
    # Sort
    @pytest.mark.parametrize(
        "sort_item",
        [
            "account_address",
            "hold_balance",
            "locked_balance",
            "key_manager",
            "tax_category",
        ],
    )
    @pytest.mark.asyncio
    async def test_normal_4(self, sort_item, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            _personal_info = IDXPersonalInfo()
            _personal_info.issuer_address = issuer_address
            _personal_info.account_address = default_eth_account(user)["address"]
            _personal_info._personal_info = {
                "key_manager": f"key_manager_{str(i + 1)}",
                "name": f"name_{str(i + 1)}",
                "postal_code": f"{str(i + 1)}",
                "address": f"{str(i + 1)}",
                "email": f"{str(i + 1)}",
                "birth": f"{str(i + 1)}",
                "is_corporate": True,
                "tax_category": i + 1,
            }
            _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
            async_db.add(_personal_info)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": _personal_info.personal_info,
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={"sort_item": sort_item},
        )
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": sorted_holders,
        }

    # Normal_5
    # Pagination
    @pytest.mark.asyncio
    async def test_normal_5(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)
        await async_db.commit()

        holders = []
        for i, user in enumerate(["user2", "user3", "user4"]):
            _token_holder = TokenHolder()
            _token_holder.holder_list_id = _token_holders_list.id
            _token_holder.account_address = default_eth_account(user)["address"]
            _token_holder.hold_balance = 10000 * (i + 1)
            _token_holder.locked_balance = 20000 * (i + 1)
            async_db.add(_token_holder)
            holders.append(
                {
                    **_token_holder.json(),
                    "personal_information": {
                        "key_manager": None,
                        "name": None,
                        "email": None,
                        "birth": None,
                        "address": None,
                        "is_corporate": None,
                        "postal_code": None,
                        "tax_category": None,
                    },
                }
            )
        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
            params={"offset": 1, "limit": 1},
        )
        sorted_holders = sorted(holders, key=lambda x: x["account_address"])

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "status": TokenHolderBatchStatus.DONE,
            "holders": [sorted_holders[1]],
        }

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 404: Not Found Error
    # Invalid contract address
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # issue token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"
        list_id = str(uuid.uuid4())

        # request target api with not_listed contract_address
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }

    # Error_2
    # 400: Invalid Parameter Error
    # Token is pending
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # issue token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        # set status pending
        _token.token_status = 0
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)

        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }

    # Error_3
    # 400: Invalid Parameter Error
    # Invalid list_id
    @pytest.mark.asyncio
    async def test_error_3(self, async_client, async_db):
        # issue token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)

        await async_db.commit()

        # request target api with invalid list_id
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id="some_id"),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "list_id must be UUIDv4.",
        }

    # Error_4
    # 404: Not Found Error
    # There is no holder list record with given list_id.
    @pytest.mark.asyncio
    async def test_error_4(self, async_client, async_db):
        # issue token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        list_id = str(uuid.uuid4())

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "list not found",
        }

    # Error_5
    # 400: Invalid Parameter Error
    # Invalid contract address and list id combi.
    @pytest.mark.asyncio
    async def test_error_5(self, async_client, async_db):
        # issue token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address1 = "0xABCdeF1234567890abcdEf123456789000000000"
        token_address2 = "0x000000000987654321fEdcba0987654321FedCBA"

        # prepare data
        _token1 = Token()
        _token1.type = TokenType.IBET_STRAIGHT_BOND
        _token1.tx_hash = ""
        _token1.issuer_address = issuer_address
        _token1.token_address = token_address1
        _token1.abi = {}
        _token1.version = TokenVersion.V_25_06
        async_db.add(_token1)

        _token2 = Token()
        _token2.type = TokenType.IBET_STRAIGHT_BOND
        _token2.tx_hash = ""
        _token2.issuer_address = issuer_address
        _token2.token_address = token_address2
        _token2.abi = {}
        _token2.version = TokenVersion.V_25_06
        async_db.add(_token2)

        list_id = str(uuid.uuid4())
        _token_holders_list = TokenHoldersList()
        _token_holders_list.list_id = list_id
        _token_holders_list.token_address = token_address1
        _token_holders_list.block_number = 100
        _token_holders_list.batch_status = TokenHolderBatchStatus.DONE
        async_db.add(_token_holders_list)

        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address2, list_id=list_id),
            headers={"issuer-address": issuer_address},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": f"list_id: {list_id} is not related to token_address: {token_address2}",
        }

    # Error_6
    # 422: Request Validation Error
    # Issuer-address in request header is not set.
    @mock.patch("web3.eth.Eth.block_number", 100)
    @pytest.mark.asyncio
    async def test_error_6(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        list_id = str(uuid.uuid4())
        _token_holders_collection = TokenHoldersList()
        _token_holders_collection.list_id = list_id
        _token_holders_collection.token_address = token_address
        _token_holders_collection.block_number = 100
        _token_holders_collection.batch_status = TokenHolderBatchStatus.DONE

        async_db.add(_token_holders_collection)

        await async_db.commit()

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id=list_id)
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # Error_7
    # 422: Request Validation Error
    # offset/limit: Input should be greater than or equal to 0
    @pytest.mark.asyncio
    async def test_error_7(self, async_client, async_db):
        # Issue Token
        user = default_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # request target api
        resp = await async_client.get(
            self.base_url.format(token_address=token_address, list_id="some_list_id"),
            headers={"issuer-address": issuer_address},
            params={"offset": -1, "limit": -1},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "greater_than_equal",
                    "loc": ["query", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": "-1",
                    "ctx": {"ge": 0},
                },
                {
                    "type": "greater_than_equal",
                    "loc": ["query", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "input": "-1",
                    "ctx": {"ge": 0},
                },
            ],
        }
