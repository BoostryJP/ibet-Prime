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
from app.model.utils import E2EEUtils
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
    LedgerTemplate,
    LedgerTemplateRights,
    LedgerRightsDetails,
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
    # Share Token(JPN)
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
        _template.country_code = "JPN"
        _template.ledger_name = "受益権テスト"
        _template.item = {
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
        db.add(_template)

        # Template Rights 1
        _right_1 = LedgerTemplateRights()
        _right_1.token_address = token_address_1
        _right_1.rights_name = "優先受益権"
        _right_1.item = {
            "test項目1": "test値1",
            "test項目2": {
                "test項目A": "test値2A",
            },
        }
        _right_1.details_item = {
            "test-item1": "test-value1",
            "test-item2": {
                "test-itemA": {
                    "test-itema": "test-value2Aa"
                }
            },
        }
        db.add(_right_1)

        # Template Rights 2
        _right_2 = LedgerTemplateRights()
        _right_2.token_address = token_address_1
        _right_2.rights_name = "劣後受益権"
        _right_2.is_uploaded_details = True  # Details From DB
        _right_2.item = {
            "r-test項目1": "r-test値1",
            "r-test項目2": "r-test値2",
        }
        _right_2.details_item = {
            "r-test-item1": "r-test-value1",
            "r-test-item2": "r-test-value2",
        }
        db.add(_right_2)

        # Rights 2 Details
        _right_2_details_1 = LedgerRightsDetails()
        _right_2_details_1.token_address = token_address_1
        _right_2_details_1.rights_name = "劣後受益権"
        _right_2_details_1.account_address = "0x0001"
        _right_2_details_1.name = "test_detail_name_1"
        _right_2_details_1.address = "test_detail_address_1"
        _right_2_details_1.amount = 100
        _right_2_details_1.price = 200
        _right_2_details_1.balance = 20000
        _right_2_details_1.acquisition_date = "2022/03/03"
        db.add(_right_2_details_1)

        _right_2_details_2 = LedgerRightsDetails()
        _right_2_details_2.token_address = token_address_1
        _right_2_details_2.rights_name = "劣後受益権"
        _right_2_details_2.account_address = "0x0002"
        _right_2_details_2.name = "test_detail_name_2"
        _right_2_details_2.address = "test_detail_address_2"
        _right_2_details_2.amount = 30
        _right_2_details_2.price = 40
        _right_2_details_2.balance = 1200
        _right_2_details_2.acquisition_date = "2022/12/03"
        db.add(_right_2_details_2)

        # Execute
        create_ledger.create_ledger(token_address_1, db)

        # assertion
        _ledger = db.query(Ledger).first()
        assert _ledger.id == 1
        assert _ledger.token_address == token_address_1
        assert _ledger.token_type == TokenType.IBET_SHARE
        now_ymd = datetime.now(pytz.timezone(TZ)).strftime("%Y/%m/%d")
        assert _ledger.ledger == {
            "原簿作成日": now_ymd,
            "原簿名称": "受益権テスト",
            "項目": {
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
            },
            "権利": [
                {
                    "権利名称": "優先受益権",
                    "項目": {
                        "test項目1": "test値1",
                        "test項目2": {
                            "test項目A": "test値2A",
                        },
                    },
                    "明細": [
                        {
                            "アカウントアドレス": user_address_2,
                            "氏名または名称": "name_test_con_2",
                            "住所": "address_test_con_2",
                            "保有口数": 220,
                            "一口あたりの金額": 200,
                            "保有残高": 220 * 200,
                            "取得日": "2022/01/01",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                        {
                            "アカウントアドレス": user_address_2,
                            "氏名または名称": "name_test_con_2",
                            "住所": "address_test_con_2",
                            "保有口数": 42,
                            "一口あたりの金額": 200,
                            "保有残高": 42 * 200,
                            "取得日": "2022/01/02",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                        {
                            "アカウントアドレス": user_address_1,
                            "氏名または名称": "name_test_db_1",
                            "住所": "address_test_db_1",
                            "保有口数": 110,
                            "一口あたりの金額": 200,
                            "保有残高": 110 * 200,
                            "取得日": "2022/01/01",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                        {
                            "アカウントアドレス": user_address_1,
                            "氏名または名称": "name_test_db_1",
                            "住所": "address_test_db_1",
                            "保有口数": 70,
                            "一口あたりの金額": 200,
                            "保有残高": 70 * 200,
                            "取得日": "2022/01/02",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                    ]
                },
                {
                    "権利名称": "劣後受益権",
                    "項目": {
                        "r-test項目1": "r-test値1",
                        "r-test項目2": "r-test値2",
                    },
                    "明細": [
                        {
                            "アカウントアドレス": "0x0001",
                            "氏名または名称": "test_detail_name_1",
                            "住所": "test_detail_address_1",
                            "保有口数": 100,
                            "一口あたりの金額": 200,
                            "保有残高": 20000,
                            "取得日": "2022/03/03",
                            "r-test-item1": "r-test-value1",
                            "r-test-item2": "r-test-value2",
                        },
                        {
                            "アカウントアドレス": "0x0002",
                            "氏名または名称": "test_detail_name_2",
                            "住所": "test_detail_address_2",
                            "保有口数": 30,
                            "一口あたりの金額": 40,
                            "保有残高": 1200,
                            "取得日": "2022/12/03",
                            "r-test-item1": "r-test-value1",
                            "r-test-item2": "r-test-value2",
                        },
                    ]
                },
            ]
        }
        assert _ledger.country_code == "JPN"

    # <Normal_2>
    # Bond Token(USA)
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
        _template = LedgerTemplate()
        _template.token_address = token_address_1
        _template.issuer_address = issuer_address
        _template.country_code = "USA"
        _template.ledger_name = "受益権テスト"
        _template.item = {
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
        db.add(_template)

        # Template Rights 1
        _right_1 = LedgerTemplateRights()
        _right_1.token_address = token_address_1
        _right_1.rights_name = "優先受益権"
        _right_1.item = {
            "test項目1": "test値1",
            "test項目2": {
                "test項目A": "test値2A",
            },
        }
        _right_1.details_item = {
            "test-item1": "test-value1",
            "test-item2": {
                "test-itemA": {
                    "test-itema": "test-value2Aa"
                }
            },
        }
        db.add(_right_1)

        # Template Rights 2
        _right_2 = LedgerTemplateRights()
        _right_2.token_address = token_address_1
        _right_2.rights_name = "劣後受益権"
        _right_2.is_uploaded_details = True  # Details From DB
        _right_2.item = {
            "r-test項目1": "r-test値1",
            "r-test項目2": "r-test値2",
        }
        _right_2.details_item = {
            "r-test-item1": "r-test-value1",
            "r-test-item2": "r-test-value2",
        }
        db.add(_right_2)

        # Rights 2 Details
        _right_2_details_1 = LedgerRightsDetails()
        _right_2_details_1.token_address = token_address_1
        _right_2_details_1.rights_name = "劣後受益権"
        _right_2_details_1.account_address = "0x0001"
        _right_2_details_1.name = "test_detail_name_1"
        _right_2_details_1.address = "test_detail_address_1"
        _right_2_details_1.amount = 100
        _right_2_details_1.price = 200
        _right_2_details_1.balance = 20000
        _right_2_details_1.acquisition_date = "2022/03/03"
        db.add(_right_2_details_1)

        _right_2_details_2 = LedgerRightsDetails()
        _right_2_details_2.token_address = token_address_1
        _right_2_details_2.rights_name = "劣後受益権"
        _right_2_details_2.account_address = "0x0002"
        _right_2_details_2.name = "test_detail_name_2"
        _right_2_details_2.address = "test_detail_address_2"
        _right_2_details_2.amount = 30
        _right_2_details_2.price = 40
        _right_2_details_2.balance = 1200
        _right_2_details_2.acquisition_date = "2022/12/03"
        db.add(_right_2_details_2)

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
            "ledger_name": "受益権テスト",
            "item": {
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
            },
            "rights": [
                {
                    "rights_name": "優先受益権",
                    "item": {
                        "test項目1": "test値1",
                        "test項目2": {
                            "test項目A": "test値2A",
                        },
                    },
                    "details": [
                        {
                            "account_address": user_address_2,
                            "name": "name_test_con_2",
                            "address": "address_test_con_2",
                            "amount": 220,
                            "price": 20,
                            "balance": 220 * 20,
                            "acquisition_date": "2022/01/01",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                        {
                            "account_address": user_address_2,
                            "name": "name_test_con_2",
                            "address": "address_test_con_2",
                            "amount": 42,
                            "price": 20,
                            "balance": 42 * 20,
                            "acquisition_date": "2022/01/02",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                        {
                            "account_address": user_address_1,
                            "name": "name_test_db_1",
                            "address": "address_test_db_1",
                            "amount": 110,
                            "price": 20,
                            "balance": 110 * 20,
                            "acquisition_date": "2022/01/01",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                        {
                            "account_address": user_address_1,
                            "name": "name_test_db_1",
                            "address": "address_test_db_1",
                            "amount": 70,
                            "price": 20,
                            "balance": 70 * 20,
                            "acquisition_date": "2022/01/02",
                            "test-item1": "test-value1",
                            "test-item2": {
                                "test-itemA": {
                                    "test-itema": "test-value2Aa"
                                }
                            },
                        },
                    ]
                },
                {
                    "rights_name": "劣後受益権",
                    "item": {
                        "r-test項目1": "r-test値1",
                        "r-test項目2": "r-test値2",
                    },
                    "details": [
                        {
                            "account_address": "0x0001",
                            "name": "test_detail_name_1",
                            "address": "test_detail_address_1",
                            "amount": 100,
                            "price": 200,
                            "balance": 20000,
                            "acquisition_date": "2022/03/03",
                            "r-test-item1": "r-test-value1",
                            "r-test-item2": "r-test-value2",
                        },
                        {
                            "account_address": "0x0002",
                            "name": "test_detail_name_2",
                            "address": "test_detail_address_2",
                            "amount": 30,
                            "price": 40,
                            "balance": 1200,
                            "acquisition_date": "2022/12/03",
                            "r-test-item1": "r-test-value1",
                            "r-test-item2": "r-test-value2",
                        },
                    ]
                },
            ]
        }
        assert _ledger.country_code == "USA"

    # <Normal_3>
    # Create Default Corporate Bond Ledger
    def test_normal_3(self, db):
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

        # Execute
        create_ledger.create_ledger(token_address_1, db)

        # assertion
        _ledger = db.query(Ledger).first()
        assert _ledger.id == 1
        assert _ledger.token_address == token_address_1
        assert _ledger.token_type == TokenType.IBET_STRAIGHT_BOND
        now_ymd = datetime.now(pytz.timezone(TZ)).strftime("%Y/%m/%d")
        assert _ledger.ledger == {
            "原簿作成日": now_ymd,
            "原簿名称": "",
            "項目": {
                "社債の説明": "",
                "社債の総額": None,
                "各社債の金額": None,
                "払込情報": {
                    "払込金額": None,
                    "払込日": "",
                    "払込状況": None
                },
                "社債の種類": "",
                "社債原簿管理人": {
                    "氏名または名称": "",
                    "住所": "",
                    "事務取扱場所": ""
                },
            },
            "権利": [
                {
                    "権利名称": "社債",
                    "項目": {},
                    "明細": [
                        {
                            "アカウントアドレス": user_address_2,
                            "氏名または名称": "name_test_con_2",
                            "住所": "address_test_con_2",
                            "保有口数": 220,
                            "一口あたりの金額": 20,
                            "保有残高": 220 * 20,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                        {
                            "アカウントアドレス": user_address_2,
                            "氏名または名称": "name_test_con_2",
                            "住所": "address_test_con_2",
                            "保有口数": 42,
                            "一口あたりの金額": 20,
                            "保有残高": 42 * 20,
                            "取得日": "2022/01/02",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                        {
                            "アカウントアドレス": user_address_1,
                            "氏名または名称": "name_test_db_1",
                            "住所": "address_test_db_1",
                            "保有口数": 110,
                            "一口あたりの金額": 20,
                            "保有残高": 110 * 20,
                            "取得日": "2022/01/01",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                        {
                            "アカウントアドレス": user_address_1,
                            "氏名または名称": "name_test_db_1",
                            "住所": "address_test_db_1",
                            "保有口数": 70,
                            "一口あたりの金額": 20,
                            "保有残高": 70 * 20,
                            "取得日": "2022/01/02",
                            "金銭以外の財産給付情報": {
                                "財産の価格": "-",
                                "給付日": "-",
                            },
                            "債権相殺情報": {
                                "相殺する債権額": "-",
                                "相殺日": "-",
                            },
                            "質権情報": {
                                "質権者の氏名または名称": "-",
                                "質権者の住所": "-",
                                "質権の目的である債券": "-",
                            },
                            "備考": "-",
                        },
                    ]
                },
            ]
        }
        assert _ledger.country_code == "JPN"

    # <Normal_4>
    # SKIP: Not Exist Template
    @mock.patch("batch.lib.create_ledger.SYSTEM_LOCALE", ["USA"])
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

    # <Normal_5>
    # SKIP: Not Exist Template
    @mock.patch("batch.lib.create_ledger.SYSTEM_LOCALE", ["USA"])
    def test_normal_5(self, db):
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

    # <Normal_6>
    # SKIP: Other Token Type
    def test_normal_6(self, db):
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
