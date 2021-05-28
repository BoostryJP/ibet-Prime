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

import pytz
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_keyfile import decode_keyfile_json

from config import (
    WEB3_HTTP_PROVIDER,
    CHAIN_ID,
    TX_GAS_LIMIT,
    ZERO_ADDRESS,
    TZ
)
from app.utils.e2ee_utils import E2EEUtils
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract,
)
from app.model.blockchain.utils import ContractUtils
from app.model.schema import (
    IbetShareUpdate,
    IbetStraightBondUpdate
)
from app.model.db import (
    Account,
    AccountRsaStatus,
    Token,
    TokenType,
    IDXPersonalInfo,
    UTXO,
    Ledger,
    LedgerDetailsData,
    LedgerTemplate,
    LedgerDetailsTemplate,
    LedgerDetailsDataType,
)
from batch.lib import create_ledger
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def deploy_bond_token_contract(address, private_key, personal_info_contract_address):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        "token.redemption_date",
        30,
        "token.return_date",
        "token.return_amount",
        "token.purpose"
    ]

    contract_address, _, _ = IbetStraightBondContract.create(arguments, address, private_key)

    data = IbetStraightBondUpdate()
    data.personal_info_contract_address = personal_info_contract_address
    IbetStraightBondContract.update(contract_address, data, address, private_key)

    return contract_address


def deploy_share_token_contract(address, private_key, personal_info_contract_address):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        int(0.03 * 100),
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date",
        200
    ]

    contract_address, _, _ = IbetShareContract.create(arguments, address, private_key)

    data = IbetShareUpdate()
    data.image_url = ["aaa", "aaa", "aaa"]
    data.personal_info_contract_address = personal_info_contract_address
    IbetShareContract.update(contract_address, data, address, private_key)

    return contract_address


def deploy_personal_info_contract(address, private_key):
    contract_address, _, _ = ContractUtils.deploy_contract("PersonalInfo", [], address, private_key)
    return contract_address


