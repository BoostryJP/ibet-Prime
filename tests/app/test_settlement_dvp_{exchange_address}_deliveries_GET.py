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

from datetime import UTC, datetime

from app.model.db import (
    DeliveryStatus,
    IDXDelivery,
    IDXPersonalInfo,
    Token,
    TokenType,
    TokenVersion,
)


class TestListAllDVPDeliveries:
    # target API endpoint
    base_url = "/settlement/dvp/{exchange_address}/deliveries"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # 0 record
    def test_normal_1(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            headers={
                "issuer-address": issuer_address,
            },
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
            "deliveries": [],
        }

    # Normal_2_1
    # Multi record
    def test_normal_2_1(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 6, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 1,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
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
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 3,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_CONFIRMED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 4,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "finish_transaction_hash": "tx_hash_4",
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_FINISHED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 5,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "abort_transaction_hash": "tx_hash_5",
                    "confirmed": True,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_ABORTED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 6,
                    "token_address": token_address_2,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_2,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_2,
                    "data": "",
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
                },
            ],
        }

    # Normal_2_2
    # Multi record (PersonalInfo is set)
    def test_normal_2_2(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        db.add(_personal_info)

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
        db.add(_personal_info)

        _personal_info = IDXPersonalInfo()
        _personal_info.account_address = seller_address_2
        _personal_info.issuer_address = "other_issuer_address"  # Other issuer address
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
        db.add(_personal_info)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 6, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
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
                    "data": "",
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
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
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
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 3,
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
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_CONFIRMED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 4,
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
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "finish_transaction_hash": "tx_hash_4",
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_FINISHED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 5,
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
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "abort_transaction_hash": "tx_hash_5",
                    "confirmed": True,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_ABORTED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 6,
                    "token_address": token_address_2,
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
                    "seller_address": seller_address_2,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_2,
                    "data": "",
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
                },
            ],
        }

    # Normal_3_1
    # Search filter: token_address
    def test_normal_3_1(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"token_address": token_address_1},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 1,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
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
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 3,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_CONFIRMED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 4,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "finish_transaction_hash": "tx_hash_4",
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_FINISHED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 5,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "abort_transaction_hash": "tx_hash_5",
                    "confirmed": True,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_ABORTED,
                },
            ],
        }

    # Normal_3_2
    # Search filter: seller_address
    def test_normal_3_2(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"seller_address": seller_address_1},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 1,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
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
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 3,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_CONFIRMED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 4,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "finish_transaction_hash": "tx_hash_4",
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_FINISHED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 5,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "abort_transaction_hash": "tx_hash_5",
                    "confirmed": True,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_ABORTED,
                },
            ],
        }

    # Normal_3_3
    # Search filter: agent_address
    def test_normal_3_3(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"agent_address": agent_address_1},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 5, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 1,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
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
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 3,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_CONFIRMED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 4,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "finish_transaction_hash": "tx_hash_4",
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_FINISHED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 5,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "abort_transaction_hash": "tx_hash_5",
                    "confirmed": True,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_ABORTED,
                },
            ],
        }

    # Normal_3_4
    # Search filter: valid
    def test_normal_3_4(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"valid": False},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 5,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "abort_transaction_hash": "tx_hash_5",
                    "confirmed": True,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_ABORTED,
                },
            ],
        }

    # Normal_3_5
    # Search filter: status
    def test_normal_3_5(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"status": DeliveryStatus.DELIVERY_FINISHED.value},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 4,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "finish_transaction_hash": "tx_hash_4",
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_FINISHED,
                },
            ],
        }

    # Normal_3_6_1
    # Search filter: create_blocktimestamp_from
    def test_normal_3_6_1(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"create_blocktimestamp_from": str(datetime(2024, 1, 1, 9, 0, 1))},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 1,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:01+00:00",
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
                },
            ],
        }

    # Normal_3_6_2
    # Search filter: create_blocktimestamp_to
    def test_normal_3_6_2(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 5)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"create_blocktimestamp_to": str(datetime(2024, 1, 1, 9, 0, 1))},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 1,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
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
                },
            ],
        }

    # Normal_3_6_3
    # Search filter: create_blocktimestamp_from & create_blocktimestamp_to
    def test_normal_3_6_3(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 5)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={
                "create_blocktimestamp_from": str(datetime(2024, 1, 1, 9, 0, 1)),
                "create_blocktimestamp_to": str(datetime(2024, 1, 1, 9, 0, 1)),
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
            ],
        }

    # Normal_4
    # Sort
    def test_normal_4(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"sort_order": 0},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 6, "limit": None, "offset": None, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 1,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
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
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 3,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_CONFIRMED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 4,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": "2023-12-31T15:00:03+00:00",
                    "finish_transaction_hash": "tx_hash_4",
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_FINISHED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 5,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": "2023-12-31T15:00:04+00:00",
                    "abort_transaction_hash": "tx_hash_5",
                    "confirmed": True,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_ABORTED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 6,
                    "token_address": token_address_2,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_2,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_2,
                    "data": "",
                    "create_blocktimestamp": "2024-01-01T15:00:00+00:00",
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
                },
            ],
        }

    # Normal_5
    # Pagination
    def test_normal_5(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        token_address_1 = "0x1234567890123456789012345678900000000010"
        token_address_2 = "0x1234567890123456789012345678900000000020"

        issuer_address = "0x1234567890123456789012345678900000000100"

        seller_address_1 = issuer_address
        seller_address_2 = "0x1234567890123456789012345678900000000200"

        buyer_address = "0x1234567890123456789012345678911111111111"

        agent_address_1 = "0x1234567890123456789012345678900000001000"
        agent_address_2 = "0x1234567890123456789012345678900000002000"

        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_1
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address_2
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

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
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Canceled)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 2
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.cancel_blocktimestamp = datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC)
        _idx_delivery.cancel_transaction_hash = "tx_hash_2"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_CANCELED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Confirmed)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 3
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CONFIRMED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Finished)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 4
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = datetime(2024, 1, 1, 0, 0, 3, tzinfo=UTC)
        _idx_delivery.finish_transaction_hash = "tx_hash_4"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_FINISHED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Aborted)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 5
        _idx_delivery.token_address = token_address_1
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_1
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_1
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirm_blocktimestamp = datetime(2024, 1, 1, 0, 0, 2, tzinfo=UTC)
        _idx_delivery.confirm_transaction_hash = "tx_hash_3"
        _idx_delivery.finish_blocktimestamp = None
        _idx_delivery.finish_transaction_hash = None
        _idx_delivery.abort_blocktimestamp = datetime(2024, 1, 1, 0, 0, 4, tzinfo=UTC)
        _idx_delivery.abort_transaction_hash = "tx_hash_5"
        _idx_delivery.confirmed = True
        _idx_delivery.valid = False
        _idx_delivery.status = DeliveryStatus.DELIVERY_ABORTED.value
        db.add(_idx_delivery)

        # prepare data: IDXDelivery(Created)
        _idx_delivery = IDXDelivery()
        _idx_delivery.exchange_address = exchange_address
        _idx_delivery.delivery_id = 6
        _idx_delivery.token_address = token_address_2
        _idx_delivery.buyer_address = buyer_address
        _idx_delivery.seller_address = seller_address_2
        _idx_delivery.amount = 1
        _idx_delivery.agent_address = agent_address_2
        _idx_delivery.data = ""
        _idx_delivery.create_blocktimestamp = datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        _idx_delivery.create_transaction_hash = "tx_hash_1"
        _idx_delivery.confirmed = False
        _idx_delivery.valid = True
        _idx_delivery.status = DeliveryStatus.DELIVERY_CREATED.value
        db.add(_idx_delivery)
        db.commit()

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={"offset": 2, "limit": 2},
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {"count": 6, "limit": 2, "offset": 2, "total": 6},
            "deliveries": [
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 2,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": "2023-12-31T15:00:01+00:00",
                    "cancel_transaction_hash": "tx_hash_2",
                    "confirm_blocktimestamp": None,
                    "confirm_transaction_hash": None,
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": False,
                    "valid": False,
                    "status": DeliveryStatus.DELIVERY_CANCELED,
                },
                {
                    "exchange_address": exchange_address,
                    "delivery_id": 3,
                    "token_address": token_address_1,
                    "buyer_address": buyer_address,
                    "buyer_personal_information": None,
                    "seller_address": seller_address_1,
                    "seller_personal_information": None,
                    "amount": 1,
                    "agent_address": agent_address_1,
                    "data": "",
                    "create_blocktimestamp": "2023-12-31T15:00:00+00:00",
                    "create_transaction_hash": "tx_hash_1",
                    "cancel_blocktimestamp": None,
                    "cancel_transaction_hash": None,
                    "confirm_blocktimestamp": "2023-12-31T15:00:02+00:00",
                    "confirm_transaction_hash": "tx_hash_3",
                    "finish_blocktimestamp": None,
                    "finish_transaction_hash": None,
                    "abort_blocktimestamp": None,
                    "abort_transaction_hash": None,
                    "confirmed": True,
                    "valid": True,
                    "status": DeliveryStatus.DELIVERY_CONFIRMED,
                },
            ],
        }

    # ###########################################################################
    # # Error Case
    # ###########################################################################

    # Error_1
    # RequestValidationError
    # Missing header
    def test_error_1(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
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
    # RequestValidationError
    # query(invalid value)
    def test_error_2(self, client, db):
        exchange_address = "0x1234567890123456789012345678900000000000"
        issuer_address = "0x1234567890123456789012345678900000000100"

        # request target api
        resp = client.get(
            self.base_url.format(exchange_address=exchange_address),
            params={
                "valid": "invalid_value",
                "status": "invalid_value",
                "crate_blocktimestamp_from": "invalid_value",
                "crate_blocktimestamp_to": "invalid_value",
                "sort_item": "test",
                "offset": "test",
                "limit": "test",
            },
            headers={
                "issuer-address": issuer_address,
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "bool_parsing",
                    "loc": ["query", "valid"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "input": "invalid_value",
                },
                {
                    "type": "enum",
                    "loc": ["query", "status"],
                    "msg": "Input should be 0, 1, 2, 3 or 4",
                    "input": "invalid_value",
                    "ctx": {"expected": "0, 1, 2, 3 or 4"},
                },
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
            ],
        }
