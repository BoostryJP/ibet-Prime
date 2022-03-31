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
from unittest import mock
from unittest.mock import (
    ANY,
    MagicMock
)
from datetime import datetime

from pytz import timezone

import config
from app.model.db import (
    Account,
    Token,
    TokenType,
    AdditionalTokenInfo,
    IDXTransferApproval
)
from app.model.schema import (
    IbetSecurityTokenApproveTransfer,
    IbetSecurityTokenEscrowApproveTransfer
)
from app.utils.e2ee_utils import E2EEUtils
from app.exceptions import SendTransactionError

from tests.account_config import config_eth_account

local_tz = timezone(config.TZ)


class TestAppRoutersShareTransferApprovalsTokenAddressIdPOST:
    # target API endpoint
    base_url = "/share/transfer_approvals/{}/{}"

    test_transaction_hash = "test_transaction_hash"

    test_token_address = "test_token_address"
    test_exchange_address = "0x1234567890aBcDFE1234567890abcDFE12345679"
    test_from_address = "test_from_address"
    test_to_address = "test_to_address"
    test_application_datetime = datetime(year=2019, month=9, day=1)
    test_application_datetime_str = timezone("UTC").localize(test_application_datetime).astimezone(local_tz).isoformat()
    test_application_blocktimestamp = datetime(year=2019, month=9, day=2)
    test_application_blocktimestamp_str = timezone("UTC").localize(test_application_blocktimestamp).astimezone(
        local_tz).isoformat()
    test_approval_datetime = datetime(year=2019, month=9, day=3)
    test_approval_blocktimestamp = datetime(year=2019, month=9, day=4)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # APPROVE
    # token
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_1_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # mock
        IbetSecurityTokenContract_approve_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 1})
        )

        # request target API
        with IbetSecurityTokenContract_approve_transfer as mock_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={
                    "operation_type": "approve"
                },
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _expected = {
            "application_id": 100,
            "data": str(datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            contract_address=self.test_token_address,
            data=IbetSecurityTokenApproveTransfer(**_expected),
            tx_from=issuer_address,
            private_key=ANY
        )

    # <Normal_1_2>
    # APPROVE
    # exchange
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_1_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # mock
        IbetSecurityTokenEscrow_approve_transfer = mock.patch(
            target="app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
            return_value=("test_tx_hash", {"status": 1})
        )

        # request target API
        with IbetSecurityTokenEscrow_approve_transfer as mock_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={
                    "operation_type": "approve"
                },
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password")
                }
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _expected = {
            "escrow_id": 100,
            "data": str(datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            data=IbetSecurityTokenEscrowApproveTransfer(**_expected),
            tx_from=issuer_address,
            private_key=ANY
        )

    # <Normal_2_1>
    # CANCEL
    # token
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # mock
        IbetSecurityTokenContract_cancel_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
            return_value=("test_tx_hash", {"status": 1})
        )

        # request target API
        with IbetSecurityTokenContract_cancel_transfer as mock_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password")
                },
                json={
                    "operation_type": "cancel"
                }
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _expected = {
            "application_id": 100,
            "data": str(datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            contract_address=self.test_token_address,
            data=IbetSecurityTokenApproveTransfer(**_expected),
            tx_from=issuer_address,
            private_key=ANY
        )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # Validation Error
    # missing headers: issuer-address, body
    def test_error_1_1(self, client, db):
        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
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
                },
                {
                    "loc": ["body"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_1_2>
    # Validation Error
    # missing body: operation_type
    def test_error_1_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={},
            headers={
                "issuer-address": issuer_address,
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
                    "loc": ["body", "operation_type"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
            ]
        }

    # <Error_1_3>
    # Validation Error
    # missing headers: eoa-password
    def test_error_1_3(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
                },
            ]
        }

    # <Error_1_4>
    # Validation Error
    # invalid value: body
    def test_error_1_4(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "test"
            },
            headers={
                "issuer-address": issuer_address,
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
                    "loc": ["body", "operation_type"],
                    "ctx": {"enum_values": ["approve", "cancel"]},
                    "msg": "value is not a valid enumeration member; permitted: 'approve', 'cancel'",
                    "type": "type_error.enum"
                },
            ]
        }

    # <Error_1_5>
    # Validation Error
    # invalid value: header
    def test_error_1_5(self, client, db):
        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": "issuer_address",
                "eoa-password": "password"
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
                },
                {
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error"
                }
            ]
        }

    # <Error_2_1>
    # Authorize Error
    # not account
    def test_error_2_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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

    # <Error_2_2>
    # Authorize Error
    # invalid password
    def test_error_2_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password_test")
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

    # <Error_3_1>
    # Not Found Error
    # token
    def test_error_3_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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

    # <Error_3_2>
    # Not Found Error
    # transfer approval
    def test_error_3_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
            "detail": "transfer approval not found"
        }

    # <Error_4_1>
    # Invalid Parameter Error
    # processing Token
    def test_error_4_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.token_status = 0
        db.add(_token)

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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

    # <Error_4_2>
    # Invalid Parameter Error
    # already approved
    def test_error_4_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = self.test_approval_blocktimestamp
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
            "detail": "already approved"
        }

    # <Error_4_3>
    # Invalid Parameter Error
    # canceled application
    def test_error_4_3(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = True
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
            "detail": "canceled application"
        }

    # <Error_4_4>
    # Invalid Parameter Error
    # application that cannot be canceled
    def test_error_4_4(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = False
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            },
            json={
                "operation_type": "cancel"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "application that cannot be canceled"
        }

    # <Error_4_5>
    # Invalid Parameter Error
    # token is automatic approval
    # unset is_manual_transfer_approval
    def test_error_4_5(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = None  # not target
        db.add(additional_info)

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
            "detail": "token is automatic approval"
        }

    # <Error_4_6>
    # Invalid Parameter Error
    # token is automatic approval
    # is_manual_transfer_approval is automatic
    def test_error_4_6(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = False
        db.add(additional_info)

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
            "detail": "token is automatic approval"
        }

    # <Error_5_1>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenInterface.approve_transfer
    # raise SendTransactionError
    @mock.patch(
        "app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
        MagicMock(side_effect=SendTransactionError()))
    def test_error_5_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # request target API
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
            "detail": "failed to send transaction"
        }

    # <Error_5_2>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenInterface.approve_transfer
    # return fail
    def test_error_5_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # mock
        IbetSecurityTokenContract_approve_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 0})
        )
        IbetSecurityTokenContract_cancel_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
            return_value=("test_tx_hash", {"status": 1})
        )

        # request target API
        with IbetSecurityTokenContract_approve_transfer, IbetSecurityTokenContract_cancel_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={
                    "operation_type": "approve"
                },
                headers={
                    "issuer-address": issuer_address,
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
            "detail": "failed to send transaction"
        }

    # <Error_5_3>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenEscrow.approve_transfer
    # raise SendTransactionError
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
        MagicMock(side_effect=SendTransactionError()))
    def test_error_5_3(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # request target API
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={
                "operation_type": "approve"
            },
            headers={
                "issuer-address": issuer_address,
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
            "detail": "failed to send transaction"
        }

    # <Error_5_4>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenEscrow.approve_transfer
    # return fail
    def test_error_5_4(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = self.test_exchange_address
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # mock
        IbetSecurityTokenEscrow_approve_transfer = mock.patch(
            target="app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
            return_value=("test_tx_hash", {"status": 0})
        )

        # request target API
        with IbetSecurityTokenEscrow_approve_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={
                    "operation_type": "approve"
                },
                headers={
                    "issuer-address": issuer_address,
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
            "detail": "failed to send transaction"
        }

    # <Error_6_1>
    # CANCEL
    # Send Transaction Error
    # IbetSecurityTokenInterface.cancel_transfer
    # raise SendTransactionError
    @mock.patch(
        "app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
        MagicMock(side_effect=SendTransactionError()))
    def test_error_6_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # request target API
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password")
            },
            json={
                "operation_type": "cancel"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 2,
                "title": "SendTransactionError"
            },
            "detail": "failed to send transaction"
        }

    # <Error_6_2>
    # CANCEL
    # Send Transaction Error
    # IbetSecurityTokenInterface.cancel_transfer
    # return fail
    def test_error_6_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_SHARE
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = None
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = self.test_application_blocktimestamp
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        additional_info = AdditionalTokenInfo()
        additional_info.token_address = self.test_token_address
        additional_info.is_manual_transfer_approval = True
        db.add(additional_info)

        # mock
        IbetSecurityTokenContract_cancel_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
            return_value=("test_tx_hash", {"status": 0})
        )

        # request target API
        with IbetSecurityTokenContract_cancel_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password")
                },
                json={
                    "operation_type": "cancel"
                }
            )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 2,
                "title": "SendTransactionError"
            },
            "detail": "failed to send transaction"
        }
