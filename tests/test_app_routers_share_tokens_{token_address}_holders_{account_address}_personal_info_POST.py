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
from unittest.mock import patch

from app.model.db import (
    Account,
    Token,
    TokenType
)
from app.model.utils import E2EEUtils
from app.model.blockchain import (
    IbetShareContract,
    PersonalInfoContract
)
from app.exceptions import SendTransactionError
from tests.account_config import config_eth_account


class TestAppRoutersShareTokensTokenAddressHoldersAccountAddressPersonalInfoPOST:
    # target API endpoint
    test_url = "/share/tokens/{}/holders/{}/personal_info"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # mock
        ibet_share_contract = IbetShareContract()
        ibet_share_contract.personal_info_contract_address = "personal_info_contract_address"
        IbetShareContract_get = patch(
            target="app.model.blockchain.token.IbetShareContract.get",
            return_value=ibet_share_contract
        )
        PersonalInfoContract_init = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.__init__",
            return_value=None
        )
        PersonalInfoContract_modify_info = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.modify_info",
            return_value=None
        )

        with IbetShareContract_get, PersonalInfoContract_init, PersonalInfoContract_modify_info:
            # request target API
            req_param = {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth"
            }
            resp = client.post(
                self.test_url.format(_token_address, _test_account_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

            # assertion
            assert resp.status_code == 200
            IbetShareContract.get.assert_called_with(_token_address)
            PersonalInfoContract.__init__.assert_called_with(
                db=db,
                issuer_address=_issuer_address,
                contract_address="personal_info_contract_address"
            )
            PersonalInfoContract.modify_info.assert_called_with(
                account_address=_test_account_address,
                data=req_param
            )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # headers and body required
    def test_error_1(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address)
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }, {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_2>
    # RequestValidationError
    # personal_info
    def test_error_2(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail":  [
                {
                    "loc": ["body", "key_manager"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed"
                }, {
                    "loc": ["body", "name"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed"
                }, {
                    "loc": ["body", "postal_code"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed"
                }, {
                    "loc": ["body", "address"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed"
                }, {
                    "loc": ["body", "email"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed"
                }, {
                    "loc": ["body", "birth"],
                    "msg": "none is not an allowed value",
                    "type": "type_error.none.not_allowed"
                }
            ]
        }

    # <Error_3>
    # RequestValidationError
    # issuer_address
    def test_error_3(self, client, db):
        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth"
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": "test_issuer_address",
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error"
                }
            ]
        }

    # <Error_4>
    # RequestValidationError
    # eoa-password required
    def test_error_4(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth"
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": None
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "eoa-password"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }

    # <Error_5>
    # RequestValidationError
    # eoa-password not encrypted
    def test_error_5(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth"
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": "not_encrypted_password"
            }
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error"
                }
            ]
        }

    # <Error_6>
    # AuthorizationError
    # issuer does not exist
    def test_error_6(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # request target API
        req_param = {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth"
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
        }

    # <Error_7>
    # AuthorizationError
    # password mismatch
    def test_error_7(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth"
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("mismatch_password")
            }
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "AuthorizationError"
            },
            "detail": "issuer does not exist, or password mismatch"
        }

    # <Error_8>
    # InvalidParameterError
    # token not found
    def test_error_8(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        # request target API
        req_param = {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth"
        }
        resp = client.post(
            self.test_url.format(_token_address, _test_account_address),
            json=req_param,
            headers={
                "issuer-address": _issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "token not found"
        }

    # <Error_9>
    # SendTransactionError
    def test_error_9(self, client, db):
        _issuer_account = config_eth_account("user1")
        _issuer_address = _issuer_account["address"]
        _issuer_keyfile = _issuer_account["keyfile_json"]

        _test_account = config_eth_account("user2")
        _test_account_address = _test_account["address"]

        _token_address = "0xd9F55747DE740297ff1eEe537aBE0f8d73B7D783"

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _issuer_keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        token = Token()
        token.type = TokenType.IBET_SHARE
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # mock
        ibet_share_contract = IbetShareContract()
        ibet_share_contract.personal_info_contract_address = "personal_info_contract_address"
        IbetShareContract_get = patch(
            target="app.model.blockchain.token.IbetShareContract.get",
            return_value=ibet_share_contract
        )
        PersonalInfoContract_init = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.__init__",
            return_value=None
        )
        PersonalInfoContract_modify_info = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.modify_info",
            side_effect=SendTransactionError()
        )

        with IbetShareContract_get, PersonalInfoContract_init, PersonalInfoContract_modify_info:
            # request target API
            req_param = {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth"
            }
            resp = client.post(
                self.test_url.format(_token_address, _test_account_address),
                json=req_param,
                headers={
                    "issuer-address": _issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

            # assertion
            assert resp.status_code == 400
            assert resp.json() == {
                "meta": {
                    "code": 2,
                    "title": "SendTransactionError"
                },
                "detail": "failed to modify personal information"
            }
