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
import pytest
from datetime import datetime, timezone, timedelta

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_keyfile import decode_keyfile_json

from config import WEB3_HTTP_PROVIDER, CHAIN_ID, TX_GAS_LIMIT
from app.model.utils import E2EEUtils
from app.model.blockchain import IbetShareContract, IbetStraightBondContract, PersonalInfoContract
from app.model.blockchain.utils import ContractUtils
from app.model.db import Token, TokenType, UTXO, BondLedger, IDXPersonalInfo, CorporateBondLedgerTemplateJPN, Account, \
    AccountRsaStatus
from app.model.schema import IbetShareTransfer, IbetStraightBondTransfer, IbetStraightBondUpdate
from batch.processor_create_utxo import Sinks, DBSink, Processor
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

JST = timezone(timedelta(hours=+9), "JST")


@pytest.fixture(scope='function')
def processor(db):
    _sink = Sinks()
    _sink.register(DBSink(db))
    return Processor(sink=_sink, db=db)


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

    if personal_info_contract_address:
        data = IbetStraightBondUpdate()
        data.personal_info_contract_address = personal_info_contract_address
        IbetStraightBondContract.update(contract_address, data, address, private_key)

    return contract_address


def deploy_share_token_contract(address, private_key):
    arguments = [
        "token.name",
        "token.symbol",
        100,
        20,
        int(0.03 * 100),
        "token.dividend_record_date",
        "token.dividend_payment_date",
        "token.cancellation_date"
    ]

    contract_address, _, _ = IbetShareContract.create(arguments, address, private_key)

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


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Skip(Other than Bond)
    def test_normal_1(self, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]

        # prepare data
        token_address_1 = deploy_share_token_contract(issuer_address, issuer_private_key)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        # Execute Transfer Event
        _transfer_1 = IbetShareTransfer(
            token_address=token_address_1,
            transfer_from=issuer_address,
            transfer_to=user_address_1,
            amount=10
        )
        IbetShareContract.transfer(_transfer_1, issuer_address, issuer_private_key)

        # Execute batch
        processor.process()

        # assertion
        _bond_ledger_list = db.query(BondLedger).all()
        assert len(_bond_ledger_list) == 0

    # <Normal_2>
    # BondInfo:default, PersonalInfo:from DB
    def test_normal_2(self, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]

        # prepare data
        personal_info_contract_address = deploy_personal_info_contract(issuer_address, issuer_private_key)
        token_address_1 = deploy_bond_token_contract(issuer_address, issuer_private_key,
                                                     personal_info_contract_address)
        _token_1 = Token()
        _token_1.type = TokenType.IBET_STRAIGHT_BOND
        _token_1.tx_hash = ""
        _token_1.issuer_address = issuer_address
        _token_1.token_address = token_address_1
        _token_1.abi = {}
        db.add(_token_1)

        token_address_2 = deploy_bond_token_contract(issuer_address, issuer_private_key,
                                                     personal_info_contract_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_STRAIGHT_BOND
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        _idx_personal_info_1 = IDXPersonalInfo()
        _idx_personal_info_1.account_address = user_address_1
        _idx_personal_info_1.issuer_address = issuer_address
        _idx_personal_info_1.personal_info = {
            "name": "name_test_db_1",
            "address": "address_test_db_1",
        }
        db.add(_idx_personal_info_1)

        _idx_personal_info_2 = IDXPersonalInfo()
        _idx_personal_info_2.account_address = user_address_2
        _idx_personal_info_2.issuer_address = issuer_address
        _idx_personal_info_2.personal_info = {
            "name": "name_test_db_2",
            "address": "address_test_db_2",
        }
        db.add(_idx_personal_info_2)

        _utxo_1 = UTXO()
        _utxo_1.transaction_hash = "tx1"
        _utxo_1.account_address = user_address_1
        _utxo_1.token_address = token_address_2
        _utxo_1.amount = 100
        _utxo_1.block_number = 1
        _utxo_1.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_1)

        _utxo_2 = UTXO()
        _utxo_2.transaction_hash = "tx2"
        _utxo_2.account_address = user_address_2
        _utxo_2.token_address = token_address_2
        _utxo_2.amount = 200
        _utxo_2.block_number = 1
        _utxo_2.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_2)

        # Execute Transfer Event
        # Bond 1:issuer -> user1
        _transfer_1 = IbetStraightBondTransfer(
            token_address=token_address_1,
            transfer_from=issuer_address,
            transfer_to=user_address_1,
            amount=40
        )
        IbetStraightBondContract.transfer(_transfer_1, issuer_address, issuer_private_key)

        # Bond 1:issuer -> user2
        _transfer_2 = IbetStraightBondTransfer(
            token_address=token_address_1,
            transfer_from=issuer_address,
            transfer_to=user_address_2,
            amount=20
        )
        IbetStraightBondContract.transfer(_transfer_2, issuer_address, issuer_private_key)

        # Bond 1:user1 -> user2
        _transfer_3 = IbetShareTransfer(
            token_address=token_address_1,
            transfer_from=user_address_1,
            transfer_to=user_address_2,
            amount=5
        )
        IbetShareContract.transfer(_transfer_3, issuer_address, issuer_private_key)

        # Bond 2:issuer -> user2
        _transfer_4 = IbetStraightBondTransfer(
            token_address=token_address_2,
            transfer_from=issuer_address,
            transfer_to=user_address_2,
            amount=90
        )
        IbetStraightBondContract.transfer(_transfer_4, issuer_address, issuer_private_key)

        # Execute batch
        created_date = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(JST).strftime("%Y/%m/%d")
        processor.process()

        # assertion
        _bond_ledger_list = db.query(BondLedger).all()
        assert len(_bond_ledger_list) == 4
        _bond_ledger = _bond_ledger_list[0]
        assert _bond_ledger.id == 1
        assert _bond_ledger.token_address == token_address_1
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "",
                "社債の説明": "",
                "社債の総額": None,
                "各社債の金額": None,
                "払込情報": {
                    "払込金額": None,
                    "払込日": "",
                    "払込状況": None
                },
                "社債の種類": ""
            },
            "社債原簿管理人": {
                "氏名または名称": "",
                "住所": "",
                "事務取扱場所": ""
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_db_1",
                    "住所": "address_test_db_1",
                    "社債金額": 20 * 40,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None
        _bond_ledger = _bond_ledger_list[1]
        assert _bond_ledger.id == 2
        assert _bond_ledger.token_address == token_address_1
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "",
                "社債の説明": "",
                "社債の総額": None,
                "各社債の金額": None,
                "払込情報": {
                    "払込金額": None,
                    "払込日": "",
                    "払込状況": None
                },
                "社債の種類": ""
            },
            "社債原簿管理人": {
                "氏名または名称": "",
                "住所": "",
                "事務取扱場所": ""
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_db_1",
                    "住所": "address_test_db_1",
                    "社債金額": 20 * 40,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_db_2",
                    "住所": "address_test_db_2",
                    "社債金額": 20 * 20,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None
        _bond_ledger = _bond_ledger_list[2]
        assert _bond_ledger.id == 3
        assert _bond_ledger.token_address == token_address_1
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "",
                "社債の説明": "",
                "社債の総額": None,
                "各社債の金額": None,
                "払込情報": {
                    "払込金額": None,
                    "払込日": "",
                    "払込状況": None
                },
                "社債の種類": ""
            },
            "社債原簿管理人": {
                "氏名または名称": "",
                "住所": "",
                "事務取扱場所": ""
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_db_1",
                    "住所": "address_test_db_1",
                    "社債金額": 20 * 35,  # spend to user2(40 - 5)
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_db_2",
                    "住所": "address_test_db_2",
                    "社債金額": 20 * 25,  # spend from user1(20 + 5)
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None
        _bond_ledger = _bond_ledger_list[3]
        assert _bond_ledger.id == 4
        assert _bond_ledger.token_address == token_address_2
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "",
                "社債の説明": "",
                "社債の総額": None,
                "各社債の金額": None,
                "払込情報": {
                    "払込金額": None,
                    "払込日": "",
                    "払込状況": None
                },
                "社債の種類": ""
            },
            "社債原簿管理人": {
                "氏名または名称": "",
                "住所": "",
                "事務取扱場所": ""
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_db_1",
                    "住所": "address_test_db_1",
                    "社債金額": 20 * 100,  # pre registered UTXO amount
                    "取得日": "2022/01/01",  # pre registered UTXO datetime(UTC->JST)
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_db_2",
                    "住所": "address_test_db_2",
                    "社債金額": 20 * 90,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_db_2",
                    "住所": "address_test_db_2",
                    "社債金額": 20 * 200,  # pre registered UTXO amount
                    "取得日": "2022/01/01",  # pre registered UTXO datetime(UTC->JST)
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None

    # <Normal_3>
    # BondInfo:from Template, PersonalInfo:from Contract
    def test_normal_3(self, processor, db):
        user_1 = config_eth_account("user1")
        issuer_address = user_1["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=user_1["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_2 = config_eth_account("user2")
        user_address_1 = user_2["address"]
        user_private_key_1 = decode_keyfile_json(
            raw_keyfile_json=user_2["keyfile_json"],
            password="password".encode("utf-8")
        )
        user_3 = config_eth_account("user3")
        user_address_2 = user_3["address"]
        user_private_key_2 = decode_keyfile_json(
            raw_keyfile_json=user_3["keyfile_json"],
            password="password".encode("utf-8")
        )

        # prepare data
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = user_1["keyfile_json"]
        _account.eoa_password = E2EEUtils.encrypt("password")
        _account.rsa_private_key = user_1["rsa_private_key"]
        _account.rsa_public_key = user_1["rsa_public_key"]
        _account.rsa_passphrase = E2EEUtils.encrypt("password")
        _account.rsa_status = AccountRsaStatus.SET.value
        db.add(_account)

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

        token_address_2 = deploy_bond_token_contract(issuer_address, issuer_private_key,
                                                     personal_info_contract_address)
        _token_2 = Token()
        _token_2.type = TokenType.IBET_STRAIGHT_BOND
        _token_2.tx_hash = ""
        _token_2.issuer_address = issuer_address
        _token_2.token_address = token_address_2
        _token_2.abi = {}
        db.add(_token_2)

        _template_1 = CorporateBondLedgerTemplateJPN()
        _template_1.token_address = token_address_1
        _template_1.issuer_address = issuer_address
        _template_1.bond_name = "bond_name_test1"
        _template_1.bond_description = "bond_description_test1"
        _template_1.bond_type = "bond_type_test1"
        _template_1.total_amount = 1000
        _template_1.face_value = 2000
        _template_1.payment_amount = 3000
        _template_1.payment_date = "20301231"
        _template_1.payment_status = False
        _template_1.hq_name = "hq_name_test1"
        _template_1.hq_address = "hq_address_test1"
        _template_1.hq_office_address = "hq_office_address_test1"
        db.add(_template_1)

        _template_2 = CorporateBondLedgerTemplateJPN()
        _template_2.token_address = token_address_2
        _template_2.issuer_address = issuer_address
        _template_2.bond_name = "bond_name_test2"
        _template_2.bond_description = "bond_description_test2"
        _template_2.bond_type = "bond_type_test2"
        _template_2.total_amount = 4000
        _template_2.face_value = 5000
        _template_2.payment_amount = 6000
        _template_2.payment_date = "20310101"
        _template_2.payment_status = True
        _template_2.hq_name = "hq_name_test2"
        _template_2.hq_address = "hq_address_test2"
        _template_2.hq_office_address = "hq_office_address_test2"
        db.add(_template_2)

        _utxo_1 = UTXO()
        _utxo_1.transaction_hash = "tx1"
        _utxo_1.account_address = user_address_1
        _utxo_1.token_address = token_address_2
        _utxo_1.amount = 100
        _utxo_1.block_number = 1
        _utxo_1.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_1)

        _utxo_2 = UTXO()
        _utxo_2.transaction_hash = "tx2"
        _utxo_2.account_address = user_address_2
        _utxo_2.token_address = token_address_2
        _utxo_2.amount = 200
        _utxo_2.block_number = 1
        _utxo_2.block_timestamp = datetime.strptime("2021/12/31 15:20:30", '%Y/%m/%d %H:%M:%S')  # JST 2022/01/01
        db.add(_utxo_2)

        # Execute Transfer Event
        # Bond 1:issuer -> user1
        _transfer_1 = IbetStraightBondTransfer(
            token_address=token_address_1,
            transfer_from=issuer_address,
            transfer_to=user_address_1,
            amount=40
        )
        IbetStraightBondContract.transfer(_transfer_1, issuer_address, issuer_private_key)

        # Bond 1:issuer -> user2
        _transfer_2 = IbetStraightBondTransfer(
            token_address=token_address_1,
            transfer_from=issuer_address,
            transfer_to=user_address_2,
            amount=20
        )
        IbetStraightBondContract.transfer(_transfer_2, issuer_address, issuer_private_key)

        # Bond 1:user1 -> user2
        _transfer_3 = IbetShareTransfer(
            token_address=token_address_1,
            transfer_from=user_address_1,
            transfer_to=user_address_2,
            amount=5
        )
        IbetShareContract.transfer(_transfer_3, issuer_address, issuer_private_key)

        # Bond 2:issuer -> user2
        _transfer_4 = IbetStraightBondTransfer(
            token_address=token_address_2,
            transfer_from=issuer_address,
            transfer_to=user_address_2,
            amount=90
        )
        IbetStraightBondContract.transfer(_transfer_4, issuer_address, issuer_private_key)

        # Execute batch
        created_date = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(JST).strftime("%Y/%m/%d")
        processor.process()

        # assertion
        _bond_ledger_list = db.query(BondLedger).all()
        assert len(_bond_ledger_list) == 4
        _bond_ledger = _bond_ledger_list[0]
        assert _bond_ledger.id == 1
        assert _bond_ledger.token_address == token_address_1
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "bond_name_test1",
                "社債の説明": "bond_description_test1",
                "社債の総額": 1000,
                "各社債の金額": 2000,
                "払込情報": {
                    "払込金額": 3000,
                    "払込日": "20301231",
                    "払込状況": False
                },
                "社債の種類": "bond_type_test1"
            },
            "社債原簿管理人": {
                "氏名または名称": "hq_name_test1",
                "住所": "hq_address_test1",
                "事務取扱場所": "hq_office_address_test1"
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_con_1",
                    "住所": "address_test_con_1",
                    "社債金額": 20 * 40,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None
        _bond_ledger = _bond_ledger_list[1]
        assert _bond_ledger.id == 2
        assert _bond_ledger.token_address == token_address_1
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "bond_name_test1",
                "社債の説明": "bond_description_test1",
                "社債の総額": 1000,
                "各社債の金額": 2000,
                "払込情報": {
                    "払込金額": 3000,
                    "払込日": "20301231",
                    "払込状況": False
                },
                "社債の種類": "bond_type_test1"
            },
            "社債原簿管理人": {
                "氏名または名称": "hq_name_test1",
                "住所": "hq_address_test1",
                "事務取扱場所": "hq_office_address_test1"
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_con_1",
                    "住所": "address_test_con_1",
                    "社債金額": 20 * 40,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_con_2",
                    "住所": "address_test_con_2",
                    "社債金額": 20 * 20,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None
        _bond_ledger = _bond_ledger_list[2]
        assert _bond_ledger.id == 3
        assert _bond_ledger.token_address == token_address_1
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "bond_name_test1",
                "社債の説明": "bond_description_test1",
                "社債の総額": 1000,
                "各社債の金額": 2000,
                "払込情報": {
                    "払込金額": 3000,
                    "払込日": "20301231",
                    "払込状況": False
                },
                "社債の種類": "bond_type_test1"
            },
            "社債原簿管理人": {
                "氏名または名称": "hq_name_test1",
                "住所": "hq_address_test1",
                "事務取扱場所": "hq_office_address_test1"
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_con_1",
                    "住所": "address_test_con_1",
                    "社債金額": 20 * 35,  # spend to user2(40 - 5)
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_con_2",
                    "住所": "address_test_con_2",
                    "社債金額": 20 * 25,  # spend from user1(20 + 5)
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None
        _bond_ledger = _bond_ledger_list[3]
        assert _bond_ledger.id == 4
        assert _bond_ledger.token_address == token_address_2
        assert _bond_ledger.ledger == {
            "社債原簿作成日": created_date,
            "社債情報": {
                "社債名称": "bond_name_test2",
                "社債の説明": "bond_description_test2",
                "社債の総額": 4000,
                "各社債の金額": 5000,
                "払込情報": {
                    "払込金額": 6000,
                    "払込日": "20310101",
                    "払込状況": True
                },
                "社債の種類": "bond_type_test2"
            },
            "社債原簿管理人": {
                "氏名または名称": "hq_name_test2",
                "住所": "hq_address_test2",
                "事務取扱場所": "hq_office_address_test2"
            },
            "社債権者": [
                {
                    "アカウントアドレス": user_address_1,
                    "氏名または名称": "name_test_con_1",
                    "住所": "address_test_con_1",
                    "社債金額": 20 * 100,  # pre registered UTXO amount
                    "取得日": "2022/01/01",  # pre registered UTXO datetime(UTC->JST)
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_con_2",
                    "住所": "address_test_con_2",
                    "社債金額": 20 * 90,
                    "取得日": created_date,
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                },
                {
                    "アカウントアドレス": user_address_2,
                    "氏名または名称": "name_test_con_2",
                    "住所": "address_test_con_2",
                    "社債金額": 20 * 200,  # pre registered UTXO amount
                    "取得日": "2022/01/01",  # pre registered UTXO datetime(UTC->JST)
                    "金銭以外の財産給付情報": {
                        "財産の価格": "-",
                        "給付日": "-"
                    },
                    "債権相殺情報": {
                        "相殺する債権額": "-",
                        "相殺日": "-"
                    },
                    "質権情報": {
                        "質権者の氏名または名称": "-",
                        "質権者の住所": "-",
                        "質権の目的である債券": "-"
                    },
                    "備考": "-"
                }
            ]
        }
        assert _bond_ledger.country_code == "JPN"
        assert _bond_ledger.bond_ledger_created is not None

    ###########################################################################
    # Error Case
    ###########################################################################
