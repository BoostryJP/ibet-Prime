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

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
)
from app.model.db import (
    UTXO,
    IDXPersonalInfo,
    Ledger,
    LedgerCreationRequest,
    LedgerCreationRequestData,
    LedgerCreationStatus,
    LedgerDataType,
    LedgerDetailsData,
    LedgerDetailsTemplate,
    LedgerTemplate,
    Notification,
    NotificationType,
    PersonalInfoDataSource,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils import ledger_utils
from config import WEB3_HTTP_PROVIDER
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


async def deploy_bond_token_contract(
    issuer_address: str,
    issuer_private_key: bytes,
):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        "JPY",
        "token.redemption_date",
        30,
        "JPY",
        "token.return_date",
        "token.return_amount",
        "token.purpose",
    ]
    bond_contrat = IbetStraightBondContract()
    contract_address, _, _ = await bond_contrat.create(
        arguments, issuer_address, issuer_private_key
    )
    return contract_address


async def deploy_share_token_contract(
    issuer_address: str,
    issuer_private_key: bytes,
):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        3,
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        200,
    ]
    share_contract = IbetShareContract()
    contract_address, _, _ = await share_contract.create(
        arguments, issuer_address, issuer_private_key
    )
    return contract_address


@pytest.mark.asyncio
class TestRequestLedgerCreation:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # No token information
    # -> skip
    async def test_normal_1_1(self, async_db):
        # Execute
        await ledger_utils.request_ledger_creation(async_db, "invalid_address")
        await async_db.commit()

        # Assertion
        assert len((await async_db.scalars(select(LedgerCreationRequest))).all()) == 0

    # <Normal_1_2>
    # Only IBET_STRAIGHT_BOND/IBET_SHARE can be used as token.type
    # -> skip
    async def test_normal_1_2(self, async_db):
        token_address_1 = "test_token_address"

        # Prepare data
        _token_1 = Token()
        _token_1.type = "invalid_token_type"
        _token_1.tx_hash = ""
        _token_1.issuer_address = "test_issuer_address"
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)
        await async_db.commit()

        # Execute
        await ledger_utils.request_ledger_creation(async_db, token_address_1)
        await async_db.commit()

        # Assertion
        assert len((await async_db.scalars(select(LedgerCreationRequest))).all()) == 0

    # <Normal_2>
    # Ledger template is not set
    # -> skip
    async def test_normal_2(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data
        token_address_1 = await deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)
        await async_db.commit()

        # Execute
        await ledger_utils.request_ledger_creation(async_db, token_address_1)
        await async_db.commit()

        # Assertion
        assert len((await async_db.scalars(select(LedgerCreationRequest))).all()) == 0

    # <Normal_3>
    # Request ledger creation
    # - Ledger details template is not set
    async def test_normal_3(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data: Token
        token_address_1 = await deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)

        # Prepare data: LedgerTemplate
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "テスト項目1": "テスト値1",
                "テスト項目2": {
                    "テスト項目A": "テスト値2A",
                    "テスト項目B": "テスト値2B",
                },
                "テスト項目3": {
                    "テスト項目A": {"テスト項目a": "テスト値3Aa"},
                    "テスト項目B": "テスト値3B",
                },
            },
        ]
        _template.token_name = "受益権テスト"
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-テスト項目1": "f-テスト値1",
                "f-テスト項目2": {
                    "f-テスト項目A": "f-テスト値2A",
                    "f-テスト項目B": "f-テスト値2B",
                },
                "f-テスト項目3": {
                    "f-テスト項目A": {"f-テスト項目a": "f-テスト値3Aa"},
                    "f-テスト項目B": "f-テスト値3B",
                },
            },
        ]
        async_db.add(_template)

        await async_db.commit()

        # Execute
        await ledger_utils.request_ledger_creation(async_db, token_address_1)
        await async_db.commit()

        # Assertion
        ledger_req = (await async_db.scalars(select(LedgerCreationRequest))).all()
        assert len(ledger_req) == 1
        assert ledger_req[0].request_id is not None
        assert ledger_req[0].token_type == TokenType.IBET_SHARE
        assert ledger_req[0].token_address == token_address_1
        assert ledger_req[0].status == LedgerCreationStatus.PROCESSING

        ledger_req_data = (
            await async_db.scalars(select(LedgerCreationRequestData))
        ).all()
        assert len(ledger_req_data) == 0

    # <Normal_4_1>
    # Successfully request ledger creation
    # - Create dataset from DB (off-chain data)
    async def test_normal_4_1(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )

        # Prepare data: Token
        token_address_1 = await deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)

        # Prepare data: LedgerTemplate
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "テスト項目1": "テスト値1",
                "テスト項目2": {
                    "テスト項目A": "テスト値2A",
                    "テスト項目B": "テスト値2B",
                },
                "テスト項目3": {
                    "テスト項目A": {"テスト項目a": "テスト値3Aa"},
                    "テスト項目B": "テスト値3B",
                },
            },
        ]
        _template.token_name = "受益権テスト"
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-テスト項目1": "f-テスト値1",
                "f-テスト項目2": {
                    "f-テスト項目A": "f-テスト値2A",
                    "f-テスト項目B": "f-テスト値2B",
                },
                "f-テスト項目3": {
                    "f-テスト項目A": {"f-テスト項目a": "f-テスト値3Aa"},
                    "f-テスト項目B": "f-テスト値3B",
                },
            },
        ]
        async_db.add(_template)

        # Prepare data: LedgerDetailsData
        _details_data_1 = LedgerDetailsData()
        _details_data_1.token_address = token_address_1
        _details_data_1.data_id = "data_id_1"
        _details_data_1.name = "test_data_name_1"
        _details_data_1.address = "test_data_address_1"
        _details_data_1.amount = 100
        _details_data_1.price = 200
        _details_data_1.balance = 20000
        _details_data_1.acquisition_date = "2022/03/03"
        async_db.add(_details_data_1)

        _details_data_2 = LedgerDetailsData()
        _details_data_2.token_address = token_address_1
        _details_data_2.data_id = "data_id_1"
        _details_data_2.name = "test_data_name_2"
        _details_data_2.address = "test_data_address_2"
        _details_data_2.amount = 30
        _details_data_2.price = 40
        _details_data_2.balance = 1200
        _details_data_2.acquisition_date = "2022/12/03"
        async_db.add(_details_data_2)

        # Prepare data: LedgerDetailsTemplate
        _details_template = LedgerDetailsTemplate()
        _details_template.token_address = token_address_1
        _details_template.token_detail_type = "劣後受益権"
        _details_template.data_type = LedgerDataType.DB
        _details_template.data_source = "data_id_1"
        async_db.add(_details_template)

        await async_db.commit()

        # Execute
        await ledger_utils.request_ledger_creation(async_db, token_address_1)
        await async_db.commit()

        # Assertion
        ledger_req = (await async_db.scalars(select(LedgerCreationRequest))).all()
        assert len(ledger_req) == 1
        assert ledger_req[0].request_id is not None
        assert ledger_req[0].token_type == TokenType.IBET_SHARE
        assert ledger_req[0].token_address == token_address_1
        assert ledger_req[0].status == LedgerCreationStatus.PROCESSING

        ledger_req_data = (
            await async_db.scalars(select(LedgerCreationRequestData))
        ).all()
        assert len(ledger_req_data) == 2

        assert ledger_req_data[0].request_id == ledger_req[0].request_id
        assert ledger_req_data[0].data_type == LedgerDataType.DB
        assert ledger_req_data[0].account_address == ""
        assert ledger_req_data[0].acquisition_date == "2022/03/03"
        assert ledger_req_data[0].name == "test_data_name_1"
        assert ledger_req_data[0].address == "test_data_address_1"
        assert ledger_req_data[0].amount == 100
        assert ledger_req_data[0].price == 200
        assert ledger_req_data[0].balance == 20000

        assert ledger_req_data[1].request_id == ledger_req[0].request_id
        assert ledger_req_data[1].data_type == LedgerDataType.DB
        assert ledger_req_data[1].account_address == ""
        assert ledger_req_data[1].acquisition_date == "2022/12/03"
        assert ledger_req_data[1].name == "test_data_name_2"
        assert ledger_req_data[1].address == "test_data_address_2"
        assert ledger_req_data[1].amount == 30
        assert ledger_req_data[1].price == 40
        assert ledger_req_data[1].balance == 1200

    # <Normal_4_2_1>
    # Successfully request ledger creation
    # - Create dataset from ibet for Fin (on-chain data)
    # - token_type == TokenType.IBET_SHARE
    async def test_normal_4_2_1(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )
        user_1 = config_eth_account("user2")
        user_address_1 = user_1["address"]

        user_2 = config_eth_account("user3")
        user_address_2 = user_2["address"]

        # Prepare data: Token
        token_address_1 = await deploy_share_token_contract(
            issuer_address,
            issuer_private_key,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)

        # Prepare data: LedgerTemplate
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "テスト項目1": "テスト値1",
                "テスト項目2": {
                    "テスト項目A": "テスト値2A",
                    "テスト項目B": "テスト値2B",
                },
                "テスト項目3": {
                    "テスト項目A": {"テスト項目a": "テスト値3Aa"},
                    "テスト項目B": "テスト値3B",
                },
            },
        ]
        _template.token_name = "受益権テスト"
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-テスト項目1": "f-テスト値1",
                "f-テスト項目2": {
                    "f-テスト項目A": "f-テスト値2A",
                    "f-テスト項目B": "f-テスト値2B",
                },
                "f-テスト項目3": {
                    "f-テスト項目A": {"f-テスト項目a": "f-テスト値3Aa"},
                    "f-テスト項目B": "f-テスト値3B",
                },
            },
        ]
        async_db.add(_template)

        # Prepare data: UTXO
        # - user_1: "2022/01/01" = 100 + 10, "2022/01/02" = 30 + 40
        # - user_2: "2022/01/01" = 200 + 20, "2022/01/02" = 40 + 2
        # - issuer: "2022/01/01" = 300
        _utxo_1 = UTXO()
        _utxo_1.transaction_hash = "tx1"
        _utxo_1.account_address = user_address_1
        _utxo_1.token_address = token_address_1
        _utxo_1.amount = 100
        _utxo_1.block_number = 1
        _utxo_1.block_timestamp = datetime.strptime(
            "2021/12/31 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_1)

        _utxo_2 = UTXO()
        _utxo_2.transaction_hash = "tx2"
        _utxo_2.account_address = user_address_1
        _utxo_2.token_address = token_address_1
        _utxo_2.amount = 10
        _utxo_2.block_number = 2
        _utxo_2.block_timestamp = datetime.strptime(
            "2022/01/01 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_2)

        _utxo_3 = UTXO()
        _utxo_3.transaction_hash = "tx3"
        _utxo_3.account_address = user_address_1
        _utxo_3.token_address = token_address_1
        _utxo_3.amount = 30
        _utxo_3.block_number = 3
        _utxo_3.block_timestamp = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_3)

        _utxo_4 = UTXO()
        _utxo_4.transaction_hash = "tx4"
        _utxo_4.account_address = user_address_1
        _utxo_4.token_address = token_address_1
        _utxo_4.amount = 40
        _utxo_4.block_number = 4
        _utxo_4.block_timestamp = datetime.strptime(
            "2022/01/02 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_4)

        _utxo_5 = UTXO()
        _utxo_5.transaction_hash = "tx5"
        _utxo_5.account_address = user_address_2
        _utxo_5.token_address = token_address_1
        _utxo_5.amount = 200
        _utxo_5.block_number = 5
        _utxo_5.block_timestamp = datetime.strptime(
            "2021/12/31 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_5)

        _utxo_6 = UTXO()
        _utxo_6.transaction_hash = "tx6"
        _utxo_6.account_address = user_address_2
        _utxo_6.token_address = token_address_1
        _utxo_6.amount = 20
        _utxo_6.block_number = 6
        _utxo_6.block_timestamp = datetime.strptime(
            "2022/01/01 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_6)

        _utxo_7 = UTXO()
        _utxo_7.transaction_hash = "tx7"
        _utxo_7.account_address = user_address_2
        _utxo_7.token_address = token_address_1
        _utxo_7.amount = 40
        _utxo_7.block_number = 7
        _utxo_7.block_timestamp = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_7)

        _utxo_8 = UTXO()
        _utxo_8.transaction_hash = "tx8"
        _utxo_8.account_address = user_address_2
        _utxo_8.token_address = token_address_1
        _utxo_8.amount = 2
        _utxo_8.block_number = 8
        _utxo_8.block_timestamp = datetime.strptime(
            "2022/01/02 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_8)

        _utxo_9 = UTXO()
        _utxo_9.transaction_hash = "tx9"
        _utxo_9.account_address = issuer_address
        _utxo_9.token_address = token_address_1
        _utxo_9.amount = 300
        _utxo_9.block_number = 9
        _utxo_9.block_timestamp = datetime.strptime(
            "2021/12/31 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_9)

        # Prepare data: LedgerDetailsTemplate
        _details_template = LedgerDetailsTemplate()
        _details_template.token_address = token_address_1
        _details_template.token_detail_type = "劣後受益権"
        _details_template.data_type = LedgerDataType.IBET_FIN
        _details_template.data_source = "data_id_1"
        async_db.add(_details_template)

        await async_db.commit()

        # Execute
        await ledger_utils.request_ledger_creation(async_db, token_address_1)
        await async_db.commit()

        # Assertion
        ledger_req = (await async_db.scalars(select(LedgerCreationRequest))).all()
        assert len(ledger_req) == 1
        assert ledger_req[0].request_id is not None
        assert ledger_req[0].token_type == TokenType.IBET_SHARE
        assert ledger_req[0].token_address == token_address_1
        assert ledger_req[0].status == LedgerCreationStatus.PROCESSING

        ledger_req_data = (
            await async_db.scalars(select(LedgerCreationRequestData))
        ).all()
        assert len(ledger_req_data) == 5

        assert ledger_req_data[0].request_id == ledger_req[0].request_id
        assert ledger_req_data[0].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[0].account_address == user_address_1
        assert ledger_req_data[0].acquisition_date == "2022/01/01"
        assert ledger_req_data[0].name is None
        assert ledger_req_data[0].address is None
        assert ledger_req_data[0].amount == 110
        assert ledger_req_data[0].price == 200
        assert ledger_req_data[0].balance == 22000

        assert ledger_req_data[1].request_id == ledger_req[0].request_id
        assert ledger_req_data[1].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[1].account_address == user_address_1
        assert ledger_req_data[1].acquisition_date == "2022/01/02"
        assert ledger_req_data[1].name is None
        assert ledger_req_data[1].address is None
        assert ledger_req_data[1].amount == 70
        assert ledger_req_data[1].price == 200
        assert ledger_req_data[1].balance == 14000

        assert ledger_req_data[2].request_id == ledger_req[0].request_id
        assert ledger_req_data[2].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[2].account_address == user_address_2
        assert ledger_req_data[2].acquisition_date == "2022/01/01"
        assert ledger_req_data[2].name is None
        assert ledger_req_data[2].address is None
        assert ledger_req_data[2].amount == 220
        assert ledger_req_data[2].price == 200
        assert ledger_req_data[2].balance == 44000

        assert ledger_req_data[3].request_id == ledger_req[0].request_id
        assert ledger_req_data[3].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[3].account_address == user_address_2
        assert ledger_req_data[3].acquisition_date == "2022/01/02"
        assert ledger_req_data[3].name is None
        assert ledger_req_data[3].address is None
        assert ledger_req_data[3].amount == 42
        assert ledger_req_data[3].price == 200
        assert ledger_req_data[3].balance == 8400

        assert ledger_req_data[4].request_id == ledger_req[0].request_id
        assert ledger_req_data[4].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[4].account_address == issuer_address
        assert ledger_req_data[4].acquisition_date == "2022/01/01"
        assert ledger_req_data[4].name is None
        assert ledger_req_data[4].address is None
        assert ledger_req_data[4].amount == 300
        assert ledger_req_data[4].price == 200
        assert ledger_req_data[4].balance == 60000

    # <Normal_4_2_2>
    # Successfully request ledger creation
    # - Create dataset from ibet for Fin (on-chain data)
    # - token_type == TokenType.IBET_STRAIGHT_BOND
    async def test_normal_4_2_2(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"], password="password".encode("utf-8")
        )
        user_1 = config_eth_account("user2")
        user_address_1 = user_1["address"]

        user_2 = config_eth_account("user3")
        user_address_2 = user_2["address"]

        # Prepare data: Token
        token_address_1 = await deploy_bond_token_contract(
            issuer_address,
            issuer_private_key,
        )
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)

        # Prepare data: LedgerTemplate
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "テスト項目1": "テスト値1",
                "テスト項目2": {
                    "テスト項目A": "テスト値2A",
                    "テスト項目B": "テスト値2B",
                },
                "テスト項目3": {
                    "テスト項目A": {"テスト項目a": "テスト値3Aa"},
                    "テスト項目B": "テスト値3B",
                },
            },
        ]
        _template.token_name = "受益権テスト"
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-テスト項目1": "f-テスト値1",
                "f-テスト項目2": {
                    "f-テスト項目A": "f-テスト値2A",
                    "f-テスト項目B": "f-テスト値2B",
                },
                "f-テスト項目3": {
                    "f-テスト項目A": {"f-テスト項目a": "f-テスト値3Aa"},
                    "f-テスト項目B": "f-テスト値3B",
                },
            },
        ]
        async_db.add(_template)

        # Prepare data: UTXO
        # - user_1: "2022/01/01" = 100 + 10, "2022/01/02" = 30 + 40
        # - user_2: "2022/01/01" = 200 + 20, "2022/01/02" = 40 + 2
        # - issuer: "2022/01/01" = 300
        _utxo_1 = UTXO()
        _utxo_1.transaction_hash = "tx1"
        _utxo_1.account_address = user_address_1
        _utxo_1.token_address = token_address_1
        _utxo_1.amount = 100
        _utxo_1.block_number = 1
        _utxo_1.block_timestamp = datetime.strptime(
            "2021/12/31 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_1)

        _utxo_2 = UTXO()
        _utxo_2.transaction_hash = "tx2"
        _utxo_2.account_address = user_address_1
        _utxo_2.token_address = token_address_1
        _utxo_2.amount = 10
        _utxo_2.block_number = 2
        _utxo_2.block_timestamp = datetime.strptime(
            "2022/01/01 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_2)

        _utxo_3 = UTXO()
        _utxo_3.transaction_hash = "tx3"
        _utxo_3.account_address = user_address_1
        _utxo_3.token_address = token_address_1
        _utxo_3.amount = 30
        _utxo_3.block_number = 3
        _utxo_3.block_timestamp = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_3)

        _utxo_4 = UTXO()
        _utxo_4.transaction_hash = "tx4"
        _utxo_4.account_address = user_address_1
        _utxo_4.token_address = token_address_1
        _utxo_4.amount = 40
        _utxo_4.block_number = 4
        _utxo_4.block_timestamp = datetime.strptime(
            "2022/01/02 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_4)

        _utxo_5 = UTXO()
        _utxo_5.transaction_hash = "tx5"
        _utxo_5.account_address = user_address_2
        _utxo_5.token_address = token_address_1
        _utxo_5.amount = 200
        _utxo_5.block_number = 5
        _utxo_5.block_timestamp = datetime.strptime(
            "2021/12/31 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_5)

        _utxo_6 = UTXO()
        _utxo_6.transaction_hash = "tx6"
        _utxo_6.account_address = user_address_2
        _utxo_6.token_address = token_address_1
        _utxo_6.amount = 20
        _utxo_6.block_number = 6
        _utxo_6.block_timestamp = datetime.strptime(
            "2022/01/01 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_6)

        _utxo_7 = UTXO()
        _utxo_7.transaction_hash = "tx7"
        _utxo_7.account_address = user_address_2
        _utxo_7.token_address = token_address_1
        _utxo_7.amount = 40
        _utxo_7.block_number = 7
        _utxo_7.block_timestamp = datetime.strptime(
            "2022/01/01 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_7)

        _utxo_8 = UTXO()
        _utxo_8.transaction_hash = "tx8"
        _utxo_8.account_address = user_address_2
        _utxo_8.token_address = token_address_1
        _utxo_8.amount = 2
        _utxo_8.block_number = 8
        _utxo_8.block_timestamp = datetime.strptime(
            "2022/01/02 01:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/02
        async_db.add(_utxo_8)

        _utxo_9 = UTXO()
        _utxo_9.transaction_hash = "tx9"
        _utxo_9.account_address = issuer_address
        _utxo_9.token_address = token_address_1
        _utxo_9.amount = 300
        _utxo_9.block_number = 9
        _utxo_9.block_timestamp = datetime.strptime(
            "2021/12/31 15:20:30", "%Y/%m/%d %H:%M:%S"
        )  # JST 2022/01/01
        async_db.add(_utxo_9)

        # Prepare data: LedgerDetailsTemplate
        _details_template = LedgerDetailsTemplate()
        _details_template.token_address = token_address_1
        _details_template.token_detail_type = "劣後受益権"
        _details_template.data_type = LedgerDataType.IBET_FIN
        _details_template.data_source = "data_id_1"
        async_db.add(_details_template)

        await async_db.commit()

        # Execute
        await ledger_utils.request_ledger_creation(async_db, token_address_1)
        await async_db.commit()

        # Assertion
        ledger_req = (await async_db.scalars(select(LedgerCreationRequest))).all()
        assert len(ledger_req) == 1
        assert ledger_req[0].request_id is not None
        assert ledger_req[0].token_type == TokenType.IBET_STRAIGHT_BOND
        assert ledger_req[0].token_address == token_address_1
        assert ledger_req[0].status == LedgerCreationStatus.PROCESSING

        ledger_req_data = (
            await async_db.scalars(select(LedgerCreationRequestData))
        ).all()
        assert len(ledger_req_data) == 5

        assert ledger_req_data[0].request_id == ledger_req[0].request_id
        assert ledger_req_data[0].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[0].account_address == user_address_1
        assert ledger_req_data[0].acquisition_date == "2022/01/01"
        assert ledger_req_data[0].name is None
        assert ledger_req_data[0].address is None
        assert ledger_req_data[0].amount == 110
        assert ledger_req_data[0].price == 20
        assert ledger_req_data[0].balance == 2200

        assert ledger_req_data[1].request_id == ledger_req[0].request_id
        assert ledger_req_data[1].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[1].account_address == user_address_1
        assert ledger_req_data[1].acquisition_date == "2022/01/02"
        assert ledger_req_data[1].name is None
        assert ledger_req_data[1].address is None
        assert ledger_req_data[1].amount == 70
        assert ledger_req_data[1].price == 20
        assert ledger_req_data[1].balance == 1400

        assert ledger_req_data[2].request_id == ledger_req[0].request_id
        assert ledger_req_data[2].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[2].account_address == user_address_2
        assert ledger_req_data[2].acquisition_date == "2022/01/01"
        assert ledger_req_data[2].name is None
        assert ledger_req_data[2].address is None
        assert ledger_req_data[2].amount == 220
        assert ledger_req_data[2].price == 20
        assert ledger_req_data[2].balance == 4400

        assert ledger_req_data[3].request_id == ledger_req[0].request_id
        assert ledger_req_data[3].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[3].account_address == user_address_2
        assert ledger_req_data[3].acquisition_date == "2022/01/02"
        assert ledger_req_data[3].name is None
        assert ledger_req_data[3].address is None
        assert ledger_req_data[3].amount == 42
        assert ledger_req_data[3].price == 20
        assert ledger_req_data[3].balance == 840

        assert ledger_req_data[4].request_id == ledger_req[0].request_id
        assert ledger_req_data[4].data_type == LedgerDataType.IBET_FIN
        assert ledger_req_data[4].account_address == issuer_address
        assert ledger_req_data[4].acquisition_date == "2022/01/01"
        assert ledger_req_data[4].name is None
        assert ledger_req_data[4].address is None
        assert ledger_req_data[4].amount == 300
        assert ledger_req_data[4].price == 20
        assert ledger_req_data[4].balance == 6000


@pytest.mark.asyncio
class TestSyncRequestWithRegisteredPersonalInfo:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # No request data
    # -> skip
    async def test_normal_1(self, async_db):
        # Execute
        (
            initial_unset_count,
            final_set_count,
        ) = await ledger_utils.sync_request_with_registered_personal_info(
            async_db,
            request_id="test_request_id",
            issuer_address="test_issuer_address",
        )
        await async_db.commit()

        # Assertion
        assert initial_unset_count == 0
        assert final_set_count == 0

    # <Normal_2>
    # PersonalInfo is not registered
    async def test_normal_2(self, async_db):
        request_id = "test_req_id"
        issuer_address = "test_issuer_address"
        user_address_1 = "test_address_1"

        # Prepare data: LedgerCreationRequestData
        ledger_req_data = LedgerCreationRequestData()
        ledger_req_data.request_id = request_id
        ledger_req_data.data_type = LedgerDataType.IBET_FIN
        ledger_req_data.account_address = user_address_1
        ledger_req_data.acquisition_date = "2024/11/09"
        ledger_req_data.amount = 10
        ledger_req_data.price = 20
        ledger_req_data.balance = 200
        async_db.add(ledger_req_data)
        await async_db.commit()

        # Execute
        (
            initial_unset_count,
            final_set_count,
        ) = await ledger_utils.sync_request_with_registered_personal_info(
            async_db,
            request_id=request_id,
            issuer_address=issuer_address,
        )
        await async_db.commit()

        # Assertion
        assert initial_unset_count == 1
        assert final_set_count == 0

    # <Normal_3>
    # Update PersonalInfo
    async def test_normal_3(self, async_db):
        request_id = "test_req_id"
        issuer_address = "test_issuer_address"
        user_address_1 = "test_address_1"

        # Prepare data: LedgerCreationRequestData
        ledger_req_data = LedgerCreationRequestData()
        ledger_req_data.request_id = request_id
        ledger_req_data.data_type = LedgerDataType.IBET_FIN
        ledger_req_data.account_address = user_address_1
        ledger_req_data.acquisition_date = "2024/11/09"
        ledger_req_data.amount = 10
        ledger_req_data.price = 20
        ledger_req_data.balance = 200
        async_db.add(ledger_req_data)

        # Prepare data: IDXPersonalInfo
        idx_personal_info = IDXPersonalInfo()
        idx_personal_info.account_address = user_address_1
        idx_personal_info.issuer_address = issuer_address
        idx_personal_info.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        idx_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(idx_personal_info)

        await async_db.commit()

        # Execute
        (
            initial_unset_count,
            final_set_count,
        ) = await ledger_utils.sync_request_with_registered_personal_info(
            async_db,
            request_id=request_id,
            issuer_address=issuer_address,
        )
        await async_db.commit()

        # Assertion
        assert initial_unset_count == 1
        assert final_set_count == 1

        ledger_req_data = (
            await async_db.scalars(select(LedgerCreationRequestData).limit(1))
        ).first()
        assert ledger_req_data.name == "name_test1"
        assert ledger_req_data.address == "address_test1"


@pytest.mark.asyncio
class TestFinalizeLedger:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # No token information
    # -> skip
    async def test_normal_1_1(self, async_db):
        # Execute
        await ledger_utils.finalize_ledger(
            async_db,
            request_id="test_request_id",
            token_address="invalid_token_address",
        )
        await async_db.commit()

        # Assertion
        assert len((await async_db.scalars(select(Ledger))).all()) == 0

    # <Normal_1_2>
    # Only IBET_STRAIGHT_BOND/IBET_SHARE can be used as token.type
    # -> skip
    async def test_normal_1_2(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        token_address_1 = "test_token_address"

        # Prepare data
        _token_1 = Token()
        _token_1.type = "invalid_token_type"
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)
        await async_db.commit()

        # Execute
        await ledger_utils.finalize_ledger(
            async_db,
            request_id="test_request_id",
            token_address=token_address_1,
        )
        await async_db.commit()

        # Assertion
        assert len((await async_db.scalars(select(Ledger))).all()) == 0

    # <Normal_2>
    # Ledger template is not set
    # -> skip
    async def test_normal_2(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        token_address_1 = "test_token_address"

        # Prepare data
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)
        await async_db.commit()

        # Execute
        await ledger_utils.finalize_ledger(
            async_db,
            request_id="test_request_id",
            token_address=token_address_1,
        )
        await async_db.commit()

        # Assertion
        assert len((await async_db.scalars(select(Ledger))).all()) == 0

    # <Normal_3>
    # Ledger details template is not set
    @pytest.mark.freeze_time("2024-11-06 12:34:56")
    async def test_normal_3(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        token_address_1 = "test_token_address"

        # Prepare data: Token
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)
        await async_db.commit()

        # Prepare data: LedgerTemplate
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "テスト項目1": "テスト値1",
                "テスト項目2": {
                    "テスト項目A": "テスト値2A",
                    "テスト項目B": "テスト値2B",
                },
                "テスト項目3": {
                    "テスト項目A": {"テスト項目a": "テスト値3Aa"},
                    "テスト項目B": "テスト値3B",
                },
            },
        ]
        _template.token_name = "受益権テスト"
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-テスト項目1": "f-テスト値1",
                "f-テスト項目2": {
                    "f-テスト項目A": "f-テスト値2A",
                    "f-テスト項目B": "f-テスト値2B",
                },
                "f-テスト項目3": {
                    "f-テスト項目A": {"f-テスト項目a": "f-テスト値3Aa"},
                    "f-テスト項目B": "f-テスト値3B",
                },
            },
        ]
        async_db.add(_template)

        await async_db.commit()

        # Execute
        await ledger_utils.finalize_ledger(
            async_db,
            request_id="test_request_id",
            token_address=token_address_1,
            currency_code="JPY",
        )
        await async_db.commit()

        # Assertion
        ledger = (await async_db.scalars(select(Ledger))).all()
        assert len(ledger) == 1

        assert ledger[0].token_address == token_address_1
        assert ledger[0].token_type == TokenType.IBET_SHARE
        assert ledger[0].ledger == {
            "created": "2024/11/06",
            "token_name": _template.token_name,
            "currency": "JPY",
            "headers": _template.headers,
            "details": [],
            "footers": _template.footers,
        }

        _notifications = (await async_db.scalars(select(Notification))).all()
        assert len(_notifications) == 1
        assert _notifications[0].id == 1
        assert _notifications[0].notice_id is not None
        assert _notifications[0].issuer_address == issuer_address
        assert _notifications[0].priority == 0
        assert _notifications[0].type == NotificationType.CREATE_LEDGER_INFO
        assert _notifications[0].code == 0
        assert _notifications[0].metainfo == {
            "token_address": token_address_1,
            "token_type": TokenType.IBET_SHARE,
            "ledger_id": 1,
        }

    # <Normal_4>
    # Create Ledger data from LedgerCreationRequestData
    @pytest.mark.freeze_time("2024-11-06 12:34:56")
    async def test_normal_4(self, async_db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        user_1 = config_eth_account("user2")
        user_address_1 = user_1["address"]

        token_address_1 = "test_token_address"

        # Prepare data: Token
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        _token_1.version = TokenVersion.V_24_09
        async_db.add(_token_1)
        await async_db.commit()

        # Prepare data: LedgerTemplate
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "テスト項目1": "テスト値1",
                "テスト項目2": {
                    "テスト項目A": "テスト値2A",
                    "テスト項目B": "テスト値2B",
                },
                "テスト項目3": {
                    "テスト項目A": {"テスト項目a": "テスト値3Aa"},
                    "テスト項目B": "テスト値3B",
                },
            },
        ]
        _template.token_name = "受益権テスト"
        _template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-テスト項目1": "f-テスト値1",
                "f-テスト項目2": {
                    "f-テスト項目A": "f-テスト値2A",
                    "f-テスト項目B": "f-テスト値2B",
                },
                "f-テスト項目3": {
                    "f-テスト項目A": {"f-テスト項目a": "f-テスト値3Aa"},
                    "f-テスト項目B": "f-テスト値3B",
                },
            },
        ]
        async_db.add(_template)

        # Prepare data: LedgerDetailsTemplate
        _details_template = LedgerDetailsTemplate()
        _details_template.token_address = token_address_1
        _details_template.token_detail_type = "劣後受益権"
        _details_template.data_type = LedgerDataType.DB
        _details_template.data_source = "data_id_1"
        async_db.add(_details_template)

        _details_template = LedgerDetailsTemplate()
        _details_template.token_address = token_address_1
        _details_template.token_detail_type = "受益権"
        _details_template.data_type = LedgerDataType.IBET_FIN
        _details_template.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "test項目1": "test値1",
                "test項目2": {
                    "test項目A": "test値2A",
                },
            },
        ]
        _details_template.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "test-item1": "test-value1",
                "test-item2": {"test-itemA": {"test-item": "test-value2Aa"}},
            },
        ]
        _details_template.data_source = None
        async_db.add(_details_template)

        # Prepare data: LedgerCreationRequestData
        ledger_req_data = LedgerCreationRequestData()
        ledger_req_data.request_id = "req_id_1"
        ledger_req_data.data_type = LedgerDataType.DB
        ledger_req_data.account_address = user_address_1
        ledger_req_data.acquisition_date = "2024/11/08"
        ledger_req_data.name = "test_investor_name_1"
        ledger_req_data.address = "test_investor_address_1"
        ledger_req_data.amount = 10
        ledger_req_data.price = 20
        ledger_req_data.balance = 200
        async_db.add(ledger_req_data)

        ledger_req_data = LedgerCreationRequestData()
        ledger_req_data.request_id = "req_id_1"
        ledger_req_data.data_type = LedgerDataType.DB
        ledger_req_data.account_address = user_address_1
        ledger_req_data.acquisition_date = "2024/11/09"
        ledger_req_data.name = "test_investor_name_2"
        ledger_req_data.address = "test_investor_address_2"
        ledger_req_data.amount = 30
        ledger_req_data.price = 40
        ledger_req_data.balance = 1200
        async_db.add(ledger_req_data)

        ledger_req_data = LedgerCreationRequestData()
        ledger_req_data.request_id = "req_id_1"
        ledger_req_data.data_type = LedgerDataType.IBET_FIN
        ledger_req_data.account_address = user_address_1
        ledger_req_data.acquisition_date = "2024/11/08"
        ledger_req_data.name = "test_investor_name_3"
        ledger_req_data.address = "test_investor_address_3"
        ledger_req_data.amount = 10
        ledger_req_data.price = 20
        ledger_req_data.balance = 200
        async_db.add(ledger_req_data)

        ledger_req_data = LedgerCreationRequestData()
        ledger_req_data.request_id = "req_id_1"
        ledger_req_data.data_type = LedgerDataType.IBET_FIN
        ledger_req_data.account_address = user_address_1
        ledger_req_data.acquisition_date = "2024/11/09"
        ledger_req_data.name = None
        ledger_req_data.address = None
        ledger_req_data.amount = 30
        ledger_req_data.price = 40
        ledger_req_data.balance = 1200
        async_db.add(ledger_req_data)

        await async_db.commit()

        # Execute
        await ledger_utils.finalize_ledger(
            async_db,
            request_id="req_id_1",
            token_address=token_address_1,
            currency_code="JPY",
            some_personal_info_not_registered=True,
        )
        await async_db.commit()

        # Assertion
        ledger = (await async_db.scalars(select(Ledger))).all()
        assert len(ledger) == 1

        assert ledger[0].token_address == token_address_1
        assert ledger[0].token_type == TokenType.IBET_SHARE
        assert ledger[0].ledger == {
            "created": "2024/11/06",
            "token_name": _template.token_name,
            "currency": "JPY",
            "headers": _template.headers,
            "details": [
                {
                    "token_detail_type": "劣後受益権",
                    "headers": [],
                    "data": [
                        {
                            "account_address": user_address_1,
                            "name": "test_investor_name_1",
                            "address": "test_investor_address_1",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2024/11/08",
                        },
                        {
                            "account_address": user_address_1,
                            "name": "test_investor_name_2",
                            "address": "test_investor_address_2",
                            "amount": 30,
                            "price": 40,
                            "balance": 1200,
                            "acquisition_date": "2024/11/09",
                        },
                    ],
                    "footers": [],
                    "some_personal_info_not_registered": False,
                },
                {
                    "token_detail_type": "受益権",
                    "headers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "test項目1": "test値1",
                            "test項目2": {
                                "test項目A": "test値2A",
                            },
                        },
                    ],
                    "data": [
                        {
                            "account_address": user_address_1,
                            "name": "test_investor_name_3",
                            "address": "test_investor_address_3",
                            "amount": 10,
                            "price": 20,
                            "balance": 200,
                            "acquisition_date": "2024/11/08",
                        },
                        {
                            "account_address": user_address_1,
                            "name": None,
                            "address": None,
                            "amount": 30,
                            "price": 40,
                            "balance": 1200,
                            "acquisition_date": "2024/11/09",
                        },
                    ],
                    "footers": [
                        {
                            "key": "aaa",
                            "value": "bbb",
                        },
                        {
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {"test-item": "test-value2Aa"}
                            },
                        },
                    ],
                    "some_personal_info_not_registered": True,
                },
            ],
            "footers": _template.footers,
        }

        ledger_req_data = (
            await async_db.scalars(select(LedgerCreationRequestData))
        ).all()
        assert len(ledger_req_data) == 0

        _notifications = (await async_db.scalars(select(Notification))).all()
        assert len(_notifications) == 1
        assert _notifications[0].id == 1
        assert _notifications[0].notice_id is not None
        assert _notifications[0].issuer_address == issuer_address
        assert _notifications[0].priority == 0
        assert _notifications[0].type == NotificationType.CREATE_LEDGER_INFO
        assert _notifications[0].code == 0
        assert _notifications[0].metainfo == {
            "token_address": token_address_1,
            "token_type": TokenType.IBET_SHARE,
            "ledger_id": 1,
        }
