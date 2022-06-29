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
from app.utils.e2ee_utils import E2EEUtils
from app.model.blockchain import (
    IbetStraightBondContract,
    PersonalInfoContract
)
from app.exceptions import SendTransactionError
from tests.account_config import config_eth_account


class TestAppRoutersBondTokensTokenAddressHoldersAccountAddressPersonalInfoPOST:
    # target API endpoint
    test_url = "/bond/tokens/{}/holders/{}/personal_info"

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
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = "personal_info_contract_address"
        IbetStraightBondContract_get = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract
        )
        PersonalInfoContract_init = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.__init__",
            return_value=None
        )
        PersonalInfoContract_modify_info = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.modify_info",
            return_value=None
        )

        with IbetStraightBondContract_get, PersonalInfoContract_init, PersonalInfoContract_modify_info:
            # request target API
            req_param = {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10
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
            assert resp.json() is None
            IbetStraightBondContract.get.assert_called_with(_token_address)
            PersonalInfoContract.__init__.assert_called_with(
                db=db,
                issuer_address=_issuer_address,
                contract_address="personal_info_contract_address"
            )
            PersonalInfoContract.modify_info.assert_called_with(
                account_address=_test_account_address,
                data=req_param,
                default_value=None
            )

    # <Normal_2>
    # Nullable items
    def test_normal_2(self, client, db):
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
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = "personal_info_contract_address"
        IbetStraightBondContract_get = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract
        )
        PersonalInfoContract_init = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.__init__",
            return_value=None
        )
        PersonalInfoContract_modify_info = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.modify_info",
            return_value=None
        )

        with IbetStraightBondContract_get, PersonalInfoContract_init, PersonalInfoContract_modify_info:
            # request target API
            req_param = {
                "key_manager": "test_key_manager",
                "name": None,
                "postal_code": None,
                "address": None,
                "email": None,
                "birth": None,
                "is_corporate": None,
                "tax_category": None
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
            assert resp.json() is None
            IbetStraightBondContract.get.assert_called_with(_token_address)
            PersonalInfoContract.__init__.assert_called_with(
                db=db,
                issuer_address=_issuer_address,
                contract_address="personal_info_contract_address"
            )
            PersonalInfoContract.modify_info.assert_called_with(
                account_address=_test_account_address,
                data=req_param,
                default_value=None
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
            "birth": None,
            "is_corporate": None,
            "tax_category": None
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
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10
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
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10
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
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10
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
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10
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
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10
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
    # HTTPException 404
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
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10
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
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "NotFound"
            },
            "detail": "token not found"
        }

    # <Error_9>
    # InvalidParameterError
    # processing token
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
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        token.token_status = 0
        db.add(token)

        # request target API
        req_param = {
            "key_manager": "test_key_manager",
            "name": "test_name",
            "postal_code": "test_postal_code",
            "address": "test_address",
            "email": "test_email",
            "birth": "test_birth",
            "is_corporate": False,
            "tax_category": 10
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
            "detail": "wait for a while as the token is being processed"
        }

    # <Error_10>
    # SendTransactionError
    def test_error_10(self, client, db):
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
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.tx_hash = ""
        token.issuer_address = _issuer_address
        token.token_address = _token_address
        token.abi = ""
        db.add(token)

        # mock
        ibet_bond_contract = IbetStraightBondContract()
        ibet_bond_contract.personal_info_contract_address = "personal_info_contract_address"
        IbetStraightBondContract_get = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.get",
            return_value=ibet_bond_contract
        )
        PersonalInfoContract_init = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.__init__",
            return_value=None
        )
        PersonalInfoContract_modify_info = patch(
            target="app.model.blockchain.personal_info.PersonalInfoContract.modify_info",
            side_effect=SendTransactionError()
        )

        with IbetStraightBondContract_get, PersonalInfoContract_init, PersonalInfoContract_modify_info:
            # request target API
            req_param = {
                "key_manager": "test_key_manager",
                "name": "test_name",
                "postal_code": "test_postal_code",
                "address": "test_address",
                "email": "test_email",
                "birth": "test_birth",
                "is_corporate": False,
                "tax_category": 10
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