def set_personal_info_contract(db, contract_address, issuer_address, sender_list):
    contract = ContractUtils.get_contract("PersonalInfo", contract_address)

    for sender in sender_list:
        tx = contract.functions.register(issuer_address, "").buildTransaction({
            "nonce": web3.eth.getTransactionCount(sender["address"]),
            "chainId": CHAIN_ID,
            "from": sender["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0
        })
        ContractUtils.send_transaction(tx, sender["private_key"])

        personal_info = PersonalInfoContract(db, issuer_address, contract_address)
        personal_info.modify_info(sender["address"], sender["data"])


class TestBatchLibCreateLedger:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Share Token
    def test_normal_1(self, db):
        issuer = config_eth_account("user5")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        # Account
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = issuer["rsa_private_key"]
        _account.rsa_public_key = issuer["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.SET.value
        db.add(_account)

        # Token
        personal_info_contract_address = deploy_personal_info_contract(issuer_address, issuer_private_key)
        set_personal_info_contract(db, personal_info_contract_address, issuer_address,
                                   [
                                       {
                                           "address": user_address_1,
                                           "private_key": user_private_key_1,
                                           "data": {
                                               "name": "name_test_con_1",
                                               "address": "address_test_con_1",
                                           },
                                       },
                                       {
                                           "address": user_address_2,
                                           "private_key": user_private_key_2,
                                           "data": {
                                               "name": "name_test_con_2",
                                               "address": "address_test_con_2",
                                           },
                                       }
                                   ])
        token_address_1 = deploy_share_token_contract(issuer_address, issuer_private_key,
                                                      personal_info_contract_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        # IDXPersonalInfo(only user_1)
        _idx_personal_info_1 = IDXPersonalInfo()
        _idx_personal_info_1.account_address = user_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": "name_test_db_1",
            "address": "address_test_db_1",
        }
        db.add(_idx_personal_info_1)

        # UTXO
        # user_1: "2022/01/01" = 100 + 10, "2022/01/02" = 30 + 40
        # user_2: "2022/01/01" = 200 + 20, "2022/01/02" = 40 + 2
        _utxo_1 = UTXO()
        _utxo_1.transaction_hash = "tx1"
        _utxo_1.account_address = user_address_1
        _utxo_1.token_address = token_address_1
        _utxo_1.amount = 100
        _utxo_1.block_number = 1
        _utxo_1.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_1)

        _utxo_2 = UTXO()
        _utxo_2.transaction_hash = "tx2"
        _utxo_2.account_address = user_address_1
        _utxo_2.token_address = token_address_1
        _utxo_2.amount = 10
        _utxo_2.block_number = 2
        _utxo_2.block_timestamp = datetime.strptime("2022/01/01 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_2)

        _utxo_3 = UTXO()
        _utxo_3.transaction_hash = "tx3"
        _utxo_3.account_address = user_address_1
        _utxo_3.token_address = token_address_1
        _utxo_3.amount = 30
        _utxo_3.block_number = 3
        _utxo_3.block_timestamp = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_3)

        _utxo_4 = UTXO()
        _utxo_4.transaction_hash = "tx4"
        _utxo_4.account_address = user_address_1
        _utxo_4.token_address = token_address_1
        _utxo_4.amount = 40
        _utxo_4.block_number = 4
        _utxo_4.block_timestamp = datetime.strptime("2022/01/02 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_4)

        _utxo_5 = UTXO()
        _utxo_5.transaction_hash = "tx5"
        _utxo_5.account_address = user_address_2
        _utxo_5.token_address = token_address_1
        _utxo_5.amount = 200
        _utxo_5.block_number = 5
        _utxo_5.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_5)

        _utxo_6 = UTXO()
        _utxo_6.transaction_hash = "tx6"
        _utxo_6.account_address = user_address_2
        _utxo_6.token_address = token_address_1
        _utxo_6.amount = 20
        _utxo_6.block_number = 6
        _utxo_6.block_timestamp = datetime.strptime("2022/01/01 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_6)

        _utxo_7 = UTXO()
        _utxo_7.transaction_hash = "tx7"
        _utxo_7.account_address = user_address_2
        _utxo_7.token_address = token_address_1
        _utxo_7.amount = 40
        _utxo_7.block_number = 7
        _utxo_7.block_timestamp = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_7)

        _utxo_8 = UTXO()
        _utxo_8.transaction_hash = "tx8"
        _utxo_8.account_address = user_address_2
        _utxo_8.token_address = token_address_1
        _utxo_8.amount = 2
        _utxo_8.block_number = 8
        _utxo_8.block_timestamp = datetime.strptime("2022/01/02 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_8)

        # Template
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
                    "テスト項目A": {
                        "テスト項目a": "テスト値3Aa"
                    },
                    "テスト項目B": "テスト値3B",
                },
            }
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
                "f-テスト項目A": {
                    "f-テスト項目a": "f-テスト値3Aa"
                },
                "f-テスト項目B": "f-テスト値3B",
            },
        }]
        db.add(_template)

        # Template Details 1
        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address_1
        _details_1.token_detail_type = "優先受益権"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "test項目1": "test値1",
                "test項目2": {
                    "test項目A": "test値2A",
                },
            }
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "test-item1": "test-value1",
                "test-item2": {
                    "test-itemA": {
                        "test-itema": "test-value2Aa"
                    }
                },
            }
        ]
        _details_1.data_type = LedgerDetailsDataType.IBET_FIN
        _details_1.data_source = token_address_1
        db.add(_details_1)

        # Template Details 2
        _details_2 = LedgerDetailsTemplate()
        _details_2.token_address = token_address_1
        _details_2.token_detail_type = "劣後受益権"
        _details_2.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "d-test項目1": "d-test値1",
                "d-test項目2": "d-test値2",
            }
        ]
        _details_2.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-d-test項目1": "d-test値1",
                "f-d-test項目2": "d-test値2",
            }
        ]
        _details_2.data_type = LedgerDetailsDataType.DB
        _details_2.data_source = "data_id_2"
        db.add(_details_2)

        # Details 2 Data
        _details_2_data_1 = LedgerDetailsData()
        _details_2_data_1.token_address = token_address_1
        _details_2_data_1.data_id = "data_id_2"
        _details_2_data_1.account_address = "0x0001"
        _details_2_data_1.name = "test_data_name_1"
        _details_2_data_1.address = "test_data_address_1"
        _details_2_data_1.amount = 100
        _details_2_data_1.price = 200
        _details_2_data_1.balance = 20000
        _details_2_data_1.acquisition_date = "2022/03/03"
        db.add(_details_2_data_1)

        _details_2_data_2 = LedgerDetailsData()
        _details_2_data_2.token_address = token_address_1
        _details_2_data_2.data_id = "data_id_2"
        _details_2_data_2.account_address = "0x0002"
        _details_2_data_2.name = "test_data_name_2"
        _details_2_data_2.address = "test_data_address_2"
        _details_2_data_2.amount = 30
        _details_2_data_2.price = 40
        _details_2_data_2.balance = 1200
        _details_2_data_2.acquisition_date = "2022/12/03"
        db.add(_details_2_data_2)

        # Execute
        create_ledger.create_ledger(token_address_1, db)

        # assertion
        _ledger = db.query(Ledger).first()
        assert _ledger.id == 1
        assert _ledger.token_address == token_address_1
        assert _ledger.token_type == TokenType.IBET_SHARE
        now_ymd = datetime.now(pytz.timezone(TZ)).strftime("%Y/%m/%d")
        assert _ledger.ledger == {
            "created": now_ymd,
            "token_name": "",
            "headers": [],
            "details": [
                {
                    "token_detail_type": "優先受益権",
                    "headers": [],
                    "data": [
                        {
                            "account_address": user_address_2,
                            "name": "name_test_con_2",
                            "address": "address_test_con_2",
                            "amount": 220,
                            "price": 200,
                            "balance": 220 * 200,
                            "acquisition_date": "2022/01/01",
                        },
                        {
                            "account_address": user_address_2,
                            "name": "name_test_con_2",
                            "address": "address_test_con_2",
                            "amount": 42,
                            "price": 200,
                            "balance": 42 * 200,
                            "acquisition_date": "2022/01/02",
                        },
                        {
                            "account_address": user_address_1,
                            "name": "name_test_db_1",
                            "address": "address_test_db_1",
                            "amount": 110,
                            "price": 200,
                            "balance": 110 * 200,
                            "acquisition_date": "2022/01/01",
                        },
                        {
                            "account_address": user_address_1,
                            "name": "name_test_db_1",
                            "address": "address_test_db_1",
                            "amount": 70,
                            "price": 200,
                            "balance": 70 * 200,
                            "acquisition_date": "2022/01/02",
                        },
                    ],
                    "footers": []
                },
                {
                    "token_detail_type": "劣後受益権",
                    "headers": [],
                    "data": [],
                    "footers": []
                },
            ],
            "footers": []
        }

    # <Normal_2>
    # Bond Token
    def test_normal_2(self, db):
        issuer = config_eth_account("user5")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_1 = config_eth_account("user1")
        user_address_1 = user_1["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_2 = user_2["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        # Account
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = issuer["rsa_private_key"]
        _account.rsa_public_key = issuer["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.SET.value
        db.add(_account)

        # Token
        personal_info_contract_address = deploy_personal_info_contract(issuer_address, issuer_private_key)
        set_personal_info_contract(db, personal_info_contract_address, issuer_address,
                                   [
                                       {
                                           "address": user_address_1,
                                           "private_key": user_private_key_1,
                                           "data": {
                                               "name": "name_test_con_1",
                                               "address": "address_test_con_1",
                                           },
                                       },
                                       {
                                           "address": user_address_2,
                                           "private_key": user_private_key_2,
                                           "data": {
                                               "name": "name_test_con_2",
                                               "address": "address_test_con_2",
                                           },
                                       }
                                   ])
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key,
                                                     personal_info_contract_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        # IDXPersonalInfo(only user_1)
        _idx_personal_info_1 = IDXPersonalInfo()
        _idx_personal_info_1.account_address = user_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": "name_test_db_1",
            "address": "address_test_db_1",
        }
        db.add(_idx_personal_info_1)

        # UTXO
        # user_1: "2022/01/01" = 100 + 10, "2022/01/02" = 30 + 40
        # user_2: "2022/01/01" = 200 + 20, "2022/01/02" = 40 + 2
        _utxo_1 = UTXO()
        _utxo_1.transaction_hash = "tx1"
        _utxo_1.account_address = user_address_1
        _utxo_1.token_address = token_address_1
        _utxo_1.amount = 100
        _utxo_1.block_number = 1
        _utxo_1.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_1)

        _utxo_2 = UTXO()
        _utxo_2.transaction_hash = "tx2"
        _utxo_2.account_address = user_address_1
        _utxo_2.token_address = token_address_1
        _utxo_2.amount = 10
        _utxo_2.block_number = 2
        _utxo_2.block_timestamp = datetime.strptime("2022/01/01 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_2)

        _utxo_3 = UTXO()
        _utxo_3.transaction_hash = "tx3"
        _utxo_3.account_address = user_address_1
        _utxo_3.token_address = token_address_1
        _utxo_3.amount = 30
        _utxo_3.block_number = 3
        _utxo_3.block_timestamp = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_3)

        _utxo_4 = UTXO()
        _utxo_4.transaction_hash = "tx4"
        _utxo_4.account_address = user_address_1
        _utxo_4.token_address = token_address_1
        _utxo_4.amount = 40
        _utxo_4.block_number = 4
        _utxo_4.block_timestamp = datetime.strptime("2022/01/02 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_4)

        _utxo_5 = UTXO()
        _utxo_5.transaction_hash = "tx5"
        _utxo_5.account_address = user_address_2
        _utxo_5.token_address = token_address_1
        _utxo_5.amount = 200
        _utxo_5.block_number = 5
        _utxo_5.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_5)

        _utxo_6 = UTXO()
        _utxo_6.transaction_hash = "tx6"
        _utxo_6.account_address = user_address_2
        _utxo_6.token_address = token_address_1
        _utxo_6.amount = 20
        _utxo_6.block_number = 6
        _utxo_6.block_timestamp = datetime.strptime("2022/01/01 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_6)

        _utxo_7 = UTXO()
        _utxo_7.transaction_hash = "tx7"
        _utxo_7.account_address = user_address_2
        _utxo_7.token_address = token_address_1
        _utxo_7.amount = 40
        _utxo_7.block_number = 7
        _utxo_7.block_timestamp = datetime.strptime("2022/01/01 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_7)

        _utxo_8 = UTXO()
        _utxo_8.transaction_hash = "tx8"
        _utxo_8.account_address = user_address_2
        _utxo_8.token_address = token_address_1
        _utxo_8.amount = 2
        _utxo_8.block_number = 8
        _utxo_8.block_timestamp = datetime.strptime("2022/01/02 01:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/02
        db.add(_utxo_8)

        # Template

        # Template
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.token_name = "受益権テスト"
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
                    "テスト項目A": {
                        "テスト項目a": "テスト値3Aa"
                    },
                    "テスト項目B": "テスト値3B",
                },
            }
        ]
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
                    "f-テスト項目A": {
                        "f-テスト項目a": "f-テスト値3Aa"
                    },
                    "f-テスト項目B": "f-テスト値3B",
                },
            }
        ]
        db.add(_template)

        # Template Details 1
        _details_1 = LedgerDetailsTemplate()
        _details_1.token_address = token_address_1
        _details_1.token_detail_type = "優先受益権"
        _details_1.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "test項目1": "test値1",
                "test項目2": {
                    "test項目A": "test値2A",
                },
            }
        ]
        _details_1.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "test-item1": "test-value1",
                "test-item2": {
                    "test-itemA": {
                        "test-itema": "test-value2Aa"
                    }
                },
            }
        ]
        _details_1.data_type = LedgerDetailsDataType.IBET_FIN
        _details_1.data_source = token_address_1
        db.add(_details_1)

        # Template Details 2
        _details_2 = LedgerDetailsTemplate()
        _details_2.token_address = token_address_1
        _details_2.token_detail_type = "劣後受益権"
        _details_2.headers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "d-test項目1": "d-test値1",
                "d-test項目2": "d-test値2",
            }
        ]
        _details_2.footers = [
            {
                "key": "aaa",
                "value": "bbb",
            },
            {
                "f-d-test項目1": "d-test値1",
                "f-d-test項目2": "d-test値2",
            }
        ]
        _details_2.data_type = LedgerDetailsDataType.DB
        _details_2.data_source = "data_id_2"
        db.add(_details_2)

        # Details 2 Data
        _details_2_data_1 = LedgerDetailsData()
        _details_2_data_1.token_address = token_address_1
        _details_2_data_1.data_id = "data_id_2"
        _details_2_data_1.account_address = "0x0001"
        _details_2_data_1.name = "test_data_name_1"
        _details_2_data_1.address = "test_data_address_1"
        _details_2_data_1.amount = 100
        _details_2_data_1.price = 200
        _details_2_data_1.balance = 20000
        _details_2_data_1.acquisition_date = "2022/03/03"
        db.add(_details_2_data_1)

        _details_2_data_2 = LedgerDetailsData()
        _details_2_data_2.token_address = token_address_1
        _details_2_data_2.data_id = "data_id_2"
        _details_2_data_2.account_address = "0x0002"
        _details_2_data_2.name = "test_data_name_2"
        _details_2_data_2.address = "test_data_address_2"
        _details_2_data_2.amount = 30
        _details_2_data_2.price = 40
        _details_2_data_2.balance = 1200
        _details_2_data_2.acquisition_date = "2022/12/03"
        db.add(_details_2_data_2)

        # Execute
        create_ledger.create_ledger(token_address_1, db)

        # assertion
        _ledger = db.query(Ledger).first()
        assert _ledger.id == 1
        assert _ledger.token_address == token_address_1
        assert _ledger.token_type == TokenType.IBET_STRAIGHT_BOND
        now_ymd = datetime.now(pytz.timezone(TZ)).strftime("%Y/%m/%d")
        assert _ledger.ledger == {
            "created": now_ymd,
            "token_name": "",
            "headers": [],
            "details": [
                {
                    "token_detail_type": "優先受益権",
                    "headers": [],
                    "data": [
                        {
                            "account_address": user_address_2,
                            "name": "name_test_con_2",
                            "address": "address_test_con_2",
                            "amount": 220,
                            "price": 20,
                            "balance": 220 * 20,
                            "acquisition_date": "2022/01/01",
                        },
                        {
                            "account_address": user_address_2,
                            "name": "name_test_con_2",
                            "address": "address_test_con_2",
                            "amount": 42,
                            "price": 20,
                            "balance": 42 * 20,
                            "acquisition_date": "2022/01/02",
                        },
                        {
                            "account_address": user_address_1,
                            "name": "name_test_db_1",
                            "address": "address_test_db_1",
                            "amount": 110,
                            "price": 20,
                            "balance": 110 * 20,
                            "acquisition_date": "2022/01/01",
                        },
                        {
                            "account_address": user_address_1,
                            "name": "name_test_db_1",
                            "address": "address_test_db_1",
                            "amount": 70,
                            "price": 20,
                            "balance": 70 * 20,
                            "acquisition_date": "2022/01/02",
                        },
                    ],
                    "footers": []
                },
                {
                    "token_detail_type": "劣後受益権",
                    "headers": [],
                    "data": [],
                    "footers": []
                },
            ],
            "footers": []
        }

    # <Normal_3>
    # SKIP: Not Exist Template
    def test_normal_3(self, db):
        issuer = config_eth_account("user5")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        # Token
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key, ZERO_ADDRESS)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        # Execute
        create_ledger.create_ledger(token_address_1, db)

        # assertion
        _ledger = db.query(Ledger).first()
        assert _ledger is None

    # <Normal_4>
    # SKIP: Other Token Type
    def test_normal_4(self, db):
        issuer = config_eth_account("user5")
        issuer_address = issuer["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=issuer["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        # Token
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key, ZERO_ADDRESS)
        _token_1 = Token()
        _token_1.type = "IbetCoupon"
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        # Execute
        create_ledger.create_ledger(token_address_1, db)

        # assertion
        _ledger = db.query(Ledger).first()
        assert _ledger is None

    ###########################################################################
    # Error Case
    ###########################################################################
