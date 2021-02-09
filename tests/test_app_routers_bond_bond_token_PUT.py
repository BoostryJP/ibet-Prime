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
import eth_keyfile

from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

import config

from app.model.db import Account, Token, TokenType

from tests.account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAppRoutersBondBondTokensGET:
    # テスト対象API
    apiurl = "/bond/token"

    ###########################################################################
    # 正常系
    ###########################################################################

    # ＜正常系1＞
    def test_normal_1(self, client, db):
        local_account = web3.eth.account.create()
        address = to_checksum_address(local_account.address)
        keyfile_json = eth_keyfile.create_keyfile_json(
            private_key=local_account.key,
            password=config.KEY_FILE_PASSWORD.encode("utf-8"),
            kdf="pbkdf2"
        )

        account = Account()
        account.issuer_address = address
        account.keyfile = keyfile_json
        db.add(account)

        token_before = db.query(Token).all()

        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.005,
            "interest_payment_date": [
                "interest_payment_date1_test1", "interest_payment_date2_test1",
                "interest_payment_date3_test1", "interest_payment_date4_test1",
                "interest_payment_date5_test1", "interest_payment_date6_test1",
                "interest_payment_date7_test1", "interest_payment_date8_test1",
                "interest_payment_date9_test1", "interest_payment_date10_test1",
                "interest_payment_date11_test1", "interest_payment_date12_test1",
            ],
            "transferable": True,
            "is_redeemed": True,
            "status": True,
            "initial_offering_status": True,
            "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
            "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
            "image_url": [
                "http://hoge1.test/test1.png",
                "http://hoge2.test/test1.png",
                "http://hoge3.test/test1.png",
            ],
            "contact_information": "contact_information_test1",
            "privacy_policy": "privacy_policy_test1",
        }

        resp = client.put(self.apiurl, json=req_param, headers={"issuer-address": address})

        token_after = db.query(Token).all()

        assert resp.status_code == 200
        assert resp.json()["token_address"] is not None

        assert 0 == len(token_before)
        assert 1 == len(token_after)
        token_1 = token_after[0]
        assert token_1.id == 1
        assert token_1.type == TokenType.IBET_STRAIGHT_BOND
        assert token_1.tx_hash is not None
        assert token_1.issuer_address == address
        assert token_1.token_address == resp.json()["token_address"]
        assert token_1.abi is not None

    ###########################################################################
    # エラー系
    ###########################################################################

    # ＜エラー系1＞
    # パラメータエラー
    def test_error_1(self, client, db):
        resp = client.put(self.apiurl, headers={"issuer-address": ""})
        assert resp.status_code == 422
        assert resp.json()["meta"] == {
            "code": 1,
            "title": "RequestValidationError"
        }
        assert resp.json()["detail"] is not None

    # ＜エラー系2＞
    # DBに存在しないアドレス
    def test_error_2(self, client, db):
        local_account = web3.eth.account.create()
        address = to_checksum_address(local_account.address)
        keyfile_json = eth_keyfile.create_keyfile_json(
            private_key=local_account.key,
            password=config.KEY_FILE_PASSWORD.encode("utf-8"),
            kdf="pbkdf2"
        )

        account = Account()
        account.issuer_address = address
        account.keyfile = keyfile_json
        db.add(account)

        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.005,
            "interest_payment_date": [
                "interest_payment_date1_test1", "interest_payment_date2_test1",
                "interest_payment_date3_test1", "interest_payment_date4_test1",
                "interest_payment_date5_test1", "interest_payment_date6_test1",
                "interest_payment_date7_test1", "interest_payment_date8_test1",
                "interest_payment_date9_test1", "interest_payment_date10_test1",
                "interest_payment_date11_test1", "interest_payment_date12_test1",
            ],
            "transferable": True,
            "is_redeemed": True,
            "status": True,
            "initial_offering_status": True,
            "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
            "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
            "image_url": [
                "http://hoge1.test/test1.png",
                "http://hoge2.test/test1.png",
                "http://hoge3.test/test1.png",
            ],
            "contact_information": "contact_information_test1",
            "privacy_policy": "privacy_policy_test1",
        }

        resp = client.put(self.apiurl, json=req_param,
                          headers={"issuer-address": eth_account["issuer"]["account_address"]})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "title": "InvalidParameterError"
        }
        assert resp.json()["detail"] == ["issuer does not exist"]

    # ＜エラー系3＞
    # トランザクション送信エラー(keyfileが他アカウントのもの)
    def test_error_3(self, client, db):
        local_account_1 = web3.eth.account.create()
        address = to_checksum_address(local_account_1.address)

        local_account_2 = web3.eth.account.create()
        keyfile_json = eth_keyfile.create_keyfile_json(
            private_key=local_account_2.key,
            password=config.KEY_FILE_PASSWORD.encode("utf-8"),
            kdf="pbkdf2"
        )

        account = Account()
        account.issuer_address = address
        account.keyfile = keyfile_json
        db.add(account)

        req_param = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 10000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "redemption_value_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.005,
            "interest_payment_date": [
                "interest_payment_date1_test1", "interest_payment_date2_test1",
                "interest_payment_date3_test1", "interest_payment_date4_test1",
                "interest_payment_date5_test1", "interest_payment_date6_test1",
                "interest_payment_date7_test1", "interest_payment_date8_test1",
                "interest_payment_date9_test1", "interest_payment_date10_test1",
                "interest_payment_date11_test1", "interest_payment_date12_test1",
            ],
            "transferable": True,
            "is_redeemed": True,
            "status": True,
            "initial_offering_status": True,
            "tradable_exchange_contract_address": "0x1234567890abCdFe1234567890ABCdFE12345678",
            "personal_info_contract_address": "0x1234567890aBcDFE1234567890abcDFE12345679",
            "image_url": [
                "http://hoge1.test/test1.png",
                "http://hoge2.test/test1.png",
                "http://hoge3.test/test1.png",
            ],
            "contact_information": "contact_information_test1",
            "privacy_policy": "privacy_policy_test1",
        }

        resp = client.put(self.apiurl, json=req_param, headers={"issuer-address": address})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 2,
            "title": "SendTransactionError"
        }
        assert resp.json()["detail"] == ["failed to send transaction"]
