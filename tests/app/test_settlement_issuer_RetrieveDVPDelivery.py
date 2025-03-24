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

import json
from datetime import UTC, datetime

import pytest

from app.model.db import (
    DeliveryStatus,
    IDXDelivery,
    IDXPersonalInfo,
    PersonalInfoDataSource,
    Token,
    TokenType,
    TokenVersion,
)
from tests.account_config import config_eth_account


class TestRetrieveDVPDelivery:
    # target API endpoint
    base_url = "/settlement/dvp/{exchange_address}/delivery/{delivery_id}"

    account_list = [
        {"address": config_eth_account("user1")["address"], "amount": 1},
        {"address": config_eth_account("user2")["address"], "amount": 2},
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1_1
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info = IDXPersonalInfo()
        _personal_info.account_address = buyer_address
        _personal_info.issuer_address = issuer_address
        _personal_info._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info)

        _personal_info = IDXPersonalInfo()
        _personal_info.account_address = seller_address_1
        _personal_info.issuer_address = issuer_address
        _personal_info._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 1
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = json.dumps(
            {
                "delivery_type": "offering",
                "trade_date": "20240820",
                "settlement_date": "20240820",
                "settlement_service_account_id": "test_account",
                "value": 1,
            }
        )
        _idx_delivery.settlement_service_type = "test_service_type"
        _idx_delivery.create_blocktimestamp = datetime(
            2024, 1, 1, 0, 0, 0, tzinfo=UTC
        ).replace(tzinfo=None)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        async_db.add(_idx_delivery)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(exchange_address=exchange_address, delivery_id=1),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "exchange_address": exchange_address,
            "delivery_id": 1,
            "token_address": token_address_1,
            "buyer_address": buyer_address,
            "buyer_personal_information": {
                "key_manager": "key_manager_test1",
                "name": "name_test1",
                "postal_code": "postal_code_test1",
                "address": "address_test1",
                "email": "email_test1",
                "birth": "birth_test1",
                "is_corporate": False,
                "tax_category": 10,
            },
            "seller_address": seller_address_1,
            "seller_personal_information": {
                "key_manager": "key_manager_test2",
                "name": "name_test2",
                "postal_code": "postal_code_test2",
                "address": "address_test2",
                "email": "email_test2",
                "birth": "birth_test2",
                "is_corporate": False,
                "tax_category": 10,
            },
            "amount": 1,
            "agent_address": agent_address_1,
            "data": {
                "delivery_type": "offering",
                "trade_date": "20240820",
                "settlement_date": "20240820",
                "settlement_service_account_id": "test_account",
                "value": 1,
            },
            "settlement_service_type": "test_service_type",
            "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
            "create_transaction_hash": "tx_hash_1",
            "cancel_blocktimestamp": None,
            "cancel_transaction_hash": None,
            "confirm_blocktimestamp": None,
            "confirm_transaction_hash": None,
            "finish_blocktimestamp": None,
            "finish_transaction_hash": None,
            "abort_blocktimestamp": None,
            "abort_transaction_hash": None,
            "confirmed": False,
            "valid": True,
            "status": DeliveryStatus.DELIVERY_CREATED,
        }

    # Normal_1_2 (PersonalInfo is not set)
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _personal_info = IDXPersonalInfo()
        _personal_info.account_address = buyer_address
        _personal_info.issuer_address = "other_issuer_address"  # Other issuer
        _personal_info._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info)

        _personal_info = IDXPersonalInfo()
        _personal_info.account_address = seller_address_1
        _personal_info.issuer_address = "other_issuer_address"  # Other issuer
        _personal_info._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_personal_info)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 1
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.settlement_service_type = None
        _idx_delivery.create_blocktimestamp = datetime(
            2024, 1, 1, 0, 0, 0, tzinfo=UTC
        ).replace(tzinfo=None)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        async_db.add(_idx_delivery)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(exchange_address=exchange_address, delivery_id=1),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "exchange_address": exchange_address,
            "delivery_id": 1,
            "token_address": token_address_1,
            "buyer_address": buyer_address,
            "buyer_personal_information": None,
            "seller_address": seller_address_1,
            "seller_personal_information": None,
            "amount": 1,
            "agent_address": agent_address_1,
            "data": None,
            "settlement_service_type": None,
            "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
            "create_transaction_hash": "tx_hash_1",
            "cancel_blocktimestamp": None,
            "cancel_transaction_hash": None,
            "confirm_blocktimestamp": None,
            "confirm_transaction_hash": None,
            "finish_blocktimestamp": None,
            "finish_transaction_hash": None,
            "abort_blocktimestamp": None,
            "abort_transaction_hash": None,
            "confirmed": False,
            "valid": True,
            "status": DeliveryStatus.DELIVERY_CREATED,
        }

    #########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # RequestValidationError
    # Missing header
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        exchange_address = "0x1234567890123456789012345678900000000000"

        # request target API
        resp = await async_client.get(
            self.base_url.format(exchange_address=exchange_address, delivery_id=1),
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "input": None,
                }
            ],
        }

    # Error_2
    # NotFound
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # request target API
        resp = await async_client.get(
            self.base_url.format(exchange_address=exchange_address, delivery_id=1),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "delivery not found",
        }
