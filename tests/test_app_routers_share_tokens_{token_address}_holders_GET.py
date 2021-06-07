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
from app.model.db import (
    Account,
    Token,
    TokenType,
    IDXPosition,
    IDXPersonalInfo
)
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressHoldersGET:
    # target API endpoint
    base_url = "/share/tokens/{}/holders"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    def test_normal_1(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == []

    # <Normal_2>
    # 1 record
    def test_normal_2(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.pending_transfer = 5
        db.add(idx_position_1)

        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = _account_address_1
        idx_personal_info_1.issuer_address = _issuer_address
        idx_personal_info_1.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
        }
        db.add(idx_personal_info_1)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "account_address": _account_address_1,
                "personal_information": {
                    "key_manager": "key_manager_test1",
                    "name": "name_test1",
                    "postal_code": "postal_code_test1",
                    "address": "address_test1",
                    "email": "email_test1",
                    "birth": "birth_test1"
                },
                "balance": 10,
                "pending_transfer": 5
            }
        ]

    # <Normal_3>
    # Multi record
    def test_normal_3(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"
        _account_address_1 = "0xb75c7545b9230FEe99b7af370D38eBd3DAD929f7"
        _account_address_2 = "0x3F198534Bbe3B2a197d3B317d41392F348EAC707"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        idx_position_1 = IDXPosition()
        idx_position_1.token_address = _token_address
        idx_position_1.account_address = _account_address_1
        idx_position_1.balance = 10
        idx_position_1.pending_transfer = 5
        db.add(idx_position_1)

        idx_personal_info_1 = IDXPersonalInfo()
        idx_personal_info_1.account_address = _account_address_1
        idx_personal_info_1.issuer_address = _issuer_address
        idx_personal_info_1.personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1"
        }
        db.add(idx_personal_info_1)

        idx_position_2 = IDXPosition()
        idx_position_2.token_address = _token_address
        idx_position_2.account_address = _account_address_2
        idx_position_2.balance = 20
        idx_position_2.pending_transfer = 10
        db.add(idx_position_2)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "account_address": _account_address_1,
                "personal_information": {
                    "key_manager": "key_manager_test1",
                    "name": "name_test1",
                    "postal_code": "postal_code_test1",
                    "address": "address_test1",
                    "email": "email_test1",
                    "birth": "birth_test1"
                },
                "balance": 10,
                "pending_transfer": 5
            },
            {
                "account_address": _account_address_2,
                "personal_information": {
                    "key_manager": None,
                    "name": None,
                    "postal_code": None,
                    "address": None,
                    "email": None,
                    "birth": None
                },
                "balance": 20,
                "pending_transfer": 10
            }
        ]

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    def test_error_1(self, client, db):
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": "0x0"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [{
                "loc": ["header", "issuer-address"],
                "msg": "issuer-address is not a valid address",
                "type": "value_error"
            }]
        }

    # <Error_2>
    # InvalidParameterError: issuer does not exist
    def test_error_2(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "issuer does not exist"
        }

    # <Error_3>
    # HTTPException 404: token not found
    def test_error_3(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address
            }
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
        }

    # <Error_4>
    # InvalidParameterError: processing token
    def test_error_4(self, client, db):
        user = config_eth_account("user1")
        _issuer_address = user["address"]
        _token_address = "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb"

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        db.add(token)

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        db.add(account)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            headers={
                "issuer-address": _issuer_address
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "wait for a while as the token is being processed"
        }
